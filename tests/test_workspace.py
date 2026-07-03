"""FASE 6 — ISOLAMENTO MULTI-WORKSPACE, offline.

Roda com:  python -m tests.test_workspace
Sucesso = asserções passam e imprime "WORKSPACE OK".

Prova que dados de um workspace NÃO vazam pro outro: cria dois workspaces num
banco temporário, insere jobs/assets/tendencias/pilares em cada um e verifica que
a consulta filtrada por workspace só devolve os do próprio workspace. É o mesmo
filtro (`filter_by(workspace_id=...)`) que todo endpoint de lista usa.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.database import Base, Workspace, Pilar, Job, Asset, Tendencia  # noqa: E402


def _sessao_temporaria():
    """Engine SQLite em memória isolada (não toca no focusclear.db real)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _povoar(db, ws: str, n_jobs: int, n_tend: int):
    db.add(Workspace(id=ws, nome=ws.title()))
    db.add(Pilar(workspace_id=ws, nome="Futebol", status="ativo", config={"chave": "futebol"}))
    for i in range(n_jobs):
        jid = str(uuid.uuid4())
        db.add(Job(id=jid, workspace_id=ws, pilar="futebol", formato="carrossel",
                   tema=f"{ws} job {i}", status="concluido"))
        db.add(Asset(id=str(uuid.uuid4()), job_id=jid, workspace_id=ws, tipo="slide",
                     caminho=f"/tmp/{ws}_{i}.png", status="rascunho", metadados={"n": 1}))
    for i in range(n_tend):
        db.add(Tendencia(workspace_id=ws, pilar="futebol", termo=f"{ws} termo {i}", score=10 + i))
    db.commit()


def test_isolamento_entre_workspaces():
    db = _sessao_temporaria()
    _povoar(db, "focusclear", n_jobs=3, n_tend=4)
    _povoar(db, "demo", n_jobs=1, n_tend=2)

    for modelo, foco, dem in ((Job, 3, 1), (Asset, 3, 1), (Tendencia, 4, 2)):
        f = db.query(modelo).filter_by(workspace_id="focusclear").all()
        d = db.query(modelo).filter_by(workspace_id="demo").all()
        assert len(f) == foco, (modelo.__name__, len(f))
        assert len(d) == dem, (modelo.__name__, len(d))
        # nenhum registro de um workspace tem o id do outro
        assert all(x.workspace_id == "focusclear" for x in f)
        assert all(x.workspace_id == "demo" for x in d)

    # os temas do demo não aparecem na consulta do focusclear (e vice-versa)
    temas_foco = {j.tema for j in db.query(Job).filter_by(workspace_id="focusclear").all()}
    temas_demo = {j.tema for j in db.query(Job).filter_by(workspace_id="demo").all()}
    assert temas_foco.isdisjoint(temas_demo), (temas_foco, temas_demo)

    # cada workspace tem seus próprios pilares (seed por workspace)
    assert db.query(Pilar).filter_by(workspace_id="focusclear").count() == 1
    assert db.query(Pilar).filter_by(workspace_id="demo").count() == 1
    db.close()


def main() -> None:
    test_isolamento_entre_workspaces()
    print("\nisolamento: focusclear (3 jobs / 4 tend) × demo (1 job / 2 tend) — sem vazamento")
    print("\nWORKSPACE OK")


if __name__ == "__main__":
    main()
