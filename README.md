# Skylark Drones — BI Agent

A Monday.com-powered conversational Business Intelligence Agent that answers founder-level queries about deals, pipeline health, work orders, and revenue forecasts in real time. Built on FastAPI + React 18, it streams responses via SSE, calls live Monday.com GraphQL data, and applies 13 of Antonio Gullí's 21 Agentic Design Patterns to deliver grounded, confidence-scored insights — with no hallucination.

---

## Live Demo

| Service  | URL |
|----------|-----|
| Frontend | https://skylar-bi-agent.vercel.app |
| Backend  | https://skylark-bi-agent.onrender.com |
| Health   | https://skylark-bi-agent.onrender.com/health |

> The backend runs on Render's free tier and sleeps after 15 minutes of inactivity.
> The first request after sleep takes 30–60 seconds. The UI shows a warming banner automatically.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vercel)                        │
│   React 18 + Vite + Tailwind  ·  SSE streaming  ·  localStorage│
│   Chat UI  │  Conversation history  │  Morning Briefing button  │
└──────────────────────────┬──────────────────────────────────────┘
                           │  POST /chat   (x-api-key header)
                           │  SSE stream   text/event-stream
┌──────────────────────────▼──────────────────────────────────────┐
│                      BACKEND (Render.com)                       │
│                     FastAPI + uvicorn                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator                         │   │
│  │  P2: Route  →  P6: Plan  →  P3: Parallel tool calls    │   │
│  │  P11: Coverage check  →  P4: Critic reflection          │   │
│  │  P1: Prompt chain  →  Synthesis stream  →  P18: Guard  │   │
│  └────────────┬──────────────────────────┬─────────────────┘   │
│               │                          │                      │
│  ┌────────────▼────────┐    ┌────────────▼──────────────────┐  │
│  │   Memory (P8)       │    │   5 Typed Tools (P5)          │  │
│  │  10-turn sliding    │    │  get_at_risk_deals            │  │
│  │  window + async     │    │  get_pipeline_summary         │  │
│  │  compression        │    │  get_work_orders              │  │
│  └─────────────────────┘    │  get_anomalies                │  │
│                             │  get_revenue_forecast         │  │
│  ┌──────────────────────┐   └────────────┬──────────────────┘  │
│  │  LLM: Groq API       │                │                      │
│  │  Planner/Critic:     │   ┌────────────▼──────────────────┐  │
│  │   llama-3.1-8b       │   │  Monday.com GraphQL Client    │  │
│  │  Synthesizer:        │   │  asyncio.Semaphore(3)         │  │
│  │   llama-3.3-70b      │   │  429 retry + stale cache      │  │
│  └──────────────────────┘   │  TTL LRU cache (5 min)        │  │
│                             └───────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Data Quality Pipeline (P14)                             │  │
│  │  null handling → type coercion → normalisation → enrich  │  │
│  │  181 null deal values handled · 4 placeholder records    │  │
│  │  filtered · 127 dead deals excluded from active pipeline │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
            Monday.com GraphQL API (live boards)
            Deal Funnel Board (5027220048)
            Work Order Board  (5027220057)
```

---

## Gullí's 13 Agentic Design Patterns Applied

| # | Pattern | Implementation |
|---|---------|----------------|
| P1 | Prompt chaining | system → query-type addon → tool results → synthesis → stream |
| P2 | Routing | `_classify()` maps query to analytics / operational / forecast / anomaly |
| P3 | Parallelization | `asyncio.gather()` fires all tool calls simultaneously |
| P4 | Reflection | Critic LLM (8b) validates number grounding before synthesis — analytics + forecast only |
| P5 | Tool use | 5 typed OpenAI-format tool schemas with strict parameter validation |
| P6 | Planning | First LLM call decomposes query into ordered tool sub-goals |
| P8 | Memory management | 10-turn sliding window; older turns compressed async with 8b model |
| P11 | Goal monitoring | Coverage check post-tool; replan triggered if coverage < threshold (5 or 50) |
| P12 | Self-correction | Integrated into P4 — critic note appended, synthesis regenerated |
| P14 | Context-aware decisions | Data quality report (records_used, records_excluded) injected into every prompt |
| P16 | Resource-aware optimization | TTL LRU cache + `asyncio.Semaphore(3)` rate limiter + model cost split |
| P18 | Guardrails | `validate_output()` checks number grounding; confidence score on every answer |
| P19 | Evaluation & monitoring | Structured JSON log per request: trace_id, latency_ms, tool_calls, confidence |

**Skipped (correct for 6-hour scope):** P7 multi-agent, P9 adaptive learning, P10 MCP, P13 hierarchical, P15 A2A, P17 advanced reasoning, P21 exploration.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React 18 + Vite + Tailwind | Fast setup, SSE-native, hot reload |
| Backend | FastAPI + uvicorn (Python 3.11) | Async I/O, auto-docs, Pydantic |
| LLM — Planner | Groq llama-3.1-8b-instant | Fast + cheap for tool selection, critic, compression |
| LLM — Synthesizer | Groq llama-3.3-70b-versatile | Full quality for final founder-facing answer |
| Data | Monday.com GraphQL API | Live boards, real-time queries |
| Cache | Python in-memory TTL LRU | No Redis needed for single-server free tier |
| Hosting (FE) | Vercel | Free, instant CDN, zero config Vite |
| Hosting (BE) | Render.com free tier | FastAPI + uvicorn runs perfectly |

---

## Local Setup

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

All secrets are already in `backend/.env`. Do not commit this file.

### 2. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:
```
VITE_BACKEND_URL=http://localhost:8000
VITE_API_KEY=<copy API_KEY from backend/.env>
```

```bash
npm run dev
# Opens at http://localhost:5173
```

### 3. Data Import (one-time)

Place the Excel files in `data/`, then:
```bash
cd data
pip install pandas httpx openpyxl python-dotenv
python import_to_monday.py       # seeds Work Order board
python import_deal_funnel.py     # seeds Deal Funnel board
```

### 4. Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
# 49 tests — cleaner, guardrails, memory, tools
```

---

## Deployment

### Backend → Render.com (free tier)

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service → Connect GitHub repo
3. Render auto-detects `render.yaml` in the root — no manual config needed
4. In Render dashboard → Environment, add these secrets:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | from backend/.env |
| `MONDAY_API_TOKEN` | from backend/.env |
| `MONDAY_DEAL_BOARD_ID` | `5027220048` |
| `MONDAY_ORDER_BOARD_ID` | `5027220057` |
| `API_KEY` | from backend/.env |
| `FRONTEND_URL` | your Vercel URL (add after frontend deploy) |

5. Click Deploy. First build takes ~3 min.
6. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend → Vercel (CLI)

```bash
# Install Vercel CLI if not installed
npm i -g vercel

cd frontend
vercel

# Follow prompts:
# Project name: skylark-bi-agent
# Framework: Vite (auto-detected)
# Build command: npm run build  (auto-detected)
# Output dir: dist  (auto-detected)

# Set environment variables:
vercel env add VITE_BACKEND_URL
# Enter: https://skylark-bi-agent.onrender.com

vercel env add VITE_API_KEY
# Enter: <your API_KEY>

# Deploy to production:
vercel --prod
```

### After both are deployed

Update `FRONTEND_URL` in Render environment variables with your Vercel URL, then redeploy the backend service.

---

## 5 Evaluator Queries to Test

```
1. Which deals are at risk?
2. What is our total pipeline value?
3. Show me overdue work orders
4. What is the revenue forecast this month?
5. Any anomalies in the deal funnel?
```

Every response is:
- Grounded in live Monday.com data
- Confidence-scored (High / Medium / Low)
- Streamed token by token via SSE

---

## Cold Start Note

The Render free tier spins down after 15 minutes of inactivity. The first request after sleep takes **30–60 seconds**. The frontend automatically pings the backend on load and shows a warming banner if the response is slow. Subsequent requests run at full speed.

---

## Decision Log Summary

- **Single agent over multi-agent**: a single orchestrator with `asyncio.gather()` achieves parallel tool execution with far less coordination overhead and failure surface than a multi-agent mesh at this scope.
- **In-memory cache over Redis**: TTLCache with LRU eviction is sufficient for a single-server free-tier deployment. Redis becomes relevant only when scaling to multiple instances.
- **Data quality as a first-class concern**: 181 null deal values, 4 placeholder records (₹1.23), and 127 dead deals required explicit handling before any aggregation — the `cleaner.py` pipeline runs before every LLM call.

See `decision_log/decision_log.md` for full rationale.
