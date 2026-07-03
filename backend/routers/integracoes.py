"""Endpoint de visibilidade das integrações (.env) — read-only, mascarado.

NÃO permite editar o .env pela UI. Só reporta se cada chave está configurada e
um valor mascarado (para as secretas). O nome do arquivo é `integracoes.py`
(não `config.py`) para não colidir com o módulo config.py da raiz.
"""
from typing import Optional

import requests
from fastapi import APIRouter

import config

router = APIRouter(prefix="/config", tags=["config"])

_TIMEOUT = 8
_BRAVE_WEB = "https://api.search.brave.com/res/v1/web/search"


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
            "status": "configurada" if configurada else "pendente",
        })
    return {"integracoes": itens}


def _validar_chave(chave: str, valor: str) -> Optional[str]:
    """Testa uma chave contra o serviço real. 'ativa' | 'invalida', ou None se a
    chave não for validável isoladamente (ex.: model name, chat_id, voice_id).

    Só é chamado para chaves PREENCHIDAS — nenhuma chamada externa acontece se a
    chave não existir no .env (restrição da Fase 5). Read-only: nada é escrito.
    """
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        if chave == "BRAVE_API_KEY":
            r = requests.get(
                _BRAVE_WEB,
                headers={"Accept": "application/json", "X-Subscription-Token": valor},
                params={"q": "teste", "count": 1, "country": "br"},
                timeout=_TIMEOUT,
            )
            return "ativa" if r.status_code == 200 else "invalida"
        if chave == "TELEGRAM_BOT_TOKEN":
            r = requests.get(f"https://api.telegram.org/bot{valor}/getMe", timeout=_TIMEOUT)
            return "ativa" if (r.status_code == 200 and r.json().get("ok")) else "invalida"
        if chave == "GROQ_API_KEY":
            r = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {valor}"}, timeout=_TIMEOUT,
            )
            return "ativa" if r.status_code == 200 else "invalida"
        if chave == "ANTHROPIC_API_KEY":
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": valor,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={"model": config.ANTHROPIC_MODEL, "max_tokens": 1,
                      "messages": [{"role": "user", "content": "ping"}]},
                timeout=_TIMEOUT + 4,
            )
            return "ativa" if r.status_code == 200 else "invalida"
    except Exception:  # noqa: BLE001 — rede/timeout/DNS → chave não confirmada
        return "invalida"
    return None  # chave preenchida mas não validável isoladamente


@router.get("/validar")
def validar_integracoes():
    """Valida ao vivo as chaves PREENCHIDAS contra os serviços reais.

    Status real por chave: 'pendente' (vazia), 'ativa' (respondeu 200),
    'invalida' (preenchida mas falhou), 'configurada' (preenchida, não validável
    isoladamente — ex.: model name, chat_id, voice_id). Read-only.
    """
    validacoes = []
    for _rotulo, chave, valor, _grupo, _secreto in _campos():
        if not (valor or "").strip():
            status = "pendente"
        else:
            status = _validar_chave(chave, valor) or "configurada"
        validacoes.append({"chave": chave, "status": status})
    return {"validacoes": validacoes}
