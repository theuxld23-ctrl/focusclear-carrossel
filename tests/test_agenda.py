"""AGENDA CONECTADA AO SCHEDULER, offline.

Roda com:  python -m tests.test_agenda
Sucesso = asserções passam e imprime "AGENDA OK".

Prova, sem rede/APScheduler rodando, que:
  - o scheduler LÊ a tabela agenda (`carregar_agenda`/`montar_agenda`);
  - RETROCOMPAT: tabela vazia → cai nas 2 regras hardcoded (06h/13h focusclear);
  - `_seed_agenda` materializa as regras antes hardcoded no focusclear (e só nele);
  - linhas `ativo=False` não viram cron;
  - os endpoints CRUD (listar/criar/patch/delete) respondem sobre um banco temporário;
  - todo `horario_cron` seedado é um cron válido (CronTrigger.from_crontab).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apscheduler.triggers.cron import CronTrigger  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.database import Base, Agenda, _seed_agenda  # noqa: E402
from backend.scheduler import montar_agenda, carregar_agenda  # noqa: E402
from backend.routers.agenda import (  # noqa: E402
    listar_agenda, criar_agenda, atualizar_agenda, remover_agenda,
    NovaAgenda, PatchAgenda,
)


def _sessao_temporaria():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_retrocompat_tabela_vazia():
    """Sem nenhuma linha, o scheduler mantém o comportamento hardcoded 06h/13h."""
    specs = montar_agenda([])
    assert len(specs) == 2, specs
    assert {s["horario_cron"] for s in specs} == {"0 6 * * *", "0 13 * * *"}, specs
    assert all(s["origem"] == "hardcoded" for s in specs), specs
    assert all(s["pilar"] == "futebol" and s["formato"] == "carrossel" for s in specs), specs
    turnos = {s["turno"] for s in specs}
    assert turnos == {"manha", "tarde"}, turnos


def test_seed_agenda_focusclear():
    """_seed_agenda popula 2 regras no focusclear e nada no demo."""
    db = _sessao_temporaria()
    _seed_agenda(db, "focusclear")
    _seed_agenda(db, "demo")
    foco = db.query(Agenda).filter_by(workspace_id="focusclear").all()
    demo = db.query(Agenda).filter_by(workspace_id="demo").all()
    assert len(foco) == 2, foco
    assert len(demo) == 0, demo
    # idempotente: rodar de novo não duplica
    _seed_agenda(db, "focusclear")
    assert db.query(Agenda).filter_by(workspace_id="focusclear").count() == 2
    db.close()


def test_scheduler_le_a_tabela():
    """Com linhas na tabela, carregar_agenda devolve os specs delas (não o hardcoded)."""
    db = _sessao_temporaria()
    _seed_agenda(db, "focusclear")
    db.add(Agenda(workspace_id="focusclear", pilar="cultura_pop", formato="reel",
                  turno=None, horario_cron="30 18 * * *", ativo=True))
    db.add(Agenda(workspace_id="focusclear", pilar="futebol", formato="motion",
                  turno=None, horario_cron="0 20 * * *", ativo=False))  # pausado → ignorado
    db.commit()

    specs = carregar_agenda(db)
    assert all(s["origem"] == "tabela" for s in specs), specs
    # 2 seed + 1 novo ativo = 3; o pausado (ativo=False) NÃO entra
    assert len(specs) == 3, [s["horario_cron"] for s in specs]
    crons = {s["horario_cron"] for s in specs}
    assert "30 18 * * *" in crons and "0 20 * * *" not in crons, crons
    # o reel de 18h30 veio da tabela com o formato certo
    reel = next(s for s in specs if s["horario_cron"] == "30 18 * * *")
    assert reel["formato"] == "reel" and reel["pilar"] == "cultura_pop", reel
    db.close()


def test_todo_cron_seedado_e_valido():
    """Os cron das regras seedadas parseiam (o scheduler os registraria sem erro)."""
    db = _sessao_temporaria()
    _seed_agenda(db, "focusclear")
    for spec in carregar_agenda(db):
        # não levanta = cron válido
        CronTrigger.from_crontab(spec["horario_cron"], timezone="America/Sao_Paulo")
    db.close()


def test_crud_endpoints():
    """Os handlers de CRUD respondem sobre um banco temporário (sem HTTP/scheduler)."""
    db = _sessao_temporaria()
    _seed_agenda(db, "focusclear")

    # LISTAR (2 do seed)
    linhas = listar_agenda(workspace_id="focusclear", db=db)
    assert len(linhas) == 2, linhas

    # CRIAR
    criada = criar_agenda(
        NovaAgenda(pilar="datas_sazonais", formato="carrossel", turno="manha",
                   horario_cron="0 8 * * *", workspace_id="focusclear"),
        db=db,
    )
    assert criada.id and criada.pilar == "datas_sazonais"
    assert len(listar_agenda(workspace_id="focusclear", db=db)) == 3

    # PATCH (pausar)
    atualizada = atualizar_agenda(criada.id, PatchAgenda(ativo=False), db=db)
    assert atualizada.ativo is False
    # pausada some dos specs ativos do scheduler
    assert all(s["id"] != f"agenda_{criada.id}" for s in carregar_agenda(db)), "pausada não deveria virar cron"

    # DELETE
    resp = remover_agenda(criada.id, db=db)
    assert resp["ok"] is True
    assert len(listar_agenda(workspace_id="focusclear", db=db)) == 2
    db.close()


def main() -> None:
    test_retrocompat_tabela_vazia()
    test_seed_agenda_focusclear()
    test_scheduler_le_a_tabela()
    test_todo_cron_seedado_e_valido()
    test_crud_endpoints()
    print("\nagenda: tabela vazia → hardcoded 06h/13h (retrocompat)")
    print("agenda: 2 regras seedadas no focusclear + CRUD ok; pausadas não viram cron")
    print("\nAGENDA OK")


if __name__ == "__main__":
    main()
