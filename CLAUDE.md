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
- ✅ **FASE 3 — motor de vídeo (Reel)**, 2º output do mesmo motor. `formato="reel"`: pesquisa → coleta_imagens → seletor → **roteirista_video** (prompt = roteirista.md + adendo; 5 beats gancho≤14→tensão→espelho→virada+alívio→CTA+loop, 70-110 palavras) → **voz** (ElevenLabs) → **avatar** (HeyGen) → **reel_compositor** (poster 9:16 + manifest + **montagem REAL via ffmpeg**: `montar_ffmpeg` segmenta por beat avatar↔b-roll, queima legenda+label por segmento, concatena e faz mux da narração → MP4 1080×1920; ffmpeg do PATH ou do binário estático do `imageio-ffmpeg`). Chaves vazias (ElevenLabs/HeyGen) → voz/avatar pulam e o compositor cai no **placeholder** webm do poster (Chromium). Asset tipo `reel` com metadado label "conteúdo gerado por IA". Endpoint de arquivo serve vídeo (content-type por extensão). `/biblioteca`: reel = player `<video>`. `python -m tests.test_reel` → "REEL OK" (prova offline: MP4 real montado com avatar/áudio/fotos mockados, sem API). Nós de carrossel/motion intocados. Palmier MCP fica como alternativa (não implementada); ffmpeg é o default.
- ✅ **FASE 4 — Tendências + Motion**. **Parte 1 (Tendências):** `engine/nodes/coletor_tendencias.py` coleta na Brave por pilar (queries relevantes em `_QUERIES_POR_PILAR`: futebol/cultura_pop/musica_popular/datas_sazonais), extrai entidades dos snippets (`extrair_candidatos`), pontua por frequência + fonte confiável + recência (`score = ocorr*10 + fontes*5 + recencia*3`, int) e ranqueia; costura `buscar` injetável, **sem `BRAVE_API_KEY` pula sem erro** e retorna `[]`. `backend/scheduler.py` roda `job_tendencias` (cron 05h, no scheduler existente): coleta por pilar ativo e **substitui** as linhas de `Tendencia`. `/tendencias` já renderiza cards reais do banco (placeholder "Conecte a Brave" só quando vazio). **Parte 2 (Motion):** `engine/nodes/motion_compositor.py` reaproveita `build_html` do compositor (sem tocá-lo) — slides 1 e 5 viram **webm** com Ken Burns/rise via **CSS animation capturada pelo Chromium** (v1 sem Kling/Seedance), demais slides PNG; costuras `render_png`/`gravar_webm` injetáveis. `job_service`: `formato="motion"` → pipeline normal + `compor_motion` → Asset tipo `motion` (flag `animado` por slide). Frontend: `CarrosselPreview` renderiza `<video>` p/ slide `.webm/.mp4`; `/biblioteca` agrupa motion por pasta em card navegável com badge "motion" (mostra os 3 tipos: carrossel, reel, motion). Testes offline `python -m tests.test_tendencias` → "TENDENCIAS OK" e `python -m tests.test_motion` → "MOTION OK"; suites anteriores seguem passando. Nós de carrossel e reel intocados.
- ✅ **FASE 5 — Pilares + Personagem + Config funcionais** (a UI já existia; agora a lógica é real). **Parte 1 (Pilares):** pilares ATIVOS vêm do banco, não hardcoded. `engine/nodes/pesquisa.py` ganhou `pesquisa_pilar()` genérico (não-futebol): lê `pilar_ativo`/`pilar_config` do state e usa as queries do próprio pilar (`queries_do_pilar` = mapa por slug em `_QUERIES_MOMENTO_POR_PILAR` + derivação do `carga_emocional` do config), extrai "momentos" dos snippets Brave (reusa `extrair_candidatos`). `seletor.py`: `validar_factual` é **pilar-aware** — futebol mantém a âncora das 48 seleções; outros pilares aceitam momentos com conteúdo (âncora fechada ainda não existe → julgamento fica no LLM); `_casa_jogo` religa momento→aprovado p/ preservar narrativa; `selecionar` lê `pilar_ativo`. `coleta_imagens._queries_do_jogo` cai p/ o `momento` quando não há times. `job_service` injeta `pilar_config` do banco e faz **dispatch** da pesquisa (futebol=turnos manhã/tarde; demais=`pesquisa_pilar`). `scheduler` cria 1 job por pilar ATIVO (`pilares_ativos()` lê o banco; retrocompat: sem ativo → futebol). Frontend `/criar` lista só pilares ativos (via `/pilares`). **Parte 2 (Personagem):** `job_service` injeta a foto de referência e `voice_id`/tom do personagem (banco) no state; `avatar.py` já lia `state['avatar_foto']`, `voz.py` agora lê o `voice_id` de `state['voz_config']` (banco tem prioridade sobre o `.env`); router + UI `/personagem` ganharam o campo `voice_id` (salvo em `Personagem.config`). **Parte 3 (Config):** `integracoes.py` — `GET /config` expõe `status` (pendente/configurada); novo `GET /config/validar` testa AO VIVO só as chaves PREENCHIDAS (Brave/LLM/Telegram) → ativa|invalida|configurada|pendente; **nenhuma chamada externa se a chave não existir**; read-only (nunca edita `.env`). `next.config.mjs` ganhou rewrite p/ `/api/config/validar`. `/config` UI: botão "Validar ao vivo" + status colorido real. Teste offline `python -m tests.test_pilares` → "PILARES OK" (cultura_pop usa queries de cultura pop, sem rede/LLM). Suites anteriores seguem passando. Nós de carrossel/reel/motion **intocados na estrutura** — só leitura de config.
- ✅ **FASE 6 — Polimento + produto-ready (v1.0.0)**. **Parte 1 (Multi-workspace):** isolamento no banco, **sem auth** (v1 = quem acessa o Mac acessa tudo). `database.py` semeia 2 workspaces no boot (`focusclear` + `demo`) com pilares por workspace (`_seed_pilares(ws)`); novo `routers/workspaces.py` (`GET /workspaces`). Frontend: `lib/workspace.ts` (workspace ativo no `localStorage`; `comWorkspace()` anexa `?workspace_id=`); `api.ts` passa `workspace_id` em toda chamada com escopo (jobs/assets/pilares/tendencias/personagem); `Nav` ganhou **seletor de workspace** (trocar recarrega a página); rewrite `/api/workspaces` no next.config. `backend/seed_demo.py` (`python -m backend.seed_demo`) popula o `demo` com jobs/tendências de exemplo (idempotente, sem API externa). **Parte 2 (Export):** `components/ExportMenu.tsx` — por asset, "Baixar para Instagram/TikTok/YouTube Shorts" (download do arquivo nativo via `<a download>`; mesma resolução hoje, estrutura pronta p/ ajustes por plataforma), nos 3 tipos de card da `/biblioteca`. **Parte 3 (Docs):** `docs/SETUP.md` (subir do zero no Mac: venv, deps, `.env` por chave, portas, testes, seed) + `docs/ARQUITETURA.md` (camadas, 7 nós, fluxo por formato, onde mexer — 5 min). **Parte 4 (Limpeza):** sem TODO/FIXME reais; `.gitignore` cobre `.env`/`*.db`/`node_modules`/`.next`/`venv`/`output`/`assets` (verificado com `git check-ignore`). Teste `python -m tests.test_workspace` → "WORKSPACE OK". **9 suites passando** (test_data, pesquisa, telegram, reel, tendencias, motion, pilares, workspace, pipeline). Isolamento verificado E2E (dados do `demo` não aparecem no `focusclear` e vice-versa; export baixa o arquivo). Tag de release **`v1.0.0`** na main.
- ✅ **PILARES NÃO-FUTEBOL PONTA A PONTA — âncora, prompts e fontes por pilar** (v1 tinha só o roteamento de pesquisa; agora cultura pop/música/datas rodam ponta a ponta). **1. Âncora factual por pilar:** futebol pós-Copa ganhou `engine/data/competicoes_clubes.json` (clubes reais de Brasileirão/Libertadores/Champions/Premier — âncora de lista fixa pronta pro pivô de 20/jul, `seletor.clubes_validos()` carrega mas NÃO está no caminho de produção ainda). Pilares sem lista possível (cultura pop/música/datas) usam **ÂNCORA POR CONSENSO**: `pesquisa_pilar` conta domínios DISTINTOS por entidade (`n_fontes`/`fontes_dados`/`fontes_concordam`) e `seletor.validar_factual` (pilar-aware) **descarta momento de fonte única** — consenso ≥2 fontes substitui a lista fixa; o fato vem da pesquisa, nunca da memória do LLM. `pesquisa._FONTES_POR_PILAR` ganhou mapas domínio→rótulo de cultura pop/música/datas. **2. Prompts conscientes de pilar:** `seletor.md` (PASSO 1 = âncora por consenso documentada; PASSO 3 = exemplos de casamento por pilar: influencer cancelado→julgamento público, BBB→exclusão, letra de término→saudade/superação, Natal→solidão, Ano Novo→ansiedade de retrospectiva) e `roteirista.md` (nota "o mesmo método em cada pilar": gancho cultural→virada emocional→alívio + bloco **CUIDADO ÉTICO OBRIGATÓRIO de cultura pop**: nunca atacar/humilhar a pessoa real, falar da EMOÇÃO que o público projeta). **3. Fontes de pesquisa por pilar:** `_QUERIES_MOMENTO_POR_PILAR` com queries fortes por pilar (cultura pop: cancelado/treta/BBB/término; música: charts/lançamentos/letra término; datas: data comemorativa/Natal-Ano Novo/campanha). `pilares.json`: 4 `ancora_factual` reescritos. **Prova offline:** `python -m tests.test_pilares` → "PILARES OK" — carrossel mockado de cultura_pop passa por pesquisa_pilar→validar_factual(consenso)→selecionar→escrever_roteiro→resolve_imagens→**compor (Playwright REAL)** = 8 PNGs 1080×1350, jornada escuro→luz (38→177), e o ruído de fonte única é descartado pela âncora por consenso. **Sem API** (tudo com costuras mockadas por pilar). Pipeline de futebol **intocado**. **34 testes passando** (9 suítes).
- ✅ **DÍVIDAS MENORES FECHADAS — agenda conectada + métricas estruturadas** (sem API externa). **1. Agenda→scheduler:** a tabela `agenda` virou a fonte de verdade do agendamento. `scheduler._registrar_agenda` LÊ as linhas ativas e cria 1 cron por linha (`CronTrigger.from_crontab`); `montar_agenda`/`carregar_agenda` são puros e testáveis. **Retrocompat obrigatória:** tabela vazia → hardcoded 06h/13h do focusclear. As 2 regras antes hardcoded viram linhas via `database._seed_agenda` (só focusclear). CRUD `routers/agenda.py` (GET/POST/PATCH/DELETE, cada um chama `recarregar_agenda()`); UI `components/AgendaManager.tsx` na aba `/fila`. `_migrar_sqlite` adiciona `turno`/`criado_em` a bancos antigos (ALTER TABLE). **2. /metricas estruturada:** nova tabela `Metrica` + `routers/metricas.py` (`GET /metricas` → `{metricas, resumo, conectada:false}`, vazio sem crash); a página `/metricas` mostra números reais quando houver e estado vazio claro ("dados aparecem quando a Instagram Graph API for conectada — v2") quando não. **Graph API NÃO conectada** — só a estrutura pronta pra receber. **3. Doc:** pendências do CLAUDE.md atualizadas (agenda ✅, métricas ✅; sobram honestas o esboço HeyGen não-verificado e o pivô pós-Copa de `competicoes_clubes.json`). Testes `python -m tests.test_agenda` → "AGENDA OK" e `python -m tests.test_metricas` → "METRICAS OK". **42 testes passando** (11 suítes: as 9 anteriores + test_agenda + test_metricas). Endpoints verificados ao vivo (curl). Pipeline de carrossel/reel/motion **intocado**.

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
python -m engine.run --dry-run                   # valida o plano/fiação do pipeline (NÃO chama APIs)
python -m engine.run --turno manha               # dispara o pipeline (real; requer BRAVE + LLM no .env)
python -m engine.run --turno tarde --formato reel
python -m engine.run --pilar cultura_pop --formato motion
pytest tests/                                    # roda todos os testes (42 funções, 11 suítes)
# alternativa sem pytest: python -m tests.test_pipeline  (imprime "PIPELINE OK")
playwright install chromium                      # setup do compositor (uma vez)
```

> `engine/run.py` é o CLI real: cria um job e chama o MESMO `job_service.executar_job`
> do backend/scheduler. `--pilar` (default `futebol`) injeta `pilar_ativo` + `pilar_config`
> no state. v1: só `futebol` funcional de ponta a ponta.

## Arquitetura (pipeline de 7 nós — orquestração SEQUENCIAL em Python)
```
scheduler cron 06h/13h → pesquisa → coleta_imagens → seletor(LLM) → roteirista(LLM) → resolve_imagens → compositor(Playwright) → telegram
```
- **Não é LangGraph.** A orquestração é Python sequencial em `backend/services/job_service.py`
  (`executar_job` chama os nós em ordem e ramifica por `formato`: carrossel / reel / motion).
  "LangGraph" no briefing é rótulo/meta futura, **não implementado** (ver "Pendências conhecidas").
- Nós determinísticos: pesquisa, imagem, compositor, telegram. Só **seletor** e **roteirista** chamam LLM.
- `manha`: momentos de ontem (newsjacking). `tarde`: 2 momentos históricos.
- Fan-out no seletor: 1 execução → N carrosséis.

## Serviço (portas) — como subir e onde acessar
- **Backend** (FastAPI): `uvicorn backend.main:app --port 8010` → **http://localhost:8010** (docs em `/docs`).
- **Frontend** (Next.js): `cd frontend && npm run dev` → **http://localhost:3010** (porta fixada em `frontend/package.json`: `next dev -p 3010`). **Acesse o painel em http://localhost:3010.**
- Frontend fala com o backend via rewrite `/api/* → :8010` (`next.config.mjs`, rewrites explícitos).

## Pendências conhecidas (honestas, não silenciosas)
- **Reel — montagem real ✅ (via ffmpeg):** com avatar (HeyGen) + áudio (ElevenLabs), `reel_compositor.montar_ffmpeg` faz a costura REAL — segmenta por beat (avatar ↔ b-roll das fotos do momento), queima legenda + label "conteúdo gerado por IA" por segmento (overlay PNG do Playwright), concatena e faz mux da narração → **MP4 9:16 1080×1920**. ffmpeg vem do PATH ou do binário estático do `imageio-ffmpeg` (local). Sem avatar/áudio (chaves vazias) ou sem ffmpeg → cai no placeholder webm do poster. Provado offline em `tests.test_reel` (MP4 real montado com mocks, sem API). Pendência restante: `avatar.py` (chamada HeyGen v2) é esboço **não verificado contra a API real** — o compositor recebe o arquivo que ela produziria; Palmier MCP é alternativa detectada mas não implementada (ffmpeg é o default).
- **Tabela `agenda`:** ✅ **CONECTADA.** `scheduler.iniciar_scheduler` → `_registrar_agenda` LÊ as linhas ativas da tabela e registra 1 cron por linha (`CronTrigger.from_crontab`). Retrocompat: tabela vazia → cai no hardcoded 06h/13h do focusclear (`_AGENDA_HARDCODED`). As regras antes hardcoded viram linhas via `_seed_agenda` no boot do focusclear. CRUD em `routers/agenda.py` (GET/POST/PATCH/DELETE); cada alteração chama `recarregar_agenda()` (no-op se o scheduler não está rodando). UI de gestão na aba `/fila` (`components/AgendaManager.tsx`). Migração leve `_migrar_sqlite` adiciona `turno`/`criado_em` a bancos de fases anteriores. Teste `python -m tests.test_agenda` → "AGENDA OK".
- **/metricas:** ✅ **ESTRUTURADA** (sem Graph API ainda). Nova tabela `Metrica` (swipe_rate/saves/shares/completion por asset/período); `GET /metricas` (`routers/metricas.py`) devolve `{metricas, resumo, conectada:false}` — vazio sem crash hoje. A página lê os dados reais quando existirem e mostra estado vazio claro ("dados aparecem quando a Instagram Graph API for conectada — v2") quando não. **Nada popula a tabela ainda** (Graph API = v2); a estrutura só está pronta pra receber. Teste `python -m tests.test_metricas` → "METRICAS OK".
- **LangGraph:** não implementado (a orquestração é sequencial; ver acima).
- **`competicoes_clubes.json`** (âncora pós-Copa): ✅ criado (clubes reais Brasileirão/Libertadores/Champions/Premier); `seletor.clubes_validos()` carrega a lista, mas o pivô (trocar a âncora do futebol de seleções→clubes em 20/jul) ainda NÃO está no caminho de produção — o pipeline de futebol segue em `selecoes_classificadas.json`.

## Camada de PILARES (multi-conteúdo)
O sistema não é só futebol — "futebol" é UM pilar de vários. **O MOTOR (seletor→roteirista→cascata→compositor→telegram) é AGNÓSTICO:** processa "momentos com carga emocional" vindos de um pilar, sem saber o que é futebol. Adicionar um pilar novo = adicionar entrada em `pilares.json` + fonte de pesquisa, **SEM tocar em seletor/roteirista/compositor**.
- `engine/data/pilares.json` define os pilares em `pilares{}` (cada um com `status`/`prioridade`) + um bloco `rotacao`. **v1: só `futebol` ativo e funcional** (prioridade 1); `novela_reality`/`musica_popular`/`datas_sazonais` = `status: planejado` (arquitetura pronta, ativados depois). Urgência: a Copa acaba **19/jul/2026** — o pilar futebol pivota pra clubes (Brasileirão/Libertadores/Champions, âncora `competicoes_clubes.json` a criar) e um 2º pilar precisa existir antes disso pra conta não secar.
- Cada pilar traz: `ancora_factual` (contra o que a validação factual do seletor confere), `fontes_pesquisa` (quais fontes o nó de pesquisa consulta), `tipo_momento`, `carga_emocional` (dores típicas → casam com os perfis), `validade`, `cuidado`.
- `rotacao`: não saturar um pilar; em transição (ex: fim da Copa) o seletor pode rodar 2 pilares até um assumir.
- `state.pilar_ativo` (str, default "futebol" — não há campo `pilar_padrao` no JSON; o default é do entrypoint) + `state.pilar_config` (dict, a entrada do pilar em `pilares.json`) atravessam o pipeline.
- Seletor: valida os fatos contra a `ancora_factual` DO PILAR (futebol = `selecoes_classificadas.json`) e casa perfil via `criterio_de_casamento` (genérico) + `carga_emocional` do pilar.
- Pesquisa: fontes confiáveis por pilar em `_FONTES_POR_PILAR` (futebol + cultura_pop/musica_popular/datas_sazonais mapeados); mesma lógica de consenso multi-fonte, só troca QUAIS fontes. **Âncora por consenso** (pilares sem lista fixa): `pesquisa_pilar` conta domínios distintos por entidade e `validar_factual` descarta momento de fonte única (≥2 fontes = anti-alucinação no lugar da lista).

## Princípios inegociáveis
1. **Anti-alucinação = prioridade máxima.** Fatos de futebol SEMPRE da pesquisa (Brave — fonte única; SofaScore/FotMob bloqueiam o IP), NUNCA da memória do LLM. Validação factual roda em CÓDIGO antes do LLM (dupla camada): todo time tem que estar em `selecoes_classificadas.json`, senão descarta.
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
  nodes/           # 1 arquivo por nó (13: pesquisa, coleta_imagens, seletor, roteirista,
                   #   resolve_imagens, compositor, telegram, roteirista_video, voz, avatar,
                   #   reel_compositor, motion_compositor, coletor_tendencias)
  data/            # JSONs e prompts — FONTE DE VERDADE, não alterar
  templates/fonts/ # woff2 base64 embutidas (NÃO há slide.html — o HTML é gerado por compositor.build_html)
  output/          # PNGs/webm (gitignored)
  run.py           # CLI real (--turno/--pilar/--formato/--dry-run) → chama job_service.executar_job
backend/           # FastAPI: main, database, scheduler, seed_demo, routers/, services/job_service
                   #   (a orquestração do pipeline vive em services/job_service.py — não há engine/graph.py)
tests/             # 1 teste por etapa/feature (11 suítes; rodam via pytest ou como módulo)
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

**Canvas 4:5 — 1080×1350** (era 1:1 1080×1080; ocupa ~35% mais tela no feed). **Safe-zone central obrigatória:** texto crítico e foco visual ficam dentro do quadrado central 1080×1080 (offset de 135px no topo e 135px na base). No grid do perfil o 4:5 é cortado pra o 1080×1080 central — o que ficar nos 135px de topo/base some no grid; esses 135px servem só pra respiro visual / extensão de foto, nunca pra texto essencial. O HTML do slide (1080×1350 com a safe-zone) é gerado em código por `compositor.build_html` (não há arquivo `slide.html`; só as fontes woff2 ficam em `engine/templates/fonts/`). Tipografia Big Shoulders Display (display) + Young Serif (virada). Paleta: brasa-noite #0D0B0F, refletor #F2EBDD, brasa #FF5436, pele #E3A87C.

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
