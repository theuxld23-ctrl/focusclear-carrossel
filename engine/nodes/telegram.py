"""Nó 7 — TELEGRAM (notificação, não entrega principal).

O PAINEL é o canal primário de revisão/aprovação. O Telegram virou um AVISO:
"batch pronto, revise no painel" + os PNGs como álbum + a legenda copiável.

Comportamento:
  - com TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env → envia por carrossel:
    (a) mensagem com metadados (pilar, perfil, momento),
    (b) os PNGs como álbum (sendMediaGroup),
    (c) a legenda copiável (mensagem separada).
    perfil=trauma → adiciona "⚠️ perfil sensível — considere revisão médica".
  - sem as chaves → PULA em silêncio (log, sem erro). Telegram é bônus.

Costura injetável `enviar(metodo, data, arquivos)` permite testar sem rede.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

import requests

import config

_API = "https://api.telegram.org"
Enviar = Callable[[str, dict, Optional[dict]], Any]


def _api_sender(token: str) -> Enviar:
    """Sender real: POST pra api.telegram.org, abrindo os arquivos por path."""
    def enviar(metodo: str, data: dict, arquivos: Optional[dict] = None) -> Any:
        abertos = {k: open(v, "rb") for k, v in (arquivos or {}).items()}
        try:
            r = requests.post(
                f"{_API}/bot{token}/{metodo}",
                data=data,
                files=abertos or None,
                timeout=60,
            )
            r.raise_for_status()
            return r.json()
        finally:
            for f in abertos.values():
                f.close()

    return enviar


def _texto_metadados(state: dict, carrossel: dict) -> str:
    pilar = state.get("pilar_ativo", "futebol")
    perfil = carrossel.get("_perfil", "—")
    momento = carrossel.get("momento_usado") or " x ".join(
        (carrossel.get("_jogo", {}) or {}).get("times", []) or ["—"]
    )
    linhas = [
        "🎯 <b>Batch pronto</b> — revise e aprove no painel",
        f"Pilar: <b>{pilar}</b>",
        f"Perfil: <b>{perfil}</b>",
        f"Momento: {momento}",
    ]
    if perfil == "trauma":
        linhas.append("⚠️ <b>perfil sensível</b> — considere revisão médica")
    return "\n".join(linhas)


def notificar_telegram(
    state: dict,
    token: Optional[str] = None,
    chat_id: Optional[str] = None,
    enviar: Optional[Enviar] = None,
) -> dict:
    """Envia a notificação de cada carrossel pronto; no-op se sem chaves."""
    token = token if token is not None else config.TELEGRAM_BOT_TOKEN
    chat_id = chat_id if chat_id is not None else config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("[telegram] chaves ausentes — pulando (painel é o canal primário)")
        state["telegram_enviado"] = False
        return state

    enviar = enviar or _api_sender(token)
    enviados = 0

    for carrossel in state.get("carrosseis_prontos", []):
        pngs = carrossel.get("_pngs") or []
        if not pngs:
            continue

        # (a) metadados
        enviar("sendMessage", {
            "chat_id": chat_id,
            "text": _texto_metadados(state, carrossel),
            "parse_mode": "HTML",
        }, None)

        # (b) álbum dos PNGs (sendMediaGroup exige 2..10; fallback sendPhoto p/ 1)
        if len(pngs) >= 2:
            media = [{"type": "photo", "media": f"attach://s{i}"} for i in range(len(pngs))]
            arquivos = {f"s{i}": p for i, p in enumerate(pngs)}
            enviar("sendMediaGroup", {
                "chat_id": chat_id,
                "media": json.dumps(media),
            }, arquivos)
        else:
            enviar("sendPhoto", {"chat_id": chat_id}, {"photo": pngs[0]})

        # (c) legenda copiável (mensagem separada)
        legenda = carrossel.get("legenda")
        if legenda:
            enviar("sendMessage", {"chat_id": chat_id, "text": legenda}, None)

        enviados += 1

    state["telegram_enviado"] = enviados > 0
    state["telegram_enviados"] = enviados
    return state
