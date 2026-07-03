"""Camada de persistência — SQLAlchemy + SQLite.

Todas as tabelas carregam `workspace_id` desde o início (fundação de produto
multi-workspace). v1 opera com o workspace seed "focusclear".
"""
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./focusclear.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(String, primary_key=True)  # slug: "focusclear"
    nome = Column(String, nullable=False)
    config = Column(JSON, default=dict)
    criado_em = Column(DateTime, default=datetime.utcnow)


class Pilar(Base):
    __tablename__ = "pilares"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    status = Column(String, default="planejado")  # ativo | planejado | desativado
    config = Column(JSON, default=dict)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)  # uuid
    workspace_id = Column(String, nullable=False)
    pilar = Column(String, nullable=False)
    formato = Column(String, nullable=False)  # carrossel | reel | motion
    tema = Column(Text, nullable=True)
    turno = Column(String, nullable=True)  # manha | tarde
    status = Column(String, default="pendente")  # pendente | rodando | concluido | erro
    erro_msg = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Asset(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True)  # uuid
    job_id = Column(String, nullable=False)
    workspace_id = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # slide | reel | motion
    caminho = Column(String, nullable=True)  # path local do arquivo
    status = Column(String, default="rascunho")  # rascunho | aprovado | agendado | publicado
    metadados = Column(JSON, default=dict)  # perfil, pilar, momento, legenda, etc.
    criado_em = Column(DateTime, default=datetime.utcnow)


class Tendencia(Base):
    __tablename__ = "tendencias"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False)
    pilar = Column(String, nullable=False)
    termo = Column(String, nullable=False)
    score = Column(Integer, default=0)
    data = Column(DateTime, default=datetime.utcnow)


class Agenda(Base):
    """Agendamentos configuráveis por workspace — CONECTADA ao scheduler.

    `backend/scheduler.py` LÊ as linhas ativas desta tabela no boot e registra um
    cron job por linha (a partir de `horario_cron`). Retrocompat: se a tabela
    estiver VAZIA, o scheduler cai no comportamento hardcoded histórico
    (futebol/carrossel 06h manhã + 13h tarde no workspace focusclear).
    As regras hardcoded viram linhas via `_seed_agenda` no boot do focusclear.
    CRUD em `routers/agenda.py`; a aba /fila gerencia estas linhas."""
    __tablename__ = "agenda"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False)
    pilar = Column(String, nullable=False)
    formato = Column(String, nullable=False)  # carrossel | reel | motion
    turno = Column(String, nullable=True)  # manha | tarde (carrossel) — opcional
    horario_cron = Column(String, nullable=False)  # "0 6 * * *"
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)


class Metrica(Base):
    """Desempenho de um asset publicado — ESTRUTURA pronta para a Instagram Graph
    API (v2). Hoje NADA popula esta tabela (sem Graph API conectada); o endpoint
    `GET /metricas` devolve o que houver (vazio por enquanto) e a aba /metricas
    mostra estado vazio claro. Quando a Graph API for ligada, um coletor insere
    linhas aqui e a página passa a exibir os números reais, sem mudar a UI."""
    __tablename__ = "metricas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False)
    asset_id = Column(String, nullable=True)  # liga a um Asset publicado (opcional)
    periodo = Column(String, nullable=True)  # ex "2026-07" ou data ISO
    swipe_rate = Column(Float, nullable=True)  # % que passa do slide 1 (0-100)
    saves = Column(Integer, nullable=True)  # salvamentos
    shares = Column(Integer, nullable=True)  # compartilhamentos
    completion = Column(Float, nullable=True)  # % que chega ao slide 8 (0-100)
    coletado_em = Column(DateTime, default=datetime.utcnow)


class Personagem(Base):
    __tablename__ = "personagens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False)
    nome = Column(String, default="")
    descricao = Column(Text, default="")
    tom_de_voz = Column(Text, default="")
    foto_ref = Column(String, nullable=True)  # path em engine/assets/
    config = Column(JSON, default=dict)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Workspaces semeados no boot. "demo" é o workspace de teste do isolamento
# multi-workspace (Fase 6): dados dele nunca aparecem no "focusclear" e vice-versa.
_WORKSPACES_SEED = [("focusclear", "FocusClear"), ("demo", "Demo")]


def _seed_pilares(db, workspace_id: str):
    """Popula os pilares de UM workspace a partir de engine/data/pilares.json.

    Guarda o slug do pilar em config['chave'] (a tabela usa id autoincrement).
    futebol=ativo; cultura_pop/musica_popular/datas_sazonais=planejado.
    """
    import json
    from config import DATA

    if db.query(Pilar).filter_by(workspace_id=workspace_id).first():
        return
    data = json.loads((DATA / "pilares.json").read_text(encoding="utf-8"))
    for chave, p in data.get("pilares", {}).items():
        db.add(Pilar(
            workspace_id=workspace_id,
            nome=p.get("nome", chave),
            status=p.get("status", "planejado"),
            config={
                "chave": chave,
                "prioridade": p.get("prioridade"),
                "descricao": p.get("descricao", ""),
                "tipo_momento": p.get("tipo_momento", ""),
                "carga_emocional": p.get("carga_emocional", ""),
                "validade": p.get("validade", ""),
                "cuidado": p.get("cuidado", ""),
            },
        ))
    db.commit()


# Regras hardcoded históricas do scheduler, agora materializadas como linhas de
# agenda no boot do focusclear (a fonte de verdade do agendamento passa a ser a
# tabela). Só o focusclear é semeado; a tabela vazia = retrocompat no scheduler.
_AGENDA_SEED_FOCUSCLEAR = [
    {"pilar": "futebol", "formato": "carrossel", "turno": "manha", "horario_cron": "0 6 * * *"},
    {"pilar": "futebol", "formato": "carrossel", "turno": "tarde", "horario_cron": "0 13 * * *"},
]


def _seed_agenda(db, workspace_id: str):
    """Semeia a agenda do focusclear com as 2 regras antes hardcoded (06h/13h).

    Idempotente: só insere se o workspace ainda não tem nenhuma linha de agenda.
    Só o focusclear recebe seed (demo fica sem agendamentos)."""
    if workspace_id != "focusclear":
        return
    if db.query(Agenda).filter_by(workspace_id=workspace_id).first():
        return
    for r in _AGENDA_SEED_FOCUSCLEAR:
        db.add(Agenda(workspace_id=workspace_id, ativo=True, **r))
    db.commit()


def _migrar_sqlite(db):
    """Migração leve p/ bancos de fases anteriores: adiciona colunas novas que o
    `create_all` NÃO cria em tabelas já existentes (SQLite só faz ADD COLUMN).

    Ex.: a tabela `agenda` de antes desta feature não tinha `turno`/`criado_em`.
    Sem isso, um banco antigo quebraria ao consultar as colunas novas."""
    from sqlalchemy import text

    novas = {
        "agenda": {"turno": "VARCHAR", "criado_em": "DATETIME"},
    }
    for tabela, cols in novas.items():
        existentes = {r[1] for r in db.execute(text(f"PRAGMA table_info({tabela})"))}
        if not existentes:
            continue  # tabela nova → create_all já a criou completa
        for col, tipo in cols.items():
            if col not in existentes:
                db.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}"))
    db.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    _migrar_sqlite(db)
    for ws_id, ws_nome in _WORKSPACES_SEED:
        if not db.query(Workspace).filter_by(id=ws_id).first():
            db.add(Workspace(id=ws_id, nome=ws_nome))
            db.commit()
        _seed_pilares(db, ws_id)
        _seed_agenda(db, ws_id)
    db.close()
