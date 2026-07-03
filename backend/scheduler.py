"""Agendador interno (APScheduler) — substitui o cron do VPS.

A fonte de verdade do agendamento é a TABELA `agenda` (uma linha = um cron job:
workspace_id, pilar, formato, turno, horario_cron, ativo). No boot o scheduler LÊ
as linhas ativas e registra um cron por linha. Retrocompat: se a tabela estiver
VAZIA, cai no comportamento hardcoded histórico (futebol/carrossel 06h manhã +
13h tarde no focusclear). A coleta de tendências (05h) segue fixa.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services.job_service import criar_job, executar_job
from backend.database import SessionLocal, Pilar, Tendencia, Agenda
from engine.nodes.coletor_tendencias import coletar_tendencias

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
_TZ = "America/Sao_Paulo"

# Fallback histórico: usado SÓ quando a tabela agenda está vazia (retrocompat).
_AGENDA_HARDCODED = [
    {"id": "batch_manha", "workspace_id": "focusclear", "pilar": "futebol",
     "formato": "carrossel", "turno": "manha", "horario_cron": "0 6 * * *", "origem": "hardcoded"},
    {"id": "batch_tarde", "workspace_id": "focusclear", "pilar": "futebol",
     "formato": "carrossel", "turno": "tarde", "horario_cron": "0 13 * * *", "origem": "hardcoded"},
]


def pilares_ativos(workspace_id: str = "focusclear") -> list[str]:
    """Slugs dos pilares ATIVOS no banco. Retrocompat: se nenhum, default futebol."""
    db = SessionLocal()
    try:
        ativos = [
            (p.config or {}).get("chave") or p.nome
            for p in db.query(Pilar).filter_by(workspace_id=workspace_id, status="ativo").all()
        ]
        ativos = [a for a in ativos if a]
        return ativos or ["futebol"]
    finally:
        db.close()


# ── Agenda: tabela → specs de cron ───────────────────────────────────────────
def montar_agenda(rows: list) -> list[dict]:
    """Traduz linhas da tabela agenda em specs de cron job (puro, testável).

    Só considera linhas com `ativo=True`. RETROCOMPAT: se não houver nenhuma linha
    ativa, devolve as 2 regras hardcoded históricas (06h/13h do focusclear) — o
    comportamento atual continua idêntico em bancos sem agenda."""
    ativos = [r for r in rows if getattr(r, "ativo", True)]
    if not ativos:
        return [dict(spec) for spec in _AGENDA_HARDCODED]
    return [
        {
            "id": f"agenda_{r.id}",
            "workspace_id": r.workspace_id,
            "pilar": r.pilar,
            "formato": r.formato,
            "turno": r.turno,
            "horario_cron": r.horario_cron,
            "origem": "tabela",
        }
        for r in ativos
    ]


def carregar_agenda(db) -> list[dict]:
    """Lê a tabela agenda do banco e devolve os specs de cron (via montar_agenda)."""
    return montar_agenda(db.query(Agenda).all())


def _rodar_spec(spec: dict):
    """Cria e executa um job conforme uma linha da agenda."""
    db = SessionLocal()
    try:
        job = criar_job(
            db, spec["workspace_id"], spec["pilar"], spec["formato"],
            turno=spec.get("turno"),
        )
        jid = job.id
    finally:
        db.close()
    executar_job(jid)


def _registrar_agenda():
    """(Re)registra os cron jobs de agenda no scheduler a partir do banco.

    Remove os jobs de agenda anteriores (ids batch_*/agenda_*) e recria conforme
    as linhas ativas. A coleta de tendências (05h) NÃO é tocada."""
    for job in scheduler.get_jobs():
        if job.id.startswith(("agenda_", "batch_")):
            scheduler.remove_job(job.id)
    db = SessionLocal()
    try:
        specs = carregar_agenda(db)
    finally:
        db.close()
    for spec in specs:
        trigger = CronTrigger.from_crontab(spec["horario_cron"], timezone=_TZ)
        scheduler.add_job(_rodar_spec, trigger, args=[spec], id=spec["id"],
                          replace_existing=True)


def recarregar_agenda():
    """Reaplica a agenda do banco no scheduler (chamado pelos endpoints CRUD).

    No-op silencioso se o scheduler ainda não está rodando (ex.: testes)."""
    if scheduler.running:
        _registrar_agenda()


# ── Tendências (fixo 05h) ────────────────────────────────────────────────────
def coletar_e_salvar_tendencias(workspace_id: str = "focusclear") -> int:
    """Coleta tendências dos pilares ATIVOS e substitui as do workspace no banco.

    Retorna quantas tendências foram salvas. Sem BRAVE_API_KEY, o coletor devolve
    [] e o banco fica intocado (nada a substituir).
    """
    db = SessionLocal()
    try:
        ativos = [
            (p.config or {}).get("chave") or p.nome
            for p in db.query(Pilar).filter_by(workspace_id=workspace_id, status="ativo").all()
        ]
        tends = coletar_tendencias([a for a in ativos if a])
        if not tends:
            return 0
        db.query(Tendencia).filter_by(workspace_id=workspace_id).delete()
        for t in tends:
            db.add(Tendencia(
                workspace_id=workspace_id, pilar=t["pilar"], termo=t["termo"], score=t["score"],
            ))
        db.commit()
        return len(tends)
    finally:
        db.close()


def job_tendencias():
    salvas = coletar_e_salvar_tendencias("focusclear")
    print(f"[tendencias] coleta diária: {salvas} termos salvos")


def iniciar_scheduler():
    _registrar_agenda()  # lê a tabela agenda (ou cai no hardcoded se vazia)
    scheduler.add_job(job_tendencias, "cron", hour=5, minute=0, id="coletor_tendencias")
    scheduler.start()


def parar_scheduler():
    scheduler.shutdown()
