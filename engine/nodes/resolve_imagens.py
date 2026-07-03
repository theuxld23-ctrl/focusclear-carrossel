"""Nó 5 — RESOLVE IMAGENS. Executa a cascata (estrategia_imagem.md) por slide.

Para cada slide do roteiro, percorre as candidatas catalogadas seguindo a `busca`
declarada pelo roteirista, DESCARTA fotos com marca de patrocinador dominante
(armadilha do photocall), baixa a escolhida, faz crop 1080×1350 com foco no
sujeito e aplica tratamento por clima (escuro→luz). Slide sem foto viável vira
TIPOGRÁFICO (o compositor usa fundo sólido brasa-noite).

O resultado tratado vai em slide["_bg"] como PNG base64 (ou None = tipográfico).
Costuras injetáveis `baixar`/`buscar_no_catalogo` permitem rodar sem rede.
"""
from __future__ import annotations

import base64
import io
import unicodedata
from typing import Any, Callable, Optional

import requests
from PIL import Image, ImageEnhance

from engine.nodes.coleta_imagens import jogo_key

W, H = 1080, 1350  # canvas 4:5

# Clima por função de slide → tratamento (brilho, contraste, saturação).
# Jornada escuro→luz: gancho/dado/espelho escuros; participação transição;
# virada/prova/alívio/cta na luz.
_TRATAMENTO = {
    "gancho": (0.42, 1.18, 0.85),
    "dado": (0.50, 1.15, 0.85),
    "espelho": (0.52, 1.12, 0.88),
    "participacao": (0.72, 1.05, 0.95),
    "virada": (0.95, 1.02, 1.05),
    "prova": (1.08, 1.00, 1.10),
    "alivio": (1.18, 0.98, 1.12),
    "cta": (1.20, 0.96, 1.10),
}

# Marca de patrocinador dominante no fundo → descartar (não tenta salvar).
_MARCAS = [
    "photocall", "man of the match", "craque do jogo", "player of the match",
    "premiacao", "premiação", "trofeu", "troféu", "trophy award",
    "michelob", "budweiser", "coca-cola", "coca cola", "hyundai", "kia",
    "qatar airways", "visa ", "adidas backdrop", "unites", "mastercard",
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def risco_patrocinador(item: dict) -> bool:
    """True se a candidata tem marca de patrocinador dominante (descartar)."""
    if item.get("sponsor_risk"):
        return True
    alvo = _norm(f"{item.get('titulo','')} {item.get('fonte','')} {item.get('url','')}")
    return any(m in alvo for m in _MARCAS)


def _baixar(url: str) -> bytes:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.content


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).replace("/", " ").split() if len(t) > 2}


def escolher_candidata(
    busca: str, catalogo: list[dict]
) -> Optional[dict]:
    """Cascata: melhor candidata para a `busca` do slide, pulando marcas de patrocínio.

    Ranqueia por sobreposição de termos entre a busca e o título da candidata;
    sem sobreposição, cai pra primeira candidata limpa (níveis mais baixos da
    cascata = contexto/genérica). None = nada viável → slide tipográfico.
    """
    limpas = [c for c in catalogo if not risco_patrocinador(c)]
    if not limpas:
        return None
    termos = _tokens(busca)
    ranqueadas = sorted(
        limpas,
        key=lambda c: len(termos & _tokens(c.get("titulo", ""))),
        reverse=True,
    )
    return ranqueadas[0]


def _crop_cover(img: Image.Image, foco_y: float = 0.4) -> Image.Image:
    """Redimensiona cobrindo 1080×1350 e recorta com foco no sujeito (foco_y do topo)."""
    img = img.convert("RGB")
    escala = max(W / img.width, H / img.height)
    novo = (max(W, int(img.width * escala)), max(H, int(img.height * escala)))
    img = img.resize(novo, Image.LANCZOS)
    x = (img.width - W) // 2
    y = int((img.height - H) * min(max(foco_y, 0.0), 1.0))
    return img.crop((x, y, x + W, y + H))


def _tratar(img: Image.Image, funcao: str) -> Image.Image:
    brilho, contraste, satur = _TRATAMENTO.get(funcao, (0.8, 1.0, 1.0))
    img = ImageEnhance.Brightness(img).enhance(brilho)
    img = ImageEnhance.Contrast(img).enhance(contraste)
    img = ImageEnhance.Color(img).enhance(satur)
    return img


def _png_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def resolve_imagens(
    state: dict,
    baixar: Optional[Callable[[str], bytes]] = None,
) -> dict:
    """Preenche slide['_bg'] (PNG base64 tratado) ou None (tipográfico) por slide."""
    baixar = baixar or _baixar
    erros = state.setdefault("erros", [])

    for roteiro in state.get("carrosseis_prontos", []):
        jogo = roteiro.get("_jogo", {})
        catalogo = (state.get("imagens_por_jogo") or {}).get(jogo_key(jogo), []) if jogo else []
        for slide in roteiro.get("slides", []):
            funcao = slide.get("funcao", "")
            busca = (slide.get("imagem") or {}).get("busca", "")
            cand = escolher_candidata(busca, catalogo)
            slide["_bg"] = None
            slide["_bg_fonte"] = None
            if not cand:
                slide["_tipografico"] = True
                continue
            try:
                img = Image.open(io.BytesIO(baixar(cand["url"])))
                img = _tratar(_crop_cover(img), funcao)
                slide["_bg"] = _png_b64(img)
                slide["_bg_fonte"] = cand.get("url")
                slide["_tipografico"] = False
            except Exception as e:  # noqa: BLE001 — foto ruim → cai pra tipográfico
                erros.append(f"imagem slide {slide.get('n')} falhou: {e!r}")
                slide["_tipografico"] = True

    return state
