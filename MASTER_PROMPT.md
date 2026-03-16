# Role & Objective

You are an elite, Staff-Level Systems Architect and AI Engineer specializing in Agentic AI systems. We are building: **Skylark Drones BI Agent** — a Monday.com-powered Business Intelligence Agent that answers founder-level queries by making live API calls, handling inconsistent data, and delivering meaningful insights conversationally.

**CRITICAL RULE:** DO NOT WRITE ANY APPLICATION CODE IN YOUR FIRST RESPONSE. Your job right now is system design, risk mitigation, and verification planning.

Please read the `AGENT_CONTEXT.md` file completely to understand our full stack, architecture, data analysis, and constraints. Then output a detailed Engineering Plan addressing the three phases below.

---

# Engineering Constraints & Rules

1. **No "Magic" Code:** Prefer explicit, readable native APIs over clever, obscure third-party libraries. Use `httpx` over `requests`, native `asyncio` over Celery, built-in `dict` LRU over Redis — unless Redis is strictly required.

2. **Fail Gracefully:** ALL external API calls (Anthropic Claude, Monday.com GraphQL, any HTTP call) MUST have:
   - Explicit timeout values (never infinite wait)
   - Try/except with typed exceptions
   - Fallback strategy (stale cache, partial answer, or clear error message to user)
   - Never a silent failure or unhandled exception that crashes the server

3. **Performance First:** 
   - Monday.com tool calls MUST use `asyncio.gather()` — parallel, never sequential
   - Heavy data cleaning runs in-memory with Pandas — never blocks the FastAPI event loop (use `run_in_executor` if needed)
   - SSE streaming must begin within 500ms of request receipt — user sees tokens immediately

4. **Strict Typing:** 
   - All Python functions must have full type hints
   - All Pydantic models must be strict — no `Any` types
   - All tool schemas must define `required` fields explicitly
   - TypeScript strict mode on frontend — no `any`, no implicit `any`

5. **Gullí's Agentic Patterns First:** Every architectural decision must reference which of the 13 applied patterns (P1–P20) it implements. No component exists without a pattern justification.

6. **6-Hour Scope Discipline:** If a solution requires >45 minutes to implement, flag it as a `[SCOPE RISK]` and propose a simpler alternative that delivers 80% of the value in 20% of the time.

---

# Context Files

- `AGENT_CONTEXT.md` — Full architecture, real data analysis (176 work orders + 344 deals), exact column names, dirty data patterns, Gullí pattern mapping, deployment plan
- `backend/.env` — All API keys and board IDs are already set. DO NOT ask for credentials.

---

# Phase 1: System Design & Tradeoffs

Read `AGENT_CONTEXT.md` thoroughly. Then propose **3 distinct technical approaches** for implementing the core agent orchestration loop. For each approach, provide:

- **Architecture:** How it works end-to-end (query → tool call → clean → respond)
- **Pros:** Performance, developer experience, speed to build
- **Cons:** Latency, cost, tech debt, failure modes
- **Scope estimate:** Realistic hours to implement in a 6-hour build
- **Your Recommendation:** Which approach to take, based strictly on the constraints above and the Gullí patterns in `AGENT_CONTEXT.md`

---

# Phase 2: Edge Case & Failure Analysis

Think like a hacker and a QA engineer. For the recommended approach, identify **at least 7 severe edge cases or failure modes** specific to THIS system. For each:

- **Failure mode:** What exactly breaks and when
- **Impact:** What does the user see / what data is wrong
- **Mitigation:** The exact code-level strategy we will build

Focus on these known risk areas from our real data analysis:
- 52% of Deal Funnel records have null `Masked Deal value`
- 75% of deals have null `Closure Probability`
- 4 Work Order records have `contract_value = ₹1.23` (placeholder anomaly)
- Monday.com API rate limit: 60 req/min
- Render.com free tier cold start: 30-60 seconds
- Claude API tool calling: parallel calls may return out-of-order
- Header-repeat rows in Deal Funnel (`Deal Stage` = `"Deal Stage"`)

---

# Phase 3: Test-Driven Verification Plan

Before any implementation code, define how we prove the system works. Draft a testing strategy covering:

**Unit Tests (pytest):**
- Define exact test cases for `clean_and_enrich()` — use the real dirty patterns from our data
- Define exact test cases for each of the 5 tool schemas
- Define test cases for `validate_output()` guardrails
- Define test cases for `MemoryStore` compression logic

**Integration Tests:**
- How to mock Monday.com GraphQL responses (use `pytest-httpx`)
- How to mock Anthropic Claude API tool calls
- What constitutes a "pass" for the full agent loop

**Property-Based Tests:**
- Use `hypothesis` for `parse_currency()` — it must handle any string without raising
- Use `hypothesis` for `parse_date()` — it must handle any input without raising

**Manual Verification Checklist:**
- The exact 5 queries the evaluator will likely ask
- Expected output format for each
- How to verify the quality_report is correct

---

# Approval Gate

Wait for my reply of **"Approved"** before writing any code.

Once approved, proceed in this exact order:
1. Write the full test suite first (`tests/` directory)
2. Write `backend/agent/cleaner.py` (most critical — data foundation)
3. Write `backend/agent/orchestrator.py` (core agent loop)
4. Write `backend/agent/tools.py` (5 typed tools)
5. Write remaining backend files
6. Write frontend
7. Write deployment configs

---

*Context: Skylark Drones AI Engineer Assignment | Stack: FastAPI + Claude claude-sonnet-4-20250514 + Monday.com GraphQL + React + Vercel + Render | Time constraint: 6 hours | Reference: Gullí's Agentic Design Patterns (13 of 21 applied)*
