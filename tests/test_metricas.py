"""MÉTRICAS ESTRUTURADAS (sem Graph API), offline.

Roda com:  python -m tests.test_metricas
Sucesso = asserções passam e imprime "METRICAS OK".

Prova que o endpoint /metricas RETORNA VAZIO SEM CRASH (estrutura pronta p/ a
Instagram Graph API — v2) e, quando houver linhas, agrega corretamente:
  - banco vazio → {metricas: [], resumo: None, conectada: False} (nada quebra);
  - `resumo_metricas([])` → None; com linhas → médias (rates) e somas (contagens);
  - o filtro por workspace/período segue o mesmo padrão dos outros endpoints.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.database import Base, Metrica  # noqa: E402
from backend.routers.metricas import listar_metricas, resumo_metricas  # noqa: E402


def _sessao_temporaria():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_endpoint_vazio_sem_crash():
    """Sem nenhuma métrica (estado atual, sem Graph API): responde vazio, não quebra."""
    db = _sessao_temporaria()
    resp = listar_metricas(workspace_id="focusclear", db=db)
    assert resp["metricas"] == [], resp
    assert resp["resumo"] is None, resp
    assert resp["conectada"] is False, resp
    db.close()


def test_resumo_agrega_quando_ha_dados():
    """Com linhas, resumo = médias (swipe/completion) e somas (saves/shares)."""
    db = _sessao_temporaria()
    db.add(Metrica(workspace_id="focusclear", asset_id="a1", periodo="2026-07",
                   swipe_rate=60.0, saves=100, shares=10, completion=40.0))
    db.add(Metrica(workspace_id="focusclear", asset_id="a2", periodo="2026-07",
                   swipe_rate=80.0, saves=50, shares=20, completion=60.0))
    # ruído de OUTRO workspace: não pode entrar na conta do focusclear
    db.add(Metrica(workspace_id="demo", asset_id="d1", periodo="2026-07",
                   swipe_rate=1.0, saves=1, shares=1, completion=1.0))
    db.commit()

    resp = listar_metricas(workspace_id="focusclear", db=db)
    assert len(resp["metricas"]) == 2, resp["metricas"]
    r = resp["resumo"]
    assert r["swipe_rate"] == 70.0, r      # média (60+80)/2
    assert r["completion"] == 50.0, r      # média (40+60)/2
    assert r["saves"] == 150, r            # soma
    assert r["shares"] == 30, r            # soma
    assert r["n_posts"] == 2, r

    # filtro por período distinto → vazio (sem crash)
    vazio = listar_metricas(workspace_id="focusclear", periodo="2020-01", db=db)
    assert vazio["metricas"] == [] and vazio["resumo"] is None
    db.close()


def test_resumo_puro():
    """resumo_metricas é puro: [] → None; ignora campos None sem quebrar."""
    assert resumo_metricas([]) is None

    class _M:  # linha mínima (sem SQLAlchemy)
        def __init__(self, sr, sv, sh, cp):
            self.swipe_rate, self.saves, self.shares, self.completion = sr, sv, sh, cp

    r = resumo_metricas([_M(50.0, None, 5, None), _M(70.0, 10, None, 80.0)])
    assert r["swipe_rate"] == 60.0, r      # média dos preenchidos
    assert r["saves"] == 10 and r["shares"] == 5, r
    assert r["completion"] == 80.0, r      # só um preenchido


def main() -> None:
    test_endpoint_vazio_sem_crash()
    test_resumo_agrega_quando_ha_dados()
    test_resumo_puro()
    print("\nmetricas: banco vazio → {metricas: [], resumo: None, conectada: False} (sem crash)")
    print("metricas: com dados → médias (swipe/completion) + somas (saves/shares), por workspace")
    print("\nMETRICAS OK")


if __name__ == "__main__":
    main()
