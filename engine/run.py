"""CLI do motor FocusClear — dispara o MESMO pipeline do painel.

Não reimplementa nada: cria um job e chama `job_service.executar_job` (idêntico
ao que o backend/scheduler usam). É um atalho operacional pra rodar sem subir o
painel.

Uso:
    python -m engine.run --turno manha                       # carrossel, pilar futebol
    python -m engine.run --turno tarde --formato reel
    python -m engine.run --pilar cultura_pop --formato motion
    python -m engine.run --dry-run                           # só valida o plano (NÃO chama APIs)

Execução real (sem --dry-run) requer BRAVE_API_KEY + LLM no .env — sem elas o job
vai a "erro" na pesquisa (comportamento esperado, igual ao painel).
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="engine.run", description="Dispara o pipeline FocusClear.")
    ap.add_argument("--turno", choices=["manha", "tarde"], default="manha",
                    help="manha = momentos de ontem; tarde = históricos (só afeta o pilar futebol)")
    ap.add_argument("--pilar", default="futebol", help="slug do pilar (default: futebol)")
    ap.add_argument("--formato", choices=["carrossel", "reel", "motion"], default="carrossel")
    ap.add_argument("--workspace", default="focusclear", help="workspace_id (default: focusclear)")
    ap.add_argument("--dry-run", action="store_true",
                    help="valida o plano e as importações do pipeline SEM executar (não chama APIs)")
    args = ap.parse_args(argv)

    # Importa aqui (não no topo) pra que --help funcione mesmo sem o ambiente do backend;
    # e pra que o --dry-run já prove que a fiação do pipeline importa sem erro.
    from backend.database import init_db, SessionLocal, Job
    from backend.services.job_service import criar_job, executar_job

    plano = f"pilar={args.pilar} formato={args.formato} turno={args.turno} workspace={args.workspace}"

    if args.dry_run:
        print(f"[dry-run] pipeline importado OK · plano: {plano}")
        print("[dry-run] job NÃO criado, nada executado, nenhuma API chamada.")
        print("[dry-run] execução real requer BRAVE_API_KEY + LLM no .env.")
        return 0

    init_db()
    db = SessionLocal()
    job = criar_job(db, args.workspace, args.pilar, args.formato, turno=args.turno)
    job_id = job.id
    db.close()

    print(f"disparando job {job_id} · {plano} …")
    executar_job(job_id)  # mesmo executor do backend/scheduler

    db = SessionLocal()
    job = db.query(Job).filter_by(id=job_id).first()
    status = job.status if job else "desconhecido"
    print(f"job {job_id}: status={status}")
    if job and job.erro_msg:
        print(f"  erro: {job.erro_msg}")
    db.close()
    return 0 if status == "concluido" else 1


if __name__ == "__main__":
    sys.exit(main())
