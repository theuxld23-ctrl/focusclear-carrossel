"""Camada de persistência — SQLAlchemy + SQLite.

Todas as tabelas carregam `workspace_id` desde o início (fundação de produto
multi-workspace). v1 opera com o workspace seed "focusclear".
"""
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Boolean, Text
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
    __tablename__ = "agenda"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False)
    pilar = Column(String, nullable=False)
    formato = Column(String, nullable=False)
    horario_cron = Column(String, nullable=False)  # "0 6 * * *"
    ativo = Column(Boolean, default=True)


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


def _seed_pilares(db):
    """Popula a tabela pilares a partir de engine/data/pilares.json (fonte de verdade).

    Guarda o slug do pilar em config['chave'] (a tabela usa id autoincrement).
    futebol=ativo; novela_reality/musica_popular/datas_sazonais=planejado.
    """
    import json
    from config import DATA

    if db.query(Pilar).filter_by(workspace_id="focusclear").first():
        return
    data = json.loads((DATA / "pilares.json").read_text(encoding="utf-8"))
    for chave, p in data.get("pilares", {}).items():
        db.add(Pilar(
            workspace_id="focusclear",
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


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(Workspace).filter_by(id="focusclear").first():
        db.add(Workspace(id="focusclear", nome="FocusClear"))
        db.commit()
    _seed_pilares(db)
    db.close()
