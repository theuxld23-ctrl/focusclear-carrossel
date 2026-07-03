"""Agendador interno (APScheduler) — substitui o cron do VPS.

Dois batches diários no fuso de São Paulo: 06h (manhã/newsjacking) e 13h
(tarde/histórico). Cada batch cria um job e o executa.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from backend.services.job_service import criar_job, executar_job
from backend.database import SessionLocal

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def job_manha():
    db = SessionLocal()
    job = criar_job(db, "focusclear", "futebol", "carrossel", turno="manha")
    db.close()
    executar_job(job.id)


def job_tarde():
    db = SessionLocal()
    job = criar_job(db, "focusclear", "futebol", "carrossel", turno="tarde")
    db.close()
    executar_job(job.id)


def iniciar_scheduler():
    scheduler.add_job(job_manha, "cron", hour=6, minute=0, id="batch_manha")
    scheduler.add_job(job_tarde, "cron", hour=13, minute=0, id="batch_tarde")
    scheduler.start()


def parar_scheduler():
    scheduler.shutdown()
