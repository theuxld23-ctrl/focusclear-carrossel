"""Lógica de jobs — cria o registro, dispara o motor em background, persiste
status e resultado. v1 roda só o nó de pesquisa (motor completo vem nas etapas
seguintes da construção)."""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import Job, Asset
from engine.nodes.pesquisa import pesquisa_manha, pesquisa_tarde


def criar_job(db: Session, workspace_id: str, pilar: str, formato: str,
              tema: str = None, turno: str = None) -> Job:
    job = Job(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        pilar=pilar,
        formato=formato,
        tema=tema,
        turno=turno,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def executar_job(job_id: str):
    """Roda em background. Atualiza status no banco conforme avança."""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(Job).filter_by(id=job_id).first()
        if not job:
            return

        job.status = "rodando"
        job.atualizado_em = datetime.utcnow()
        db.commit()

        # Montar state inicial para o motor
        state = {
            "turno": job.turno or "manha",
            "pilar_ativo": job.pilar,
            "data": datetime.utcnow().date().isoformat(),
            "erros": [],
        }

        # Por enquanto: só o nó de pesquisa (motor completo vem nas etapas seguintes)
        if job.turno == "tarde":
            resultado = pesquisa_tarde(state)
        else:
            resultado = pesquisa_manha(state)

        # Salvar resultado como asset placeholder
        asset = Asset(
            id=str(uuid.uuid4()),
            job_id=job.id,
            workspace_id=job.workspace_id,
            tipo="pesquisa",  # placeholder até compositor existir
            status="rascunho",
            metadados={
                "jogos_pesquisados": resultado.get("jogos_pesquisados", []),
                "fase_copa": resultado.get("fase_copa"),
                "erros": resultado.get("erros", []),
            }
        )
        db.add(asset)

        job.status = "concluido"
        job.atualizado_em = datetime.utcnow()
        db.commit()

    except Exception as e:
        job = db.query(Job).filter_by(id=job_id).first()
        if job:
            job.status = "erro"
            job.erro_msg = str(e)
            job.atualizado_em = datetime.utcnow()
            db.commit()
    finally:
        db.close()
