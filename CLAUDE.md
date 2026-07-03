# FocusClear Carrossel Engine

Sistema autônomo que gera carrosséis de Instagram sobre futebol que funcionam como **espelho emocional de saúde mental** para o público popular brasileiro, usando a Copa 2026 como gancho. Roda no VPS 24/7. Produz e entrega no Telegram; **humano (Matheus) revisa e posta — o sistema NUNCA publica sozinho na v1.**

## STATUS DA MIGRAÇÃO
- Data: 2026-07-03
- Máquina principal: Mac Mini M4, macOS Tahoe
- VPS: permanece ativa (outros projetos — não desligar)
- Ambiente: venv Python 3.14.5, deps do requirements.lock.txt
- Testes offline: ETAPA 0 ✅  ETAPA 1 ✅
- SofaScore: BLOQUEADO (HTTP 403 mesmo em IP residencial) — Brave permanece como fonte principal
- Palmier Pro: v0.5.2 instalado, MCP http://127.0.0.1:19789/mcp (endpoint JSON-RPC via POST; `/mcp/health` não existe nesta versão)
- APIs: pendentes — .env criado vazio
- ✅ Fase 1 — Backend como serviço: FastAPI (`backend/`) + SQLite (`focusclear.db`, gitignored) + APScheduler (batches 06h/13h BRT). Tabelas com `workspace_id`; seed workspace `focusclear`. Endpoints: `/health`, `/jobs` (dispara motor em bg), `/assets`. Rodar: `uvicorn backend.main:app --port 8010`.
- ✅ Frontend core — Next.js 14.2.35 + Tailwind (`frontend/`, porta **3010**). Abas: `/criar` (form + polling do job a cada 2s), `/biblioteca` (assets + PATCH de aprovação), `/fila` (jobs recentes, auto-refresh 3s). Consome o backend via **rewrite `/api/* → :8010`** (evita CORS; `next.config.mjs` usa rewrites explícitos p/ preservar a barra final que o FastAPI exige — client chama sem barra). Design CTec: carbon #0D0D10, electric #1B4FFF, Space Grotesk + Inter Tight. Rodar: `cd frontend && npm run dev`.
- ✅ Pipeline completo do motor (`engine/nodes/`): pesquisa → **coleta_imagens** → **seletor** → **roteirista** → **resolve_imagens** → **compositor** → **telegram**. Seletor faz validação factual EM CÓDIGO (âncora `selecoes_classificadas.json`) antes do LLM; LLM sempre via `get_llm()`. Compositor renderiza 8 slides 1080×1350 (jornada escuro→luz) com Playwright — tipografia **Big Shoulders Display + Young Serif** embutidas em base64 (`engine/templates/fonts/`, offline), safe-zone central 1080×1080. `job_service.executar_job` roda o pipeline e salva Asset tipo `slide` por PNG em `engine/output/` (gitignored). Teste offline `python -m tests.test_pipeline` → "PIPELINE OK" (8 PNGs, luminância 39→173). Nós testáveis com costuras injetáveis (sem rede).
- ✅ Telegram vira **notificação, não entrega** (`engine/nodes/telegram.py`): com `TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID` no `.env`, envia metadados + álbum dos PNGs + legenda copiável ("batch pronto, revise no painel"); `perfil=trauma` adiciona aviso de revisão médica; **sem chaves pula em silêncio** (o painel é o canal primário). `python -m tests.test_telegram` → "TELEGRAM OK".
- ✅ Preview real na Biblioteca: backend `GET /assets/{id}/image` serve o PNG por file path (valida path dentro de `engine/output`); frontend agrupa os slides por carrossel e mostra um **CarrosselPreview** navegável (setas + swipe + dots, 4:5) — aprovar avança o carrossel inteiro. Assets legados sem PNG viram placeholder.
- ✅ **8 abas completas** no frontend. As 5 novas: `/tendencias` (placeholder Brave + "criar a partir disso" → `/criar?tema=&pilar=`), `/pilares` (CRUD: ativar/desativar + editar config JSON), `/personagem` (config avatar + upload foto local em `engine/assets/` gitignored + preview placeholder Fase 3), `/metricas` (placeholder Graph API), `/config` (status das chaves do `.env`, mascarado, read-only). Backend: routers `pilares` (GET+PATCH), `tendencias` (GET), `personagem` (GET/PUT/foto), `integracoes` (`GET /config`). Nova tabela `personagens`; `init_db` semeia `pilares` a partir de `pilares.json`.
- 📖 **Briefing Mestre v1.1** (fonte de verdade do produto) em `docs/BRIEFING_MESTRE.md`. Roadmap: FASE 3 ✅, FASE 4 = Tendências+Motion, FASE 5 = lógica real Pilares/Personagem/Config (UI ✅ feita), FASE 6 = produto-ready.
- ✅ Reconciliado com o briefing v1.1: pilar 2 agora é `cultura_pop` ("Cultura Pop / Fofoca", Novela vira subpilar) em `pilares.json`; brasa unificada em `#FF5436` (compositor + template). Seed lê o slug do JSON; `test_data` espera `cultura_pop`.
- ✅ **FASE 3 — motor de vídeo (Reel)**, 2º output do mesmo motor. `formato="reel"`: pesquisa → coleta_imagens → seletor → **roteirista_video** (prompt = roteirista.md + adendo; 5 beats gancho≤14→tensão→espelho→virada+alívio→CTA+loop, 70-110 palavras) → **voz** (ElevenLabs) → **avatar** (HeyGen) → **reel_compositor** (poster 9:16 1080×1920 + manifest + montagem Palmier MCP→ffmpeg→**webm placeholder via Chromium**, offline sem ffmpeg). Chaves vazias (ElevenLabs/HeyGen) → nós pulam com placeholder + log. Asset tipo `reel` com metadado label "conteúdo gerado por IA". Endpoint de arquivo agora serve vídeo (content-type por extensão). `/biblioteca`: reel = player `<video>`, carrossel = slides. `python -m tests.test_reel` → "REEL OK". Nós de carrossel intocados. Obs: ffmpeg NÃO instalado nesta máquina (placeholder usa gravação webm do Playwright); Palmier MCP no ar mas montagem completa via MCP só quando houver mídia de avatar/áudio.
- ✅ **FASE 4 — Tendências + Motion**. **Parte 1 (Tendências):** `engine/nodes/coletor_tendencias.py` coleta na Brave por pilar (queries relevantes em `_QUERIES_POR_PILAR`: futebol/cultura_pop/musica_popular/datas_sazonais), extrai entidades dos snippets (`extrair_candidatos`), pontua por frequência + fonte confiável + recência (`score = ocorr*10 + fontes*5 + recencia*3`, int) e ranqueia; costura `buscar` injetável, **sem `BRAVE_API_KEY` pula sem erro** e retorna `[]`. `backend/scheduler.py` roda `job_tendencias` (cron 05h, no scheduler existente): coleta por pilar ativo e **substitui** as linhas de `Tendencia`. `/tendencias` já renderiza cards reais do banco (placeholder "Conecte a Brave" só quando vazio). **Parte 2 (Motion):** `engine/nodes/motion_compositor.py` reaproveita `build_html` do compositor (sem tocá-lo) — slides 1 e 5 viram **webm** com Ken Burns/rise via **CSS animation capturada pelo Chromium** (v1 sem Kling/Seedance), demais slides PNG; costuras `render_png`/`gravar_webm` injetáveis. `job_service`: `formato="motion"` → pipeline normal + `compor_motion` → Asset tipo `motion` (flag `animado` por slide). Frontend: `CarrosselPreview` renderiza `<video>` p/ slide `.webm/.mp4`; `/biblioteca` agrupa motion por pasta em card navegável com badge "motion" (mostra os 3 tipos: carrossel, reel, motion). Testes offline `python -m tests.test_tendencias` → "TENDENCIAS OK" e `python -m tests.test_motion` → "MOTION OK"; suites anteriores seguem passando. Nós de carrossel e reel intocados.
- ✅ **FASE 5 — Pilares + Personagem + Config funcionais** (a UI já existia; agora a lógica é real). **Parte 1 (Pilares):** pilares ATIVOS vêm do banco, não hardcoded. `engine/nodes/pesquisa.py` ganhou `pesquisa_pilar()` genérico (não-futebol): lê `pilar_ativo`/`pilar_config` do state e usa as queries do próprio pilar (`queries_do_pilar` = mapa por slug em `_QUERIES_MOMENTO_POR_PILAR` + derivação do `carga_emocional` do config), extrai "momentos" dos snippets Brave (reusa `extrair_candidatos`). `seletor.py`: `validar_factual` é **pilar-aware** — futebol mantém a âncora das 48 seleções; outros pilares aceitam momentos com conteúdo (âncora fechada ainda não existe → julgamento fica no LLM); `_casa_jogo` religa momento→aprovado p/ preservar narrativa; `selecionar` lê `pilar_ativo`. `coleta_imagens._queries_do_jogo` cai p/ o `momento` quando não há times. `job_service` injeta `pilar_config` do banco e faz **dispatch** da pesquisa (futebol=turnos manhã/tarde; demais=`pesquisa_pilar`). `scheduler` cria 1 job por pilar ATIVO (`pilares_ativos()` lê o banco; retrocompat: sem ativo → futebol). Frontend `/criar` lista só pilares ativos (via `/pilares`). **Parte 2 (Personagem):** `job_service` injeta a foto de referência e `voice_id`/tom do personagem (banco) no state; `avatar.py` já lia `state['avatar_foto']`, `voz.py` agora lê o `voice_id` de `state['voz_config']` (banco tem prioridade sobre o `.env`); router + UI `/personagem` ganharam o campo `voice_id` (salvo em `Personagem.config`). **Parte 3 (Config):** `integracoes.py` — `GET /config` expõe `status` (pendente/configurada); novo `GET /config/validar` testa AO VIVO só as chaves PREENCHIDAS (Brave/LLM/Telegram) → ativa|invalida|configurada|pendente; **nenhuma chamada externa se a chave não existir**; read-only (nunca edita `.env`). `next.config.mjs` ganhou rewrite p/ `/api/config/validar`. `/config` UI: botão "Validar ao vivo" + status colorido real. Teste offline `python -m tests.test_pilares` → "PILARES OK" (cultura_pop usa queries de cultura pop, sem rede/LLM). Suites anteriores seguem passando. Nós de carrossel/reel/motion **intocados na estrutura** — só leitura de config.
- ✅ **FASE 6 — Polimento + produto-ready (v1.0.0)**. **Parte 1 (Multi-workspace):** isolamento no banco, **sem auth** (v1 = quem acessa o Mac acessa tudo). `database.py` semeia 2 workspaces no boot (`focusclear` + `demo`) com pilares por workspace (`_seed_pilares(ws)`); novo `routers/workspaces.py` (`GET /workspaces`). Frontend: `lib/workspace.ts` (workspace ativo no `localStorage`; `comWorkspace()` anexa `?workspace_id=`); `api.ts` passa `workspace_id` em toda chamada com escopo (jobs/assets/pilares/tendencias/personagem); `Nav` ganhou **seletor de workspace** (trocar recarrega a página); rewrite `/api/workspaces` no next.config. `backend/seed_demo.py` (`python -m backend.seed_demo`) popula o `demo` com jobs/tendências de exemplo (idempotente, sem API externa). **Parte 2 (Export):** `components/ExportMenu.tsx` — por asset, "Baixar para Instagram/TikTok/YouTube Shorts" (download do arquivo nativo via `<a download>`; mesma resolução hoje, estrutura pronta p/ ajustes por plataforma), nos 3 tipos de card da `/biblioteca`. **Parte 3 (Docs):** `docs/SETUP.md` (subir do zero no Mac: venv, deps, `.env` por chave, portas, testes, seed) + `docs/ARQUITETURA.md` (camadas, 7 nós, fluxo por formato, onde mexer — 5 min). **Parte 4 (Limpeza):** sem TODO/FIXME reais; `.gitignore` cobre `.env`/`*.db`/`node_modules`/`.next`/`venv`/`output`/`assets` (verificado com `git check-ignore`). Teste `python -m tests.test_workspace` → "WORKSPACE OK". **9 suites passando** (test_data, pesquisa, telegram, reel, tendencias, motion, pilares, workspace, pipeline). Isolamento verificado E2E (dados do `demo` não aparecem no `focusclear` e vice-versa; export baixa o arquivo). Tag de release **`v1.0.0`** na main.

## Ambiente (venv)

O VPS só tem `python3` (não há `python` no PATH). O projeto usa um **virtualenv** em `venv/` — dentro dele `python` funciona. **Ative o venv antes de qualquer comando:**

```bash
cd /root/focusclear-carrossel
source venv/bin/activate     # agora 'python' aponta pro venv
# ... rodar comandos ...
deactivate                   # ao terminar (opcional)
```

Setup inicial (já feito; refazer só se recriar a máquina):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # binário do navegador p/ o compositor (etapa do compositor)
```

Sem ativar o venv, use o interpretador dele diretamente: `./venv/bin/python -m tests.test_data`.

## Comandos

> Todos assumem o **venv ativado** (`source venv/bin/activate`).

```bash
python -m tests.test_data                        # valida dados (etapa 0) — inclui pilares.json
python -m engine.run --turno manha               # momentos do dia anterior (pilar padrão: futebol)
python -m engine.run --turno tarde               # momentos históricos
python -m engine.run --turno manha --pilar futebol   # pilar explícito (default futebol se omitido)
pytest tests/                                    # roda todos os testes
playwright install chromium                      # setup do compositor (uma vez)
```

> `--pilar` (spec da Etapa 6 / entrypoint, ainda não construído): o entrypoint carrega a entrada do pilar de `pilares.json` no início e injeta `pilar_ativo` + `pilar_config` no state. Default `futebol`. v1: só `futebol` funcional de ponta a ponta.

## Arquitetura (pipeline de 7 nós, LangGraph)
```
cron 06h/13h → pesquisa → coleta_imagens → seletor(LLM) → roteirista(LLM) → resolve_imagens → compositor(Puppeteer) → telegram
```
- Nós determinísticos: pesquisa, imagem, compositor, telegram. Só **seletor** e **roteirista** chamam LLM.
- `manha`: momentos de ontem (newsjacking). `tarde`: 2 momentos históricos.
- Fan-out no seletor: 1 execução → N carrosséis.

## Camada de PILARES (multi-conteúdo)
O sistema não é só futebol — "futebol" é UM pilar de vários. **O MOTOR (seletor→roteirista→cascata→compositor→telegram) é AGNÓSTICO:** processa "momentos com carga emocional" vindos de um pilar, sem saber o que é futebol. Adicionar um pilar novo = adicionar entrada em `pilares.json` + fonte de pesquisa, **SEM tocar em seletor/roteirista/compositor**.
- `engine/data/pilares.json` define os pilares em `pilares{}` (cada um com `status`/`prioridade`) + um bloco `rotacao`. **v1: só `futebol` ativo e funcional** (prioridade 1); `novela_reality`/`musica_popular`/`datas_sazonais` = `status: planejado` (arquitetura pronta, ativados depois). Urgência: a Copa acaba **19/jul/2026** — o pilar futebol pivota pra clubes (Brasileirão/Libertadores/Champions, âncora `competicoes_clubes.json` a criar) e um 2º pilar precisa existir antes disso pra conta não secar.
- Cada pilar traz: `ancora_factual` (contra o que a validação factual do seletor confere), `fontes_pesquisa` (quais fontes o nó de pesquisa consulta), `tipo_momento`, `carga_emocional` (dores típicas → casam com os perfis), `validade`, `cuidado`.
- `rotacao`: não saturar um pilar; em transição (ex: fim da Copa) o seletor pode rodar 2 pilares até um assumir.
- `state.pilar_ativo` (str, default "futebol" — não há campo `pilar_padrao` no JSON; o default é do entrypoint) + `state.pilar_config` (dict, a entrada do pilar em `pilares.json`) atravessam o pipeline.
- Seletor: valida os fatos contra a `ancora_factual` DO PILAR (futebol = `selecoes_classificadas.json`) e casa perfil via `criterio_de_casamento` (genérico) + `carga_emocional` do pilar.
- Pesquisa: fontes confiáveis por pilar em `_FONTES_POR_PILAR` (v1 só futebol no caminho de produção); mesma lógica de consenso multi-fonte, só troca QUAIS fontes.

## Princípios inegociáveis
1. **Anti-alucinação = prioridade máxima.** Fatos de futebol SEMPRE de pesquisa (Brave/SofaScore), NUNCA da memória do LLM. Validação factual roda em CÓDIGO antes do LLM (dupla camada): todo time tem que estar em `selecoes_classificadas.json`, senão descarta.
2. **Lei anti-genérico.** Qualidade > volume. 1 carrossel forte > 3 mornos.
3. **LLM plugável.** SEMPRE via `config.get_llm()`. NUNCA hardcode Groq/Claude.
4. **Ético.** Perfil `trauma` → flag `requer_revisao_medica` + aviso no Telegram. Zero jargão clínico. Linguagem da experiência ("o que você sente"), nunca da condição ("você tem X").
5. **Simplicidade.** Funções pequenas, sem over-engineering. Cada nó testável isolado.

## Estrutura
```
config.py          # chaves + get_llm() plugável
state.py           # CarrosselState (TypedDict)
venv/              # virtualenv (gitignored)
engine/
  nodes/           # 1 arquivo por nó (pesquisa, imagem, seletor, roteirista, compositor, telegram)
  data/            # JSONs e prompts — FONTE DE VERDADE, não alterar
  templates/       # slide.html (compositor)
  output/          # PNGs (gitignored)
  graph.py         # monta o LangGraph
  run.py           # entrypoint --turno
tests/             # 1 teste por etapa
```

## Dados (engine/data/ — fonte de verdade validada, NÃO inventar)
- `pilares.json` — camada de pilares (ver seção "Camada de PILARES"). `pilares{}` (futebol=ativo/prioridade 1; novela_reality/musica_popular/datas_sazonais=planejado) + `rotacao`. Cada pilar: nome, status, prioridade, descricao, ancora_factual, fontes_pesquisa, tipo_momento, carga_emocional, validade, cuidado.
- `ponte_emocional.json` — 5 perfis (ansiedade, burnout, trauma, hiperfoco, ahsd) nas chaves de topo (+ metadados `_doc`, `_angulos_transversais`). Cada perfil: emocao_nucleo, experiencia_em_linguagem_popular, **`criterio_de_casamento`** (AGNÓSTICO de pilar: descreve a DOR via `a_dor` + `procurar_por_generico`; a inteligência de futebol vira `exemplos_por_pilar.futebol`, com 1-2 exemplos de outro pilar), subgeracoes_alvo, tom_por_subgeracao, linha_alivio_o_premio, cta_emocional, restricoes_eticas. `trauma.restricoes_eticas.nivel_cuidado` = "ALTO — revisão médica obrigatória". SEM lista fixa de momentos — o sistema pesquisa.
- `matriz_subgeracao.json` — 7 subgerações (snake_case; z_ponte é o pilar).
- `selecoes_classificadas.json` — 48 seleções da Copa em `selecoes_por_confederacao` (espelhadas em `grupos` A–L; campo `total`=48). ÂNCORA factual. Itália/Nigéria/Chile NÃO estão (ficam em `ausencias_notaveis`).
- `calendario_copa.json` — fases + emoção dominante de cada fase.
- `estrategia_imagem.md` — cascata de imagem (6 níveis).
- `regras_fluxo.md` — Telegram, trauma, turnos.
- `prompts/seletor.md`, `prompts/roteirista.md` — system prompts dos nós LLM.

## O carrossel (8 slides, jornada escuro→luz)
1 GANCHO (futebol, escuro) · 2 DADO/NÚMERO (escuro, estatística salvável) · 3 ESPELHO (escuro, nomeia a dor) · 4 PARTICIPAÇÃO (transição, enquete 3 opções) · 5 VIRADA (futebol→mente, a luz entra) · 6 PROVA (luz, reconhecimento/superação) · 7 ALÍVIO (luz quente, "isso tem nome" + micro-CTA salvar) · 8 CTA (luz quente, "siga @focusclear"). A jornada escuro→luz e o método espelho emocional são inalterados — só a contagem de funções mudou (6→8). Se o material não render 8 fortes, o roteirista cai pra 6 e declara em `formato_usado` (melhor 6 fortes que 8 fracos).

**Canvas 4:5 — 1080×1350** (era 1:1 1080×1080; ocupa ~35% mais tela no feed). **Safe-zone central obrigatória:** texto crítico e foco visual ficam dentro do quadrado central 1080×1080 (offset de 135px no topo e 135px na base). No grid do perfil o 4:5 é cortado pra o 1080×1080 central — o que ficar nos 135px de topo/base some no grid; esses 135px servem só pra respiro visual / extensão de foto, nunca pra texto essencial. Quando a Etapa 5 (compositor) for construída, `slide.html` nasce em 1080×1350 com a safe-zone. Tipografia Big Shoulders Display (display) + Young Serif (virada). Paleta: brasa-noite #0D0B0F, refletor #F2EBDD, brasa #FF5436, pele #E3A87C.

**Ajustes de algoritmo (Instagram 2026, no roteirista.md, custo zero):** slides 2 e 3 escritos standalone (o IG re-serve o carrossel a partir do slide 2 pra quem não engajou); open loop entre slides (gate = chegar ao slide 3, transição 2→3 é a mais valiosa); micro-CTA de salvar no slide 7 (save = sinal-rei, não substitui o "siga" do 8); legenda com palavra-chave temática na 1ª frase (SEO > hashtags em 2026).

## Publicação (passo manual do Matheus)
- O sistema entrega no Telegram; Matheus revisa e posta manualmente (v1 NUNCA publica sozinho).
- **Adicionar MÚSICA ao carrossel no app ao postar** empurra o post pro feed de Reels (alcance de Reel + engajamento de carrossel). Passo manual, custo zero — faz parte do fluxo de publicação.

## Stack e chaves (.env)
- LLM plugável: Groq (`llama-3.3-70b-versatile`) ou Anthropic (`claude-sonnet-4-6`)
- **Brave Search API — FONTE ÚNICA de dados** (fatos + narrativa). Snippets trazem placar do SofaScore + notícias de CNN/ESPN/GE/CazéTV/FIFA. Endpoints: `/res/v1/web/search` (texto) e `/res/v1/images/search` (imagens, etapas futuras), header `X-Subscription-Token`.
- SofaScore/FotMob direto — **NÃO usar**: bloqueiam o IP do VPS (403 / header `x-mas` assinado). Código preservado em `pesquisa.py` como fallback DESATIVADO (`_FALLBACK_DIRETO_ATIVO=False`), só reativar se houver proxy residencial.
- Telegram Bot — entrega
- Puppeteer/Playwright — composição

## Regras de trabalho
- Construção em 8 ETAPAS sequenciais (ver `comandos/`). Cada etapa = 1 sessão focada, testável. NUNCA avançar sem o teste da etapa passar.
- Sempre rodar o teste da etapa antes de considerar feito.
- Validação factual e anti-alucinação em código, não só no prompt.
- Não alterar arquivos de `engine/data/`.

## Status das etapas
- ✅ **ETAPA 0** — scaffold, config (`get_llm` plugável), `state.py`, dados validados em `engine/data/`, `tests/test_data.py` → "ETAPA 0 OK".
- ✅ **ETAPA 1** — nó de pesquisa `engine/nodes/pesquisa.py`. **Fonte de dados = Brave Search (única).** `pesquisa_manha` (descobre confrontos via Brave → busca fatos+narrativa por jogo) / `pesquisa_tarde` (momentos históricos) + `derivar_fase`. Extração dos SNIPPETS com consenso multi-fonte: placar só fixado se ≥2 fontes confiáveis concordam (`fontes_concordam`); conflito → placar vazio (não chuta); URLs registradas em `fontes_urls` (rastreabilidade). Fontes confiáveis: SofaScore, CNN, ESPN, GE, CazéTV, FIFA. Costuras injetáveis (`descobrir`/`buscar_jogo`/`buscar_hist`) p/ teste sem rede. `tests/test_pesquisa.py` → "ETAPA 1 OK". `require_brave_key()` no config falha com msg clara se `.env` sem chave. ⏳ aguardando `BRAVE_API_KEY` no `.env` p/ teste real ponta-a-ponta antes da ETAPA 2.
