"""Endpoint de visibilidade das integrações (.env) — read-only, mascarado.

NÃO permite editar o .env pela UI. Só reporta se cada chave está configurada e
um valor mascarado (para as secretas). O nome do arquivo é `integracoes.py`
(não `config.py`) para não colidir com o módulo config.py da raiz.
"""
from fastapi import APIRouter

import config

router = APIRouter(prefix="/config", tags=["config"])


def _mascara(valor: str) -> str:
    valor = (valor or "").strip()
    if not valor:
        return ""
    if len(valor) <= 4:
        return "•" * len(valor)
    return f"{valor[:3]}{'•' * 6}"


# (rótulo, chave, valor, grupo, secreto)
def _campos():
    return [
        ("Provedor LLM", "LLM_PROVIDER", config.LLM_PROVIDER, "LLM", False),
        ("Groq API Key", "GROQ_API_KEY", config.GROQ_API_KEY, "LLM", True),
        ("Groq Model", "GROQ_MODEL", config.GROQ_MODEL, "LLM", False),
        ("Anthropic API Key", "ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY, "LLM", True),
        ("Anthropic Model", "ANTHROPIC_MODEL", config.ANTHROPIC_MODEL, "LLM", False),
        ("Brave API Key", "BRAVE_API_KEY", config.BRAVE_API_KEY, "Pesquisa", True),
        ("Telegram Bot Token", "TELEGRAM_BOT_TOKEN", config.TELEGRAM_BOT_TOKEN, "Entrega", True),
        ("Telegram Chat ID", "TELEGRAM_CHAT_ID", config.TELEGRAM_CHAT_ID, "Entrega", True),
        ("ElevenLabs API Key", "ELEVENLABS_API_KEY", config.ELEVENLABS_API_KEY, "Vídeo", True),
        ("ElevenLabs Voice ID", "ELEVENLABS_VOICE_ID", config.ELEVENLABS_VOICE_ID, "Vídeo", False),
        ("HeyGen API Key", "HEYGEN_API_KEY", config.HEYGEN_API_KEY, "Vídeo", True),
        ("HeyGen Avatar ID", "HEYGEN_AVATAR_ID", config.HEYGEN_AVATAR_ID, "Vídeo", False),
    ]


@router.get("/")
def integracoes():
    itens = []
    for rotulo, chave, valor, grupo, secreto in _campos():
        configurada = bool((valor or "").strip())
        if secreto:
            exibicao = _mascara(valor) if configurada else ""
        else:
            exibicao = (valor or "").strip()  # não-secreto: mostra literal
        itens.append({
            "rotulo": rotulo,
            "chave": chave,
            "grupo": grupo,
            "secreto": secreto,
            "configurada": configurada,
            "valor": exibicao,
        })
    return {"integracoes": itens}
