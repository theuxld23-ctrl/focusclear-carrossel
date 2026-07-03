"""Endpoints de agenda — CRUD dos agendamentos que o scheduler lê.

Cada linha vira um cron job no boot (backend/scheduler.py). Após qualquer
alteração, `recarregar_agenda()` reaplica os cron no scheduler em execução (no-op
se ele não estiver rodando, ex.: testes)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db, Agenda

router = APIRouter(prefix="/agenda", tags=["agenda"])

_FORMATOS = ("carrossel", "reel", "motion")


def _recarregar():
    """Reaplica a agenda no scheduler. Import tardio evita ciclo de import."""
    from backend.scheduler import recarregar_agenda
    recarregar_agenda()


@router.get("/")
def listar_agenda(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    return (
        db.query(Agenda)
        .filter_by(workspace_id=workspace_id)
        .order_by(Agenda.horario_cron.asc(), Agenda.id.asc())
        .all()
    )


class NovaAgenda(BaseModel):
    pilar: str
    formato: str = "carrossel"
    turno: Optional[str] = None  # manha | tarde (carrossel)
    horario_cron: str  # "0 6 * * *"
    ativo: bool = True
    workspace_id: str = "focusclear"


def _valida(formato: str, turno: Optional[str]):
    if formato not in _FORMATOS:
        raise HTTPException(422, f"formato inválido (use {', '.join(_FORMATOS)})")
    if turno is not None and turno not in ("manha", "tarde"):
        raise HTTPException(422, "turno inválido (manha | tarde | null)")


@router.post("/")
def criar_agenda(nova: NovaAgenda, db: Session = Depends(get_db)):
    _valida(nova.formato, nova.turno)
    row = Agenda(
        workspace_id=nova.workspace_id, pilar=nova.pilar, formato=nova.formato,
        turno=nova.turno, horario_cron=nova.horario_cron, ativo=nova.ativo,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _recarregar()
    return row


class PatchAgenda(BaseModel):
    pilar: Optional[str] = None
    formato: Optional[str] = None
    turno: Optional[str] = None
    horario_cron: Optional[str] = None
    ativo: Optional[bool] = None


@router.patch("/{agenda_id}")
def atualizar_agenda(agenda_id: int, patch: PatchAgenda, db: Session = Depends(get_db)):
    row = db.query(Agenda).filter_by(id=agenda_id).first()
    if not row:
        raise HTTPException(404, "Agendamento não encontrado")
    _valida(patch.formato or row.formato, patch.turno if patch.turno is not None else row.turno)
    for campo in ("pilar", "formato", "turno", "horario_cron", "ativo"):
        val = getattr(patch, campo)
        if val is not None:
            setattr(row, campo, val)
    db.commit()
    db.refresh(row)
    _recarregar()
    return row


@router.delete("/{agenda_id}")
def remover_agenda(agenda_id: int, db: Session = Depends(get_db)):
    row = db.query(Agenda).filter_by(id=agenda_id).first()
    if not row:
        raise HTTPException(404, "Agendamento não encontrado")
    db.delete(row)
    db.commit()
    _recarregar()
    return {"ok": True, "id": agenda_id}
