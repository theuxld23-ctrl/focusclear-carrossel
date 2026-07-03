# ARQUITETURA — FocusClear Content Engine (5 minutos)

Sistema que transforma momentos de carga emocional (futebol, cultura pop…) em
conteúdo de saúde mental (carrossel, reel, motion) pelo método **espelho emocional**.
Humano revisa e posta — o sistema **nunca** publica sozinho na v1.

## Camadas

```
frontend/ (Next.js :3010)  ── /api/* rewrite ──▶  backend/ (FastAPI :8010)
   painel de operação                              API + scheduler + persistência
                                                        │
                                                        ▼
                                                   engine/ (o motor)
                                                   nós + dados + templates
```

- **frontend/** — 8 abas (Criar, Biblioteca, Fila, Tendências, Pilares, Personagem,
  Métricas, Config) + seletor de workspace. Fala com o backend via rewrite
  `/api/* → :8010` (`next.config.mjs`, rewrites **explícitos**).
- **backend/** — FastAPI. `routers/` (endpoints), `services/job_service.py`
  (orquestra o pipeline), `scheduler.py` (APScheduler), `database.py` (SQLite +
  SQLAlchemy, tudo com `workspace_id`).
- **engine/** — o motor, agnóstico de backend. `nodes/` (1 arquivo por nó),
  `data/` (JSONs = fonte de verdade, **não alterar**), `templates/fonts/` (só as fontes
  woff2; o HTML do slide é gerado em código por `compositor.build_html`).

## O pipeline (orquestração sequencial em Python)

> **Não é LangGraph.** Os nós são chamados em ordem por `backend/services/job_service.py`
> (`executar_job`), que ramifica por formato. "LangGraph" no briefing é meta futura, não
> implementada.

```
pesquisa → coleta_imagens → seletor(LLM) → roteirista(LLM) → resolve_imagens → [saída] → telegram
```

| Nó | Faz | LLM? |
|----|-----|------|
| `pesquisa` | Base factual via Brave. Futebol: jogos/históricos. Outros pilares: `pesquisa_pilar` (queries do pilar). | não |
| `coleta_imagens` | Cataloga imagens candidatas por momento (Brave Images). | não |
| `seletor` | Valida fatos **em código** (âncora por pilar) e casa momento↔perfil. | sim |
| `roteirista` | Escreve os 8 slides (jornada escuro→luz). | sim |
| `resolve_imagens` | Executa a cascata de imagem por slide. | não |
| `compositor` / `reel_compositor` / `motion_compositor` | Renderiza a saída (Playwright). | não |
| `telegram` | Notifica o batch pronto (não entrega/publica). | não |

Anti-alucinação (princípio #1): a validação factual roda **em código antes do LLM**
(`seletor.validar_factual`). LLM sempre via `config.get_llm()` (plugável).

## Saída por formato (o ramo muda depois do seletor)

- **carrossel** → `roteirista → resolve_imagens → compositor` → 8 PNGs 1080×1350.
- **reel** → `roteirista_video → voz(ElevenLabs) → avatar(HeyGen) → reel_compositor`
  → vídeo 9:16 (ou webm placeholder via Chromium, sem ffmpeg).
- **motion** → `roteirista → resolve_imagens → motion_compositor` → carrossel com
  1-2 slides animados (webm, Ken Burns via CSS capturado pelo Chromium).

Cada nó é **testável offline** por costuras injetáveis (sem rede/LLM). Chaves
vazias → o nó pula com placeholder + log (nunca quebra o pipeline).

## Pilares (multi-conteúdo)

O motor é agnóstico de pilar: processa "momentos com carga emocional". Um pilar =
entrada em `engine/data/pilares.json` + fontes de pesquisa. Pilares **ativos vêm
do banco** (`/pilares`); o scheduler cria 1 job por pilar ativo. v1: `futebol`
funcional ponta-a-ponta; `cultura_pop`/`musica_popular`/`datas_sazonais` prontos
p/ ativar. Sem pilar ativo → default futebol (retrocompat).

## Banco (SQLite, tudo com `workspace_id`)

`workspaces, pilares, jobs, assets, tendencias, agenda, personagens`. Isolamento
multi-workspace v1 = **filtro no banco, sem auth** (quem acessa o Mac acessa tudo).
Seed no boot: workspaces `focusclear` + `demo`. Todo endpoint de lista filtra por
`workspace_id`; o frontend passa o workspace ativo em cada chamada.

## Onde mexer

| Quero… | Vou em… |
|--------|---------|
| Mudar o texto/tom dos slides | `engine/data/prompts/roteirista.md` |
| Ajustar critério de seleção | `engine/data/prompts/seletor.md` + `seletor.py` |
| Trocar visual do slide | `engine/nodes/compositor.py` + `engine/templates/` |
| Adicionar um pilar | `engine/data/pilares.json` (+ queries em `pesquisa.py`) |
| Novo endpoint | `backend/routers/` + registrar em `backend/main.py` + rewrite em `next.config.mjs` |
| Nova aba do painel | `frontend/app/<aba>/page.tsx` + link em `frontend/components/Nav.tsx` |

Como rodar tudo: veja **[SETUP.md](SETUP.md)**.
