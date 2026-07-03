"""Seed do workspace de TESTE "demo" — prova o isolamento multi-workspace (Fase 6).

Roda com:  python -m backend.seed_demo
Cria (se ainda não existirem) alguns jobs + tendências SÓ no workspace "demo".
Assim dá pra ver no painel que, ao trocar de workspace, os dados de "demo" não
aparecem em "focusclear" e vice-versa. Idempotente (não duplica).

Não chama nenhuma API externa: os jobs são registros de exemplo (status concluído)
e as tendências são termos fixos de demonstração.
"""
from __future__ import annotations

import uuid

from backend.database import init_db, SessionLocal, Job, Tendencia

WS = "demo"

_JOBS_DEMO = [
    {"pilar": "futebol", "formato": "carrossel", "tema": "[demo] estreia histórica"},
    {"pilar": "cultura_pop", "formato": "reel", "tema": "[demo] treta que virou lição"},
]
_TENDENCIAS_DEMO = [
    {"pilar": "futebol", "termo": "Demo FC", "score": 90},
    {"pilar": "futebol", "termo": "Zagueiro Demo", "score": 70},
    {"pilar": "cultura_pop", "termo": "Influencer Demo", "score": 60},
]


def seed_demo() -> None:
    init_db()  # garante que o workspace "demo" + pilares existem
    db = SessionLocal()
    try:
        if not db.query(Job).filter_by(workspace_id=WS).first():
            for j in _JOBS_DEMO:
                db.add(Job(id=str(uuid.uuid4()), workspace_id=WS, status="concluido", **j))
        if not db.query(Tendencia).filter_by(workspace_id=WS).first():
            for t in _TENDENCIAS_DEMO:
                db.add(Tendencia(workspace_id=WS, **t))
        db.commit()
        n_jobs = db.query(Job).filter_by(workspace_id=WS).count()
        n_tend = db.query(Tendencia).filter_by(workspace_id=WS).count()
        print(f"workspace '{WS}': {n_jobs} jobs, {n_tend} tendências")
    finally:
        db.close()
    print("SEED DEMO OK")


if __name__ == "__main__":
    seed_demo()
