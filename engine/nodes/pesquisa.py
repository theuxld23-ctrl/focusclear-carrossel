"""Nó 1 — PESQUISA. Base factual de todo o pipeline (princípio #1: anti-alucinação).

FONTE DE DADOS = BRAVE SEARCH (única). SofaScore/FotMob bloqueiam o IP do VPS
(403 / header assinado), então NÃO são acessados direto. A Brave pesquisa e seus
snippets já trazem o placar do SofaScore + a narrativa de CNN/ESPN/GE/CazéTV/FIFA.
O cliente direto SofaScore/FotMob fica preservado como fallback DESATIVADO
(`_FALLBACK_DIRETO_ATIVO = False`), caso um dia haja proxy residencial.

Como os fatos agora vêm de SNIPPET DE TEXTO (não JSON estruturado), o risco de
interpretação errada sobe. Por isso o nó:
  - coleta de MÚLTIPLAS fontes confiáveis e só fixa o placar quando há acordo
    (`fontes_concordam`); na dúvida (conflito), deixa o campo VAZIO — não chuta;
  - registra as URLs de cada fonte em `fontes_urls` (rastreabilidade).

Dois turnos:
  - pesquisa_manha(state): jogos do dia anterior (newsjacking).
  - pesquisa_tarde(state): momentos históricos marcantes (transgeracional).

Este nó NÃO valida se o time está na Copa (isso é do seletor, etapa 3) — usa a
lista de seleções apenas para RECONHECER nomes nos snippets (NER), nunca para
descartar. Costuras de injeção (`descobrir`, `buscar_jogo`, `buscar_hist`)
permitem testar a lógica sem rede.

CAMADA DE PILARES: as fontes confiáveis são POR PILAR (`_FONTES_POR_PILAR`).
v1 só tem o pilar `futebol` ativo e funcional de ponta a ponta — é o único no
caminho de produção; a lógica de consenso multi-fonte é a mesma pra qualquer
pilar, só troca QUAIS fontes (lidas de `pilar_config['fontes_pesquisa']`). Quando
um segundo pilar for ativado, registra-se aqui o mapa domínio→rótulo dele e o nó
passa a validar contra as fontes daquele pilar, sem mudar a lógica.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from typing import Any, Callable, Optional

import requests

from config import DATA, require_brave_key

# ── Endpoints Brave ──────────────────────────────────────────────────────────
_BRAVE_WEB = "https://api.search.brave.com/res/v1/web/search"
_BRAVE_IMAGES = "https://api.search.brave.com/res/v1/images/search"  # etapas futuras
_TIMEOUT = 12

# Fonte confiável -> rótulo canônico (match por substring no domínio da URL).
_FONTES_CONFIAVEIS: dict[str, str] = {
    "sofascore.com": "sofascore",
    "fotmob.com": "fotmob",
    "cnnbrasil.com": "cnn",
    "cnn.com": "cnn",
    "espn.com.br": "espn",
    "espn.com": "espn",
    "ge.globo.com": "ge",
    "globoesporte": "ge",
    "fifa.com": "fifa",
    "cazetv": "cazetv",
    "youtube.com/@cazetv": "cazetv",
    "uol.com.br": "uol",
    "lance.com.br": "lance",
}

# Fontes confiáveis POR PILAR (domínio→rótulo). Elas dão o CONSENSO multi-fonte que
# é a âncora anti-alucinação dos pilares sem lista fixa (ver docstring de
# pesquisa_pilar): um nome/evento só "conta" se aparecer em fontes distintas.
_FONTES_CULTURA_POP: dict[str, str] = {
    "metropoles.com": "metropoles", "gshow.globo.com": "gshow", "quem.globo.com": "quem",
    "otvfoco.com.br": "tvfoco", "purepeople.com.br": "purepeople", "uol.com.br": "uol",
    "terra.com.br": "terra", "hugogloss": "hugogloss", "contigo": "contigo",
    "g1.globo.com": "g1", "youtube.com": "youtube",
}
_FONTES_MUSICA: dict[str, str] = {
    "billboard.com.br": "billboard", "billboard.com": "billboard", "spotify.com": "spotify",
    "letras.mus.br": "letras", "genius.com": "genius", "rollingstone.com.br": "rollingstone",
    "tenhomaisdiscos": "tmdqa", "g1.globo.com": "g1", "uol.com.br": "uol", "youtube.com": "youtube",
}
_FONTES_DATAS: dict[str, str] = {
    "g1.globo.com": "g1", "agenciabrasil.ebc.com.br": "agenciabrasil", "gov.br": "gov",
    "cnnbrasil.com": "cnn", "uol.com.br": "uol", "terra.com.br": "terra", "bbc.com": "bbc",
}
_FONTES_POR_PILAR: dict[str, dict[str, str]] = {
    "futebol": _FONTES_CONFIAVEIS,
    "cultura_pop": _FONTES_CULTURA_POP,
    "musica_popular": _FONTES_MUSICA,
    "datas_sazonais": _FONTES_DATAS,
}


def fontes_do_pilar(pilar_ativo: str = "futebol") -> dict[str, str]:
    """Mapa domínio→rótulo das fontes confiáveis do pilar (default futebol)."""
    return _FONTES_POR_PILAR.get(pilar_ativo, _FONTES_CONFIAVEIS)


# Queries de MOMENTO por pilar não-futebol (slug de pilares.json). Se o pilar não
# estiver aqui, deriva do próprio config do pilar (carga_emocional/tipo_momento).
_QUERIES_MOMENTO_POR_PILAR: dict[str, list[str]] = {
    # Fofoca / drama de criadores: cancelamento, treta, BBB, affair/término de famosos.
    "cultura_pop": [
        "influencer cancelado polêmica repercussão hoje Brasil",
        "treta briga entre criadores YouTube assunto do dia hoje",
        "BBB paredão eliminação repercussão hoje",
        "término affair famosos fofoca repercussão hoje",
    ],
    # Charts / lançamentos: música que bombou, letra que viralizou.
    "musica_popular": [
        "música que mais tocou hoje Brasil sertanejo funk pagode paradas",
        "lançamento música viral repercussão hoje",
        "letra música término saudade viralizou hoje Brasil",
    ],
    # A própria data + o ângulo emocional do ano.
    "datas_sazonais": [
        "próxima data comemorativa Brasil o que a gente sente",
        "Natal Ano Novo Dia das Mães ângulo emocional solidão retrospectiva hoje",
        "campanha sazonal assunto do momento sentimento este ano",
    ],
}


def queries_do_pilar(pilar: str, pilar_config: Optional[dict] = None) -> list[str]:
    """Queries de busca do pilar. Usa o mapa por slug; se ausente, deriva do config
    (campo carga_emocional → termos de dor; tipo_momento como contexto)."""
    if pilar in _QUERIES_MOMENTO_POR_PILAR:
        return list(_QUERIES_MOMENTO_POR_PILAR[pilar])
    cfg = pilar_config or {}
    termos = [t.strip() for t in re.split(r"[,;]", cfg.get("carga_emocional", "")) if t.strip()]
    if termos:
        return [f"{pilar} {t} repercussão hoje Brasil" for t in termos[:3]]
    return [f"{pilar} assunto em alta hoje Brasil"]


Jogo = dict[str, Any]

_MESES_PT = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


# ── Texto / normalização ─────────────────────────────────────────────────────
def _norm(s: str) -> str:
    """minúsculo, sem acento, espaços colapsados — para casar nomes em snippet."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _dominio_confiavel(url: str, fontes: Optional[dict[str, str]] = None) -> Optional[str]:
    """Rótulo canônico se a URL for de fonte confiável. `fontes` default = futebol
    (mapa domínio→rótulo); passar o mapa do pilar ativo para outros pilares."""
    u = (url or "").lower()
    for chave, rotulo in (fontes or _FONTES_CONFIAVEIS).items():
        if chave in u:
            return rotulo
    return None


def _dominio_de(url: str) -> str:
    """Host da URL (sem www), p/ contar fontes DISTINTAS no consenso multi-fonte."""
    from urllib.parse import urlparse
    net = urlparse(url or "").netloc.lower()
    return net[4:] if net.startswith("www.") else net


# placar entre dois times (qualquer ordem); retorna sempre na ordem (t1, t2).
_SEP = r"\s*(?:x|×|-|–|a)\s*"
_GAP = r".{0,25}?"


def _placar_no_texto(texto: str, t1: str, t2: str) -> Optional[str]:
    tx, n1, n2 = _norm(texto), _norm(t1), _norm(t2)
    for a, b, invertido in ((n1, n2, False), (n2, n1, True)):
        m = re.search(
            re.escape(a) + _GAP + r"(\d{1,2})" + _SEP + r"(\d{1,2})" + _GAP + re.escape(b),
            tx,
        )
        if m:
            g1, g2 = m.group(1), m.group(2)
            return f"{g2}x{g1}" if invertido else f"{g1}x{g2}"
    return None


# ── Calendário / derivação de fase ───────────────────────────────────────────
def _carrega_calendario() -> dict:
    with open(DATA / "calendario_copa.json", encoding="utf-8") as f:
        return json.load(f)


def _selecoes() -> list[str]:
    """48 seleções (união de selecoes_por_confederacao) — âncora de reconhecimento."""
    with open(DATA / "selecoes_classificadas.json", encoding="utf-8") as f:
        d = json.load(f)
    nomes: list[str] = []
    for lista in (d.get("selecoes_por_confederacao") or {}).values():
        if isinstance(lista, list):
            nomes.extend(lista)
    return nomes


def _intervalos_fase(calendario: dict) -> list[tuple[str, dt.date, dt.date]]:
    out: list[tuple[str, dt.date, dt.date]] = []
    for f in calendario.get("fases", []):
        nome = f.get("fase", "?")
        ini = f.get("inicio") or f.get("inicio_aprox") or f.get("data")
        fim = f.get("fim") or f.get("fim_aprox") or f.get("data")
        if not ini or not fim:
            continue
        try:
            out.append((nome, dt.date.fromisoformat(ini), dt.date.fromisoformat(fim)))
        except ValueError:
            continue
    return out


def derivar_fase(data_iso: str, calendario: Optional[dict] = None) -> str:
    """Fase da Copa para uma data (cruza com calendario_copa.json). 'desconhecida' fora."""
    cal = calendario if calendario is not None else _carrega_calendario()
    try:
        alvo = dt.date.fromisoformat(data_iso)
    except (ValueError, TypeError):
        return "desconhecida"
    for nome, ini, fim in _intervalos_fase(cal):
        if ini <= alvo <= fim:
            return nome
    return "desconhecida"


# ── Datas ─────────────────────────────────────────────────────────────────
def _hoje_iso() -> str:
    return dt.date.today().isoformat()


def _ontem_iso() -> str:
    return (dt.date.today() - dt.timedelta(days=1)).isoformat()


def _data_extenso(data_iso: str) -> str:
    try:
        d = dt.date.fromisoformat(data_iso)
        return f"{d.day} de {_MESES_PT[d.month]} de {d.year}"
    except (ValueError, TypeError):
        return data_iso


# ── Brave: chamada de busca ──────────────────────────────────────────────────
def _brave_web(query: str, erros: list[str], n: int = 6) -> list[dict]:
    """Resultados crus da Brave Web Search. Levanta erro CLARO se sem chave."""
    key = require_brave_key()  # RuntimeError("BRAVE_API_KEY não configurada ...")
    r = requests.get(
        _BRAVE_WEB,
        headers={"Accept": "application/json", "X-Subscription-Token": key},
        params={"q": query, "count": n, "country": "br", "search_lang": "pt"},
        timeout=_TIMEOUT,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Brave HTTP {r.status_code} (q={query!r})")
    return (r.json().get("web") or {}).get("results", [])


# ── Extração dos fatos a partir dos snippets (puro, testável) ─────────────────
def _extrair_fato_jogo(times: list[str], resultados: list[dict]) -> Jogo:
    """Lê snippets de fontes confiáveis e extrai o placar com checagem de consenso.

    Regra anti-alucinação:
      - placar fixado só se >= 2 fontes confiáveis distintas concordam (concordam=True);
      - fonte única e sem conflito: placar registrado, mas concordam=False (a revisar);
      - conflito sem maioria: placar = None (dúvida → vazio, não chuta).
    """
    t1, t2 = times[0], times[1]
    # placar -> {labels:set, urls:list}
    candidatos: dict[str, dict[str, Any]] = {}
    fontes_dados: set[str] = set()
    fontes_urls: list[str] = []

    for r in resultados:
        url = r.get("url") or r.get("link") or ""
        rotulo = _dominio_confiavel(url)
        if not rotulo:
            continue  # ignora fonte não-confiável (blog/agregador aleatório)
        fontes_dados.add(rotulo)
        if url and url not in fontes_urls:
            fontes_urls.append(url)
        placar = _placar_no_texto(f"{r.get('title', '')} {r.get('description', '')}", t1, t2)
        if placar:
            slot = candidatos.setdefault(placar, {"labels": set(), "urls": []})
            slot["labels"].add(rotulo)
            if url:
                slot["urls"].append(url)

    placar: Optional[str] = None
    concordam = False
    if candidatos:
        ranked = sorted(candidatos.items(), key=lambda kv: len(kv[1]["labels"]), reverse=True)
        top_placar, top = ranked[0]
        n_top = len(top["labels"])
        empate = len(ranked) > 1 and len(ranked[1][1]["labels"]) == n_top
        if n_top >= 2 and not empate:
            placar, concordam = top_placar, True
        elif n_top == 1 and len(ranked) == 1:
            placar, concordam = top_placar, False  # fonte única, sem conflito

    fatos = f"{t1} {placar.replace('x', ' x ')} {t2}" if placar else f"{t1} x {t2}"
    return {
        "times": [t1, t2],
        "placar": placar,
        "data": "",
        "fatos_duros": fatos,
        "narrativa": "",
        "fonte": ["brave"],
        "fontes_dados": sorted(fontes_dados),
        "fontes_urls": fontes_urls,
        "fontes_concordam": concordam,
    }


def _extrair_narrativa(resultados: list[dict], max_trechos: int = 3) -> str:
    """História/emoção a partir das descrições de fontes confiáveis. '' se nada."""
    trechos: list[str] = []
    for r in resultados:
        if not _dominio_confiavel(r.get("url") or r.get("link") or ""):
            continue
        d = (r.get("description") or "").strip()
        if d:
            trechos.append(d)
        if len(trechos) >= max_trechos:
            break
    return " ".join(trechos).strip()


def _achar_selecao(trecho: str, norm_map: dict[str, str], do_fim: bool) -> Optional[str]:
    """Seleção reconhecida mais próxima da borda do trecho (fim p/ antes do placar)."""
    achados: list[tuple[int, str]] = []
    for nk, canon in norm_map.items():
        idx = trecho.rfind(nk) if do_fim else trecho.find(nk)
        if idx != -1:
            achados.append((idx, canon))
    if not achados:
        return None
    achados.sort(key=lambda t: t[0], reverse=do_fim)
    return achados[0][1]


def _extrair_confrontos(resultados: list[dict]) -> list[list[str]]:
    """Descobre confrontos (pares de seleções ladeando um placar) nos snippets.

    Reconhece nomes pela lista oficial (NER ancorado) — não descarta nada, só acha."""
    norm_map = {_norm(s): s for s in _selecoes()}
    pares: list[list[str]] = []
    vistos: set[tuple[str, str]] = set()
    for r in resultados:
        if not _dominio_confiavel(r.get("url") or r.get("link") or ""):
            continue
        tx = _norm(f"{r.get('title', '')} {r.get('description', '')}")
        for m in re.finditer(r"(\d{1,2})" + _SEP + r"(\d{1,2})", tx):
            antes = tx[max(0, m.start() - 30):m.start()]
            depois = tx[m.end():m.end() + 30]
            a = _achar_selecao(antes, norm_map, do_fim=True)
            b = _achar_selecao(depois, norm_map, do_fim=False)
            if a and b and a != b and (a, b) not in vistos:
                vistos.add((a, b))
                pares.append([a, b])
    return pares


# ── Brave: coleta por jogo (default de produção) ─────────────────────────────
def _brave_descobrir_confrontos(data_iso: str, erros: list[str]) -> list[list[str]]:
    res = _brave_web(f"resultados jogos Copa do Mundo {_data_extenso(data_iso)}", erros, n=10)
    confrontos = _extrair_confrontos(res)
    if not confrontos:
        erros.append(f"nenhum confronto reconhecido nos snippets de {data_iso}")
    return confrontos


def _brave_jogo(times: list[str], data_iso: str, erros: list[str]) -> Jogo:
    t1, t2 = times[0], times[1]
    fatos_res = _brave_web(f"{t1} x {t2} resultado Copa do Mundo 2026", erros)
    jogo = _extrair_fato_jogo(times, fatos_res)
    jogo["data"] = data_iso
    narr_res = _brave_web(f"{t1} {t2} Copa do Mundo 2026 como foi o jogo emoção", erros)
    jogo["narrativa"] = _extrair_narrativa(narr_res)
    return jogo


# ── Histórico (turno da tarde) ───────────────────────────────────────────────
# Sementes de busca = confrontos reais (só DIRECIONAM o Brave; fato/narrativa vêm
# sempre do retorno da busca, nunca da memória).
_TEMAS_HISTORICOS: list[dict] = [
    {"times": ["Brasil", "Alemanha"], "q": "Brasil 7x1 Alemanha 2014 o que aconteceu emoção"},
    {"times": ["Brasil", "Uruguai"], "q": "Maracanaço 1950 Brasil Uruguai derrota silêncio"},
    {"times": ["Itália", "Brasil"], "q": "Itália x Brasil 1982 Tragédia do Sarriá"},
    {"times": ["Holanda", "Brasil"], "q": "Holanda 2x1 Brasil 1974 virada futebol"},
    {"times": ["Brasil", "França"], "q": "Brasil 0x3 França 1998 final frustração"},
    {"times": ["Coreia do Sul", "Alemanha"], "q": "Coreia do Sul 2x0 Alemanha 2018 zebra"},
]


def _historico_brave(tema: dict, erros: list[str]) -> Jogo:
    res = _brave_web(tema["q"], erros, n=5)
    return {
        "times": list(tema["times"]),
        "placar": None,  # histórico não fixa placar de memória
        "data": "",
        "fatos_duros": "",
        "narrativa": _extrair_narrativa(res),
        "fonte": ["brave"],
        "fontes_dados": sorted({_dominio_confiavel(r.get("url", "")) or "" for r in res} - {""}),
        "fontes_urls": [r.get("url", "") for r in res if r.get("url")],
        "fontes_concordam": False,
    }


# ── Entradas do nó ───────────────────────────────────────────────────────────
def pesquisa_manha(
    state: dict,
    descobrir: Optional[Callable[[str, list[str]], list[list[str]]]] = None,
    buscar_jogo: Optional[Callable[[list[str], str, list[str]], Jogo]] = None,
) -> dict:
    """Jogos do dia anterior via Brave. Usa state['data_alvo'] se presente (testes)."""
    cal = _carrega_calendario()
    alvo = state.get("data_alvo") or _ontem_iso()
    state["data_alvo"] = alvo
    state.setdefault("data", _hoje_iso())
    state["fase_copa"] = derivar_fase(alvo, cal)
    erros = state.setdefault("erros", [])

    descobrir = descobrir or _brave_descobrir_confrontos
    buscar_jogo = buscar_jogo or _brave_jogo

    confrontos = descobrir(alvo, erros)
    jogos: list[Jogo] = []
    for times in confrontos:
        try:
            jogos.append(buscar_jogo(times, alvo, erros))
        except Exception as e:  # noqa: BLE001 — um jogo falhar não derruba o resto
            erros.append(f"jogo {times} falhou: {e!r}")
    state["jogos_pesquisados"] = jogos
    return state


def pesquisa_tarde(
    state: dict,
    buscar_hist: Optional[Callable[[dict, list[str]], Jogo]] = None,
    n: int = 2,
) -> dict:
    """Momentos históricos marcantes (sempre há material). Tarde produz exatamente n."""
    buscar_hist = buscar_hist or _historico_brave
    state.setdefault("data", _hoje_iso())
    state["fase_copa"] = derivar_fase(state["data"], _carrega_calendario())
    erros = state.setdefault("erros", [])

    base = dt.date.today().toordinal()  # rotação determinística por dia (sem random)
    temas = [_TEMAS_HISTORICOS[(base + i) % len(_TEMAS_HISTORICOS)] for i in range(n)]
    jogos: list[Jogo] = []
    for t in temas:
        try:
            jogos.append(buscar_hist(t, erros))
        except Exception as e:  # noqa: BLE001
            erros.append(f"histórico {t['times']} falhou: {e!r}")
    state["jogos_pesquisados"] = jogos
    return state


# ── Pesquisa genérica por pilar (não-futebol) ────────────────────────────────
def pesquisa_pilar(
    state: dict,
    buscar: Optional[Callable[[str], list[dict]]] = None,
    por_query: int = 8,
    top: int = 12,
) -> dict:
    """Momentos com carga emocional de um pilar NÃO-futebol (genérico).

    ÂNCORA POR CONSENSO (anti-alucinação sem lista fixa): pilares como cultura pop,
    música e datas não têm lista fechada (influencers/músicas mudam toda semana).
    Então a âncora é a REGRA: cada momento carrega quantas FONTES DISTINTAS da Brave
    o confirmaram (`n_fontes` = domínios únicos; `fontes_confiaveis` = os do mapa do
    pilar) e `fontes_concordam` (≥2 fontes). O seletor descarta quem não tem consenso
    — o fato vem da pesquisa, nunca da memória do LLM.

    Lê pilar_ativo/pilar_config do state, roda as queries do pilar (`queries_do_pilar`)
    na Brave e extrai 'momentos' (entidades + narrativa). Popula `jogos_pesquisados`
    no mesmo formato do seletor, sem times. Costura `buscar(query)->snippets` p/ teste.
    """
    from engine.nodes.coletor_tendencias import extrair_candidatos  # reuso do NER

    pilar = state.get("pilar_ativo", "futebol")
    cfg = state.get("pilar_config") or {}
    fontes_pilar = fontes_do_pilar(pilar)  # domínio→rótulo do pilar (bônus de confiança)
    state.setdefault("data", _hoje_iso())
    state.setdefault("fase_copa", "")
    erros = state.setdefault("erros", [])

    def _buscar_default(q: str) -> list[dict]:
        return _brave_web(q, erros, n=por_query)

    buscar = buscar or _buscar_default

    # momento_norm -> {momento, ocorr, narrativa, urls, dominios(set), confiaveis(set)}
    agrega: dict[str, dict[str, Any]] = {}
    for q in queries_do_pilar(pilar, cfg):
        try:
            snippets = buscar(q)
        except Exception as e:  # noqa: BLE001 — uma query falha não derruba o pilar
            erros.append(f"pesquisa pilar {pilar} query {q!r} falhou: {e!r}")
            continue
        for s in snippets:
            url = s.get("url") or s.get("link") or ""
            dominio = _dominio_de(url)
            rotulo = _dominio_confiavel(url, fontes_pilar)
            texto = f"{s.get('title', '')} {s.get('description', '')}".strip()
            desc = (s.get("description") or "").strip()
            for termo in extrair_candidatos(texto):
                ch = _norm(termo)
                d = agrega.setdefault(ch, {"momento": termo, "ocorr": 0, "narrativa": "",
                                           "urls": [], "dominios": set(), "confiaveis": set()})
                d["ocorr"] += 1
                if dominio:
                    d["dominios"].add(dominio)
                if rotulo:
                    d["confiaveis"].add(rotulo)
                if not d["narrativa"] and desc:
                    d["narrativa"] = desc
                if url and url not in d["urls"]:
                    d["urls"].append(url)

    # Ranqueia por CONSENSO primeiro: nº de fontes distintas > fontes confiáveis > ocorrências.
    ranq = sorted(
        agrega.values(),
        key=lambda d: (len(d["dominios"]), len(d["confiaveis"]), d["ocorr"]),
        reverse=True,
    )[:top]
    momentos: list[Jogo] = []
    for d in ranq:
        n_fontes = len(d["dominios"])
        momentos.append({
            "times": [],
            "momento": d["momento"],
            "placar": None,
            "data": state["data"],
            "fatos_duros": d["momento"],
            "narrativa": d["narrativa"],
            "fonte": ["brave"],
            "fontes_dados": sorted(d["dominios"]),
            "fontes_confiaveis": sorted(d["confiaveis"]),
            "fontes_urls": d["urls"],
            "n_fontes": n_fontes,
            "fontes_concordam": n_fontes >= 2,  # consenso multi-fonte
            "pilar": pilar,
        })
    state["jogos_pesquisados"] = momentos
    return state


# ════════════════════════════════════════════════════════════════════════════
# FALLBACK DIRETO SofaScore/FotMob — DESATIVADO (bloqueiam o IP do VPS).
# Preservado para reativar caso um dia haja proxy residencial. NÃO está no
# caminho padrão; `coletar_jogos_do_dia` só roda se _FALLBACK_DIRETO_ATIVO=True.
# ════════════════════════════════════════════════════════════════════════════
_FALLBACK_DIRETO_ATIVO = False
_SOFASCORE_WC_ID = 16
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def _ts_para_iso(ts: Any, fallback: str) -> str:
    try:
        return dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return fallback


def _normalizar_sofascore(events: list[dict], data_iso: str) -> list[Jogo]:
    """[DESATIVADO] Eventos crus do SofaScore -> schema normalizado (só Copa)."""
    jogos: list[Jogo] = []
    for ev in events:
        ut = (ev.get("tournament") or {}).get("uniqueTournament") or {}
        nome = ((ev.get("tournament") or {}).get("name") or "").lower()
        if ut.get("id") != _SOFASCORE_WC_ID and "world cup" not in nome and "copa do mundo" not in nome:
            continue
        home = (ev.get("homeTeam") or {}).get("name")
        away = (ev.get("awayTeam") or {}).get("name")
        if not home or not away:
            continue
        status = ev.get("status") or {}
        hs = (ev.get("homeScore") or {}).get("current")
        as_ = (ev.get("awayScore") or {}).get("current")
        tem = status.get("type") in ("finished", "inprogress") and hs is not None and as_ is not None
        jogos.append({
            "times": [home, away],
            "placar": f"{hs}x{as_}" if tem else None,
            "data": _ts_para_iso(ev.get("startTimestamp"), data_iso),
            "fatos_duros": (f"{home} {hs}x{as_} {away}" if tem else f"{home} x {away}"),
            "narrativa": "",
            "fonte": ["sofascore"],
        })
    return jogos


def _sofascore_jogos(data_iso: str, erros: list[str]) -> list[Jogo]:
    """[DESATIVADO] GET dos jogos do dia no SofaScore (403 no VPS)."""
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_iso}"
    r = requests.get(url, headers=_BROWSER_HEADERS, timeout=_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"sofascore HTTP {r.status_code}")
    return _normalizar_sofascore(r.json().get("events", []), data_iso)
