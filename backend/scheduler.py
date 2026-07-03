"""Agendador interno (APScheduler) — substitui o cron do VPS.

Dois batches diários no fuso de São Paulo: 06h (manhã/newsjacking) e 13h
(tarde/histórico). Cada batch cria um job e o executa.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from backend.services.job_service import criar_job, executar_job
from backend.database import SessionLocal, Pilar, Tendencia
from engine.nodes.coletor_tendencias import coletar_tendencias

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


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


def _rodar_batch(turno: str):
    """Cria e executa um job de carrossel por pilar ativo (não só futebol)."""
    db = SessionLocal()
    try:
        ids = [criar_job(db, "focusclear", p, "carrossel", turno=turno).id
               for p in pilares_ativos()]
    finally:
        db.close()
    for jid in ids:
        executar_job(jid)


def job_manha():
    _rodar_batch("manha")


def job_tarde():
    _rodar_batch("tarde")


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
    scheduler.add_job(job_manha, "cron", hour=6, minute=0, id="batch_manha")
    scheduler.add_job(job_tarde, "cron", hour=13, minute=0, id="batch_tarde")
    scheduler.add_job(job_tendencias, "cron", hour=5, minute=0, id="coletor_tendencias")
    scheduler.start()


def parar_scheduler():
    scheduler.shutdown()
