# Skylark Drones BI Agent — Decision Log

**Role evaluated for:** AI Engineer
**Constraint:** 6-hour build · Live hosted prototype · Monday.com as data source

---

## 1. Framework: FastAPI over Flask

FastAPI was chosen because Monday.com API calls are I/O-bound network requests. FastAPI's native `asyncio` support lets the orchestrator fire all tool calls with `asyncio.gather()` simultaneously — a 4-tool query completes in the time of the slowest single call (~400ms) instead of sequentially (~1600ms). Flask has no async model without bolt-ons. FastAPI's automatic Pydantic validation at the schema boundary also eliminates an entire class of type errors that would surface only at runtime in Flask.

FastAPI's auto-generated OpenAPI docs were also used during development to manually test tool schemas — a non-trivial benefit during a 6-hour build.

---

## 2. Single Agent over Multi-Agent

A multi-agent architecture (e.g., separate planner, retriever, and synthesizer agents) adds coordination overhead: message passing, failure propagation across agents, and non-deterministic execution order. For this scope — 5 typed tools, one data source, one user-facing output — a single orchestrator with parallel tool calls (Gullí P3) achieves the same latency profile as a 2-agent system with none of the coordination cost.

The real risk of multi-agent at 6 hours is debugging time. A single orchestrator fails in one place and logs in one place. Multi-agent is a v2 feature.

---

## 3. In-Memory Cache over Redis

The TTLCache with LRU eviction (max_size=100, TTL=300s) covers all cache requirements for a single-server Render.com deployment. Introducing Redis would add: a separate managed service, a connection string env var, a redis-py/aioredis dependency, and retry logic for connection failures — for no functional gain at this scale.

The cache also implements a `get_stale()` method (Patch 2): if Monday.com returns a 429 rate-limit error, the client falls back to the most recent cached value even if its TTL has expired. This makes the agent resilient to API throttling without ever crashing.

Redis becomes the correct choice when the backend scales beyond a single instance.

---

## 4. How Messy Data Was Handled

The Monday.com boards contained significant quality issues discovered during development:

**181 null deal values** — Deal Funnel records where `contract_value` was blank. These were set to `0.0` with a `has_null_value=True` flag, excluded from pipeline totals but retained in deal counts so the agent can accurately report "127 deals in pipeline, 181 records had missing values."

**4 placeholder records** — Work Order tracker has 4 rows with `contract_value = 1.23`. These are clearly masked/test values (Patch 5): any value `0 < v < 100` in a financial field is flagged as a placeholder and excluded from aggregations. The quality report surfaces this to the LLM.

**127 dead deals** — Deals with `deal_stage = "Dead"` are excluded from active pipeline calculations. Including them would overstate the pipeline by approximately ₹18 Cr.

**75% of deals had no Closure Probability set** — Rather than excluding 258 deals from weighted revenue forecasts, probability defaults to `0.50` (neutral) and the confidence score is forced to `"low"` when more than 50% of probabilities were assumed (Patch 4). This preserves a useful forecast while being transparent about the assumption.

**Header-repeat rows** — The Deal Funnel file had 2 rows where `Deal Stage = "Deal Stage"` (column header copied as a data row). These cause TypeErrors in pandas `groupby()` and are removed before any processing.

All exclusions are reported in `quality_report` which is injected into the LLM prompt so the synthesizer can cite them explicitly in responses.

---

## 5. Gullí Patterns Applied and Why

**P1 — Prompt chaining**: The system prompt is assembled in three layers: a 300-token compressed base, a query-type addon (analytics/forecast/operational), and injected business context (hardcoded real figures from initial data analysis). This prevents the LLM from needing to re-derive known facts from tool output every call.

**P2 — Routing**: A keyword classifier in `_classify()` maps query intent to one of four types. This controls which system prompt addon is loaded and whether reflection (P4) runs. Operational queries (work orders) skip reflection since hallucination risk is low for structured list outputs.

**P3 — Parallelization**: `asyncio.gather()` fires all planned tool calls simultaneously. A morning briefing query that calls 4 tools completes in ~600ms instead of ~2400ms.

**P4 — Reflection**: A second, cheap LLM call (llama-3.1-8b) acts as a critic before the synthesis pass. It answers YES/NO: "Is every number grounded in tool results?" If NO, a critic note is appended to the message thread before synthesis. This is only run for analytics and forecast queries.

**P6 — Planning**: The first LLM call does not generate user-visible text — it only decides which tools to call and with what parameters. This separates intent understanding from execution.

**P8 — Memory**: 10-turn sliding window. When a session exceeds 10 turns, older turns are compressed into a summary using llama-3.1-8b with max_tokens=100. This keeps context costs flat for long sessions.

**P11 — Goal monitoring**: After tool execution, a coverage check counts total records returned. For broad queries ("tell me everything"), coverage must be ≥ 50 records before proceeding. For specific queries, ≥ 5 records suffices (Patch 8). If coverage is insufficient, the orchestrator replans once with a `[REPLAN]` prefix.

**P14 — Context-aware decisions**: Every prompt includes the data quality report: records_used, records_excluded, exclusion_reasons, and confidence. The LLM synthesizer is instructed to always cite these figures.

**P16 — Resource-aware optimization**: `asyncio.Semaphore(3)` caps concurrent Monday.com connections. The model cost split (8b for planning/critic, 70b for synthesis) reduces per-query LLM cost by ~80%.

**P18 — Guardrails**: `validate_output()` runs a regex pass over the final response to check that every number present can be found in the raw tool output. Confidence is downgraded if grounding fails. The warning is logged internally and not shown to the user (avoids false positives from numbers injected via business context).

**P19 — Evaluation**: Every request emits a structured JSON log: `trace_id`, `query_type`, `tool_calls`, `coverage`, `latency_ms`, `confidence`, `guardrail_passed`, `replanning`. These are queryable in Render's log stream.

---

## 6. Deliberately Skipped and V2 Roadmap

**Authentication depth**: A single static API key in the `x-api-key` header is sufficient for a founder-facing prototype used by one team. JWT-based auth with user roles is a v2 feature that adds ~4 hours of work with no demo value.

**Observability**: Structured JSON logs cover what is needed at this stage. A proper observability stack (OpenTelemetry → Grafana) is a v2 feature. Render's built-in log stream is sufficient for a 6-hour submission.

**Adaptive learning (P9)**: Storing query-response pairs and fine-tuning or using them as few-shot examples would improve answer quality over time but requires a database and a feedback loop. Not feasible at this scope.

**Multi-agent (P7)**: Skipped. See Section 2.

**MCP (P10)**: Model Context Protocol is relevant when connecting to multiple external tool ecosystems. Monday.com as a single data source does not require it.

**Persistent memory**: The current in-memory session store resets on server restart (Render free tier restarts frequently). A v2 would persist sessions to SQLite or Postgres.

**Auth depth**: The current implementation uses a single static API key in the `x-api-key` header. This is sufficient for a single-founder prototype. V2 adds JWT-based authentication with user-scoped Monday.com tokens — each user authenticates with their own Monday.com OAuth token, enabling multi-user access with board-level permissions enforced at the API layer.

**Observability**: All requests emit structured JSON to stdout (`trace_id`, `latency_ms`, `tool_calls`, `confidence`, `guardrail_passed`). This is queryable in any log aggregator. V2 adds a Prometheus metrics endpoint and a Grafana dashboard tracking P95 latency, tool call frequency, guardrail failure rate, and Monday.com API error rate — giving the team a real-time health view without manual log parsing.

**Adaptive Learning (P9)**: The current agent does not learn from usage. V2 logs every failed query (guardrail_passed=false or user retry within 30s) to a Postgres table. A weekly job converts the top 10 failure patterns into few-shot examples injected into the system prompt — progressively improving answer quality on the queries the founder actually asks most.

**V2 Roadmap (priority order)**:
1. JWT auth with user-scoped Monday.com tokens
2. Prometheus + Grafana P95 observability dashboard
3. Adaptive learning — failed query logging → weekly few-shot injection
4. Persistent conversation storage (Postgres/SQLite)
5. Multi-board support (Sales, Ops, Finance boards unified)
6. Chart rendering (Recharts inline in responses)
7. Slack bot integration via Monday.com webhook triggers
