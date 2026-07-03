"""FastAPI app — expõe o motor FocusClear como serviço.

lifespan: inicializa o banco (cria tabelas + seed do workspace) e sobe o
scheduler no startup; desliga o scheduler no shutdown.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.database import init_db
from backend.scheduler import iniciar_scheduler, parar_scheduler
from backend.routers import jobs, assets, pilares, tendencias, personagem, integracoes


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    iniciar_scheduler()
    yield
    parar_scheduler()


app = FastAPI(title="FocusClear Content Engine", version="0.1.0", lifespan=lifespan)
app.include_router(jobs.router)
app.include_router(assets.router)
app.include_router(pilares.router)
app.include_router(tendencias.router)
app.include_router(personagem.router)
app.include_router(integracoes.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "focusclear-engine"}
