# BRIEFING MESTRE — FocusClear Content Engine
**Versão 1.1 · Jul/2026 · Documento de referência permanente**

> Fonte de verdade do produto. Decisão nova que mude algo abaixo deve ser
> registrada AQUI antes de virar código. O `CLAUDE.md` rastreia o status de
> implementação; este documento rastreia a intenção de produto.

---

## 1. O QUE É

Ferramenta de criação de conteúdo autônoma e semi-autônoma que transforma momentos
culturais com carga emocional (futebol, cultura pop, música, datas) em conteúdo de
saúde mental para o Instagram do FocusClear — carrosséis, reels e carrossel-motion —
usando o método espelho emocional validado.

Visão de produto: começa interna (CTec usa pra FocusClear), construída com **workspace
por marca desde o dia 1** para virar SaaS.

---

## 2. OS TRÊS PILARES DO MÉTODO

1. **Método Espelho** — Gancho = evento cultural. Virada = dor emocional humana.
   Alívio = nomear a dor + convite. Nunca vende na primeira interação.
2. **Anti-Alucinação** — Fatos SEMPRE de pesquisa real. Validação factual em CÓDIGO
   antes do LLM.
3. **Qualidade > Volume** — 1 forte > 3 medianos. Humano é o gate (v1).

---

## 3. ARQUITETURA GERAL

```
MAC MINI M4 (tudo aqui)
  FRONTEND · Next.js 14 + Tailwind
    /criar │ /biblioteca │ /fila │ /tendencias │ /pilares │ /personagem │ /metricas │ /config
  BACKEND · FastAPI + SQLite
    MOTOR (LangGraph): pesquisa → seletor → roteirista → [carrossel] [reel] [motion]
    + APScheduler + coletor tendências + biblioteca assets
  PALMIER PRO (editor vídeo, MCP)
Integrações: Brave · HeyGen · ElevenLabs · LLM (Groq/Anthropic) · Instagram Graph API (v2)
```

---

## 4. FORMATOS DE SAÍDA

- **4A. Carrossel** — 8 slides, 1080×1350 (4:5), PNG. Gancho → Dado → Espelho →
  Participação → Virada → Prova → Alívio → CTA. Big Shoulders + Young Serif, brasa
  **#FF5436**, escuro dominante. Safe-zone 1080×1080 central. Slides 2-3 standalone.
  Micro-CTA save no slide 7.
- **4B. Reel (personagem)** — 30-45s, 9:16, 1080×1920, MP4. Avatar talking-head
  fictício (voz do FocusClear). Beats: 0-3s gancho (≤14 palavras) → tensão → espelho →
  virada+alívio → CTA+loop. Legendas desde frame 1. Intercala avatar ↔ fotos reais.
  Palmier MCP pra montagem. Label obrigatório: "conteúdo gerado por IA".
- **4C. Carrossel Motion** — Carrossel com 1-2 slides em vídeo curto (2,33% eng. vs
  1,80% imagem-only).
- **Reutilização** — Mesmo momento → 3 formatos no mesmo batch. Mesmas fotos alimentam
  tudo. Zero duplicação de inteligência.

---

## 5. PILARES DE CONTEÚDO

| Pilar | Status | Gancho |
|-------|--------|--------|
| Futebol | ✅ Ativo | Jogos + históricos |
| Cultura Pop / Fofoca | 🔄 Planejado | Influencer drama, Aqueles Caras, Peixinho, BBB |
| Música Popular | 🔄 Planejado | Lançamento viral, letra que bombou |
| Datas Sazonais | 🔄 Planejado | Natal, Ano Novo, Dia das Mães |

Adicionar pilar = entrada em `pilares.json` + fonte de pesquisa. Motor não muda.

> Nota de reconciliação (jul/2026): o `engine/data/pilares.json` hoje traz o 2º pilar
> como `novela_reality`. O briefing v1.1 o define como **Cultura Pop / Fofoca**
> (decisão travada: "Cultura Pop separado de Novela"). Reconciliar o slug em
> `pilares.json` antes de ativar o 2º pilar.

---

## 6. MOTOR — 7 NÓS LANGGRAPH

```
UI/cron → pesquisa → coleta_imagens → seletor(LLM) → roteirista(LLM)
                                           ↓ por formato
                       compositor(carrossel) / reel / motion
                                           ↓
                                 biblioteca → notifica(Telegram)
```
Nós com LLM: seletor + roteirista. Custo: ~$6/mês (Sonnet 4.6).

---

## 7. FRONTEND — 8 ABAS

- `/criar` — tema, pilar, formato → dispara job → status tempo real
- `/biblioteca` — assets com estados (rascunho→aprovado→agendado→publicado), preview, edição fina
- `/fila` — jobs recentes com status
- `/tendencias` — trends por pilar via Brave, botão "criar a partir disso"
- `/pilares` — CRUD, ativar/desativar
- `/personagem` — config avatar (foto, voz, tom)
- `/metricas` — placeholder pra Graph API v2
- `/config` — chaves, workspace, status integrações

---

## 8. BANCO DE DADOS

`workspaces, pilares, jobs, assets, tendencias, agenda, personagens, metricas (v2)`.
workspace_id (org_id) desde o dia 1. SQLite → Postgres quando produto.

---

## 9. STACK

Frontend: Next.js 14 + Tailwind · Backend: FastAPI + Python (3.12+; máquina roda 3.14)
· BD: SQLite · Motor: LangGraph · LLM: Groq/Sonnet 4.6 (plugável via `get_llm()`) ·
Pesquisa: Brave · Avatar: HeyGen · Voz: ElevenLabs · Editor: Palmier Pro
(MCP, POST http://127.0.0.1:19789/mcp) · Carrossel: Playwright · Agendamento:
APScheduler · Notificação: Telegram Bot · Máquina: Mac Mini M4, macOS Tahoe.

---

## 10. FASES DE CONSTRUÇÃO

```
FASE 0 — Migração VPS → Mac                          ✅
FASE 1 — Backend FastAPI + SQLite + scheduler         ✅ (+ pipeline carrossel completo + preview + Telegram)
FASE 2 — Frontend core (/criar, /biblioteca, /fila)   ✅
FASE 3 — Motor de vídeo (Reel)                        ⬜ roteirista_video + ElevenLabs + HeyGen + Palmier + renderer
FASE 4 — Tendências + Motion                          ⬜ coletor Brave + renderer motion (Kling/Seedance)
FASE 5 — Pilares + Personagem + Config                ⬜ UI ✅ (feita); falta lógica de coleta/geração real
FASE 6 — Polimento + produto-ready                    ⬜ multi-workspace, export TikTok/Shorts, docs
```

---

## 11. DECISÕES TRAVADAS

- Método espelho emocional
- Anti-alucinação em código (dupla camada)
- Humano como gate (v1)
- LLM plugável via `get_llm()`
- workspace_id (org_id) desde o dia 1
- Canvas 4:5, 8 slides, safe-zone central
- Avatar fictício fixo (não clone de pessoa real)
- Cultura Pop separado de Novela
- Tudo no Mac Mini M4
- VPS permanece ativa (outros projetos)
- APIs pro final da construção

---

## 12. CUSTOS

LLM ~$6 · Brave ~$0-5 · HeyGen ~$29-99 · ElevenLabs ~$5-22 · Palmier grátis · Mac $0.
Total: ~$40-130/mês.
