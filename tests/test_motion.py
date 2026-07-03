"""FASE 4 (parte 2) — MOTION COMPOSITOR (slides mistos estático+animado), offline.

Roda com:  python -m tests.test_motion
Sucesso = gera slides mistos (PNG estático + webm animado) e imprime "MOTION OK".

render_png é injetado (Pillow, rápido) para provar o mix sem custo; o webm animado
é gerado DE VERDADE pelo Chromium (2s) para provar a captura de CSS animation.
Reaproveita build_html do compositor — sem tocar no nó de carrossel.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from engine.nodes.motion_compositor import compor_motion, _gravar_webm_default, W, H  # noqa: E402


def _slide(n, funcao, headline, destaque=None, sub="", **extra):
    s = {"n": n, "funcao": funcao, "kicker": funcao, "headline": headline,
         "palavra_destaque": destaque, "sub": sub, "_bg": None}
    s.update(extra)
    return s


def _state():
    slides = [
        _slide(1, "gancho", "AOS 40 ANOS\nELE NÃO ERA", "NÃO ERA", "e segurou a Espanha"),
        _slide(2, "dado", "40 ANOS.\n5 DEFESAS.", "5 DEFESAS"),
        _slide(5, "virada", "NÃO É SÓ NO GOL.\nÉ NA VIDA.", "NA VIDA", "pertencer cansa"),
    ]
    return {
        "data": "2026-06-15", "fase_copa": "grupos",
        "carrosseis_prontos": [{
            "_perfil": "ahsd", "_jogo": {"times": ["Espanha", "Cabo Verde"]}, "slides": slides,
        }],
        "erros": [],
    }


def _png_fake(html, destino):
    """render_png injetado: PNG 1080×1350 sólido (rápido, sem browser)."""
    Image.new("RGB", (W, H), (13, 11, 15)).save(destino)
    return str(destino)


def _webm_2s(html, destino_dir, nome):
    """webm animado real, curto (2s) para o teste."""
    return _gravar_webm_default(html, destino_dir, nome, segundos=2)


def test_motion_gera_slides_mistos():
    state = compor_motion(_state(), render_png=_png_fake, gravar_webm=_webm_2s)
    slides = state["carrosseis_prontos"][0]["slides"]
    por_n = {s["n"]: s for s in slides}

    # slides 1 e 5 → animados (webm); slide 2 → estático (png)
    assert por_n[1]["_animado"] is True and por_n[1]["_caminho"].endswith(".webm")
    assert por_n[5]["_animado"] is True and por_n[5]["_caminho"].endswith(".webm")
    assert por_n[2]["_animado"] is False and por_n[2]["_caminho"].endswith(".png")

    # arquivos existem e não são vazios
    for n in (1, 2, 5):
        p = Path(por_n[n]["_caminho"])
        assert p.exists() and p.stat().st_size > 0, f"slide {n} sem arquivo"

    # PNG estático é 1080×1350
    assert Image.open(por_n[2]["_caminho"]).size == (1080, 1350)

    animados = state["carrosseis_prontos"][0]["_motion_animados"]
    assert animados == [1, 5], animados
    return state


def main() -> None:
    state = test_motion_gera_slides_mistos()
    car = state["carrosseis_prontos"][0]
    print(f"\nmotion: {len(car['slides'])} slides em {Path(car['_dir']).name}")
    for s in car["slides"]:
        tipo = "webm animado" if s["_animado"] else "png estático"
        print(f"  slide {s['n']} ({s['funcao']}): {tipo} → {Path(s['_caminho']).name}")
    print("\nMOTION OK")


if __name__ == "__main__":
    main()
