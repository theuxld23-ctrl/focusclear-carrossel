"""Lógica de jobs — cria o registro, dispara o motor em background, persiste
status e resultado.

executar_job roda o PIPELINE COMPLETO do carrossel:
  pesquisa → coleta_imagens → seletor → roteirista → resolve_imagens → compositor
e salva um Asset tipo "slide" por PNG gerado (engine/output/). Em produção usa
config.get_llm() e a Brave reais — sem as chaves no .env, falha já na pesquisa e
o job vai a "erro" (comportamento esperado até as APIs entrarem)."""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import Job, Asset, Pilar, Personagem
from engine.nodes.pesquisa import pesquisa_manha, pesquisa_tarde, pesquisa_pilar
from engine.nodes.coleta_imagens import coletar_imagens
from engine.nodes.seletor import selecionar
from engine.nodes.roteirista import escrever_roteiro
from engine.nodes.resolve_imagens import resolve_imagens
from engine.nodes.compositor import compor
from engine.nodes.telegram import notificar_telegram
from engine.nodes.roteirista_video import escrever_roteiro_video
from engine.nodes.voz import gerar_voz
from engine.nodes.avatar import gerar_avatar
from engine.nodes.reel_compositor import compor_reel
from engine.nodes.motion_compositor import compor_motion


def _salvar_assets_motion(db: Session, job: Job, state: dict):
    """Um Asset tipo 'motion' por slide (PNG estático ou webm animado)."""
    for carrossel in state.get("carrosseis_prontos", []):
        perfil = carrossel.get("_perfil")
        jogo = carrossel.get("_jogo", {})
        legenda = carrossel.get("legenda", "")
        for slide in carrossel.get("slides", []):
            caminho = slide.get("_caminho")
            if not caminho:
                continue
            db.add(Asset(
                id=str(uuid.uuid4()),
                job_id=job.id,
                workspace_id=job.workspace_id,
                tipo="motion",
                caminho=caminho,
                status="rascunho",
                metadados={
                    "n": slide.get("n"),
                    "funcao": slide.get("funcao"),
                    "animado": slide.get("_animado", False),
                    "perfil": perfil,
                    "times": jogo.get("times"),
                    "fase_copa": state.get("fase_copa"),
                    "legenda": legenda if slide.get("n") == 1 else "",
                },
            ))


def _salvar_assets_carrossel(db: Session, job: Job, state: dict):
    """Um Asset tipo 'slide' por PNG gerado."""
    for carrossel in state.get("carrosseis_prontos", []):
        perfil = carrossel.get("_perfil")
        jogo = carrossel.get("_jogo", {})
        legenda = carrossel.get("legenda", "")
        for slide in carrossel.get("slides", []):
            caminho = slide.get("_png")
            if not caminho:
                continue
            db.add(Asset(
                id=str(uuid.uuid4()),
                job_id=job.id,
                workspace_id=job.workspace_id,
                tipo="slide",
                caminho=caminho,
                status="rascunho",
                metadados={
                    "n": slide.get("n"),
                    "funcao": slide.get("funcao"),
                    "perfil": perfil,
                    "times": jogo.get("times"),
                    "fase_copa": state.get("fase_copa"),
                    "legenda": legenda if slide.get("n") == 1 else "",
                    "tipografico": slide.get("_tipografico", False),
                },
            ))


def _salvar_assets_reel(db: Session, job: Job, state: dict):
    """Um Asset tipo 'reel' por reel montado (vídeo ou poster placeholder)."""
    for reel in state.get("reels_prontos", []):
        caminho = reel.get("_caminho")
        if not caminho:
            continue
        roteiro = reel.get("roteiro") or {}
        db.add(Asset(
            id=str(uuid.uuid4()),
            job_id=job.id,
            workspace_id=job.workspace_id,
            tipo="reel",
            caminho=caminho,
            status="rascunho",
            metadados={
                "perfil": reel.get("_perfil"),
                "times": (reel.get("_jogo") or {}).get("times"),
                "fase_copa": state.get("fase_copa"),
                "momento": reel.get("momento"),
                "texto_completo": roteiro.get("texto_completo", ""),
                "duracao_estimada_s": roteiro.get("duracao_estimada_s"),
                "label_ia": roteiro.get("label_ia", "conteúdo gerado por IA"),
                "placeholder": reel.get("_placeholder", True),
                "poster": reel.get("_poster"),
            },
        ))


def _config_do_pilar(db: Session, workspace_id: str, chave: str) -> dict:
    """Config (JSON) do pilar cujo slug == chave, do banco. {} se não achar."""
    for p in db.query(Pilar).filter_by(workspace_id=workspace_id).all():
        cfg = p.config or {}
        if cfg.get("chave") == chave or p.nome == chave:
            return cfg
    return {}


def _state_do_personagem(db: Session, workspace_id: str) -> dict:
    """Lê o personagem do banco e devolve as chaves que alimentam o reel
    (foto de referência do avatar + voice_id/tom da voz). {} se não configurado."""
    p = db.query(Personagem).filter_by(workspace_id=workspace_id).first()
    if not p:
        return {}
    out: dict = {}
    if p.foto_ref:
        out["avatar_foto"] = p.foto_ref
    out["voz_config"] = {
        "voice_id": (p.config or {}).get("voice_id") or "",
        "tom": p.tom_de_voz or "",
    }
    return out


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

        # Montar state inicial para o motor (config do pilar + personagem do banco)
        state = {
            "turno": job.turno or "manha",
            "pilar_ativo": job.pilar,
            "pilar_config": _config_do_pilar(db, job.workspace_id, job.pilar),
            "data": datetime.utcnow().date().isoformat(),
            "erros": [],
        }
        state.update(_state_do_personagem(db, job.workspace_id))

        # Pesquisa: futebol usa os turnos (jogos de ontem / históricos); os demais
        # pilares usam a pesquisa genérica do pilar (queries do próprio pilar).
        if job.pilar == "futebol":
            if job.turno == "tarde":
                state = pesquisa_tarde(state)
            else:
                state = pesquisa_manha(state)
        else:
            state = pesquisa_pilar(state)
        state = coletar_imagens(state)
        state = selecionar(state)

        if job.formato == "reel":
            # Ramo REEL: roteirista_video → voz → avatar → reel_compositor
            state = escrever_roteiro_video(state)
            state = gerar_voz(state)
            state = gerar_avatar(state)
            state = compor_reel(state)
            state = notificar_telegram(state)
            _salvar_assets_reel(db, job, state)
        elif job.formato == "motion":
            # Ramo MOTION: roteirista → resolve_imagens → motion_compositor
            state = escrever_roteiro(state)
            state = resolve_imagens(state)
            state = compor_motion(state)
            state = notificar_telegram(state)
            _salvar_assets_motion(db, job, state)
        else:
            # Ramo CARROSSEL: roteirista → resolve_imagens → compositor
            state = escrever_roteiro(state)
            state = resolve_imagens(state)
            state = compor(state)
            state = notificar_telegram(state)
            _salvar_assets_carrossel(db, job, state)

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
