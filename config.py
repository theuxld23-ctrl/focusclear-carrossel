"""Configuração central: chaves de ambiente, caminhos e LLM plugável.

Princípio #3 (CLAUDE.md): TODO acesso a LLM passa por get_llm().
NUNCA hardcode Groq/Claude/modelo em outro arquivo do projeto.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv

load_dotenv()

# --- Caminhos ---
BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR / "engine" / "data"
OUTPUT = BASE_DIR / "engine" / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

# --- Chaves de serviços ---
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def require_brave_key() -> str:
    """Retorna a BRAVE_API_KEY ou falha com mensagem clara se ausente.

    A Brave é a ÚNICA fonte de dados do nó de pesquisa (SofaScore/FotMob bloqueiam
    o IP do VPS). Sem a chave o nó não funciona — falhar cedo e legível em vez de
    deixar estourar um 401/422 cru lá no meio da pesquisa.
    """
    key = (BRAVE_API_KEY or os.getenv("BRAVE_API_KEY", "")).strip()
    if not key:
        raise RuntimeError(
            "BRAVE_API_KEY não configurada — defina BRAVE_API_KEY no arquivo .env "
            "(veja .env.example). A Brave é a fonte de dados do nó de pesquisa."
        )
    return key

# --- LLM plugável ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# callable retornado por get_llm(): complete(system, user) -> str
LLMComplete = Callable[[str, str], str]


def _groq_complete() -> LLMComplete:
    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)

    def complete(system: str, user: str) -> str:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    return complete


def _anthropic_complete() -> LLMComplete:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def complete(system: str, user: str) -> str:
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    return complete


def get_llm(provider: Optional[str] = None) -> LLMComplete:
    """Retorna o callable complete(system, user) -> str do provedor ativo.

    Lê LLM_PROVIDER do .env (groq|anthropic) salvo se `provider` for passado.
    Groq -> llama-3.3-70b-versatile; Anthropic -> claude-sonnet-4-6
    (ambos sobrescrevíveis via GROQ_MODEL / ANTHROPIC_MODEL).
    """
    provider = (provider or LLM_PROVIDER).lower()
    if provider == "groq":
        return _groq_complete()
    if provider == "anthropic":
        return _anthropic_complete()
    raise ValueError(
        f"LLM_PROVIDER desconhecido: {provider!r} (use 'groq' ou 'anthropic')"
    )
