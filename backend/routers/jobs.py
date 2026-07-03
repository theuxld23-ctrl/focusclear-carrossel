"""Endpoints de jobs — criar (dispara motor em background), consultar, listar."""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db, Job
from backend.services.job_service import criar_job, executar_job
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CriarJobRequest(BaseModel):
    workspace_id: str = "focusclear"
    pilar: str = "futebol"
    formato: str = "carrossel"
    tema: Optional[str] = None
    turno: Optional[str] = "manha"


@router.post("/")
def post_job(req: CriarJobRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    job = criar_job(db, req.workspace_id, req.pilar, req.formato, req.tema, req.turno)
    bg.add_task(executar_job, job.id)
    return {"job_id": job.id, "status": job.status}


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Job não encontrado")
    return job


@router.get("/")
def listar_jobs(workspace_id: str = "focusclear", db: Session = Depends(get_db)):
    return db.query(Job).filter_by(workspace_id=workspace_id).order_by(Job.criado_em.desc()).limit(50).all()
