# SETUP — rodar o FocusClear do zero (Mac)

Guia acionável pra subir backend + frontend numa máquina limpa (Mac Mini M4, macOS).

## 1. Clonar + ambiente Python

```bash
git clone https://github.com/theuxld23-ctrl/focusclear-carrossel.git
cd focusclear-carrossel
python3 -m venv venv
source venv/bin/activate            # dentro do venv, 'python' aponta pro venv
pip install -r requirements.txt
playwright install chromium         # navegador do compositor (carrossel/motion/reel)
```

> Sem ativar o venv, use `./venv/bin/python …` diretamente.

## 2. Configurar o `.env`

Copie o exemplo e preencha as chaves:

```bash
cp .env.example .env
```

| Chave | Pra quê | Obrigatória? |
|-------|---------|--------------|
| `BRAVE_API_KEY` | **Fonte única de dados** (pesquisa + tendências). Sem ela o motor não roda de verdade. | Sim (p/ execução real) |
| `LLM_PROVIDER` | `groq` ou `anthropic` — qual LLM usar no seletor/roteirista. | Sim |
| `GROQ_API_KEY` / `GROQ_MODEL` | LLM Groq (`llama-3.3-70b-versatile`). | Se `LLM_PROVIDER=groq` |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | LLM Anthropic (`claude-sonnet-4-6`). | Se `LLM_PROVIDER=anthropic` |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Notificação do batch pronto. Vazio = pula em silêncio. | Não |
| `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` | Voz do reel. Vazio = reel sai sem narração. | Não |
| `HEYGEN_API_KEY` / `HEYGEN_AVATAR_ID` | Avatar (talking-head) do reel. Vazio = reel só com b-roll. | Não |
| `PALMIER_MCP_URL` | Editor de vídeo (MCP, `POST http://127.0.0.1:19789/mcp`). | Não |

> A aba **Config** do painel mostra o status de cada chave e valida ao vivo
> (botão "Validar ao vivo") as que estiverem preenchidas — **nunca** edita o `.env`.

## 3. Subir o backend (porta 8010)

```bash
source venv/bin/activate
uvicorn backend.main:app --port 8010
```

No boot: cria as tabelas, semeia os workspaces (`focusclear` + `demo`) e sobe o
APScheduler (batches 06h/13h + coleta de tendências 05h, fuso de São Paulo).

## 4. Subir o frontend (porta 3010)

```bash
cd frontend
npm install
npm run dev
```

Abra **http://localhost:3010**. O frontend fala com o backend via rewrite
`/api/* → :8010` (sem CORS). O seletor de **workspace** fica no canto direito do
menu.

> Os rewrites em `frontend/next.config.mjs` são **explícitos** (não catch-all):
> ao criar uma rota nova no backend, adicione a entrada correspondente lá.

## 5. Testes

```bash
source venv/bin/activate
python -m tests.test_data        # ETAPA 0 OK   (dados validados)
python -m tests.test_pesquisa    # ETAPA 1 OK   (nó de pesquisa)
python -m tests.test_telegram    # TELEGRAM OK
python -m tests.test_reel        # REEL OK
python -m tests.test_tendencias  # TENDENCIAS OK
python -m tests.test_motion      # MOTION OK
python -m tests.test_pilares     # PILARES OK
python -m tests.test_workspace   # WORKSPACE OK
python -m tests.test_pipeline    # PIPELINE OK   (8 slides, luminância escuro→luz)
# ou tudo de uma vez:
pytest tests/
```

## 6. Seed de demonstração (opcional)

Popula o workspace `demo` com jobs/tendências de exemplo (isolados do `focusclear`):

```bash
python -m backend.seed_demo
```

## Portas & comandos rápidos

| O quê | Comando | Porta |
|-------|---------|-------|
| Backend | `uvicorn backend.main:app --port 8010` | 8010 |
| Frontend | `cd frontend && npm run dev` | 3010 |
| Motor (CLI) | `python -m engine.run --turno manha --pilar futebol` | — |

Arquitetura e fluxo dos nós: veja **[ARQUITETURA.md](ARQUITETURA.md)**.
