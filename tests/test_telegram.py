"""Nó TELEGRAM — notificação (não entrega). Offline, via costura `enviar`.

Roda com:  python -m tests.test_telegram   (raiz, venv ativo)
Sucesso = asserções passam e imprime "TELEGRAM OK".

Verifica:
  - com chaves: envia metadados + álbum (N fotos) + legenda copiável por carrossel;
  - perfil=trauma adiciona o aviso de revisão médica;
  - sem chaves: PULA em silêncio (o sender nunca é chamado, sem erro).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.nodes.telegram import notificar_telegram  # noqa: E402


def _state(perfil="ahsd"):
    return {
        "pilar_ativo": "futebol",
        "carrosseis_prontos": [{
            "_perfil": perfil,
            "_jogo": {"times": ["Espanha", "Cabo Verde"]},
            "momento_usado": "Espanha 0x0 Cabo Verde — Vozinha segura a Espanha",
            "legenda": "saúde mental também é pertencer. ...",
            "_pngs": [f"/tmp/slide_{i}.png" for i in range(1, 9)],
        }],
    }


def _gravador():
    chamadas = []

    def enviar(metodo, data, arquivos=None):
        chamadas.append({"metodo": metodo, "data": data, "arquivos": arquivos})
        return {"ok": True}

    return chamadas, enviar


def test_envia_com_chaves():
    chamadas, enviar = _gravador()
    state = notificar_telegram(_state(), token="TOKEN", chat_id="123", enviar=enviar)

    metodos = [c["metodo"] for c in chamadas]
    assert metodos == ["sendMessage", "sendMediaGroup", "sendMessage"], metodos
    assert state["telegram_enviado"] is True and state["telegram_enviados"] == 1

    # metadados
    meta = chamadas[0]["data"]["text"]
    assert "futebol" in meta and "ahsd" in meta and "Cabo Verde" in meta

    # álbum com 8 fotos anexadas
    album = chamadas[1]
    assert album["data"]["media"].count('"photo"') == 8, album["data"]["media"]
    assert len(album["arquivos"]) == 8

    # legenda copiável separada
    assert "saúde mental" in chamadas[2]["data"]["text"]


def test_trauma_adiciona_aviso():
    chamadas, enviar = _gravador()
    notificar_telegram(_state(perfil="trauma"), token="T", chat_id="1", enviar=enviar)
    assert "revisão médica" in chamadas[0]["data"]["text"], chamadas[0]["data"]["text"]


def test_pula_sem_chaves():
    chamadas, enviar = _gravador()
    state = notificar_telegram(_state(), token="", chat_id="", enviar=enviar)
    assert chamadas == [], "sem chaves, o sender não pode ser chamado"
    assert state["telegram_enviado"] is False


def main() -> None:
    test_envia_com_chaves()
    test_trauma_adiciona_aviso()
    test_pula_sem_chaves()
    print("\nTELEGRAM OK")


if __name__ == "__main__":
    main()
