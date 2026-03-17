"""
orchestrator.py — Heart of the agent (P1, P2, P3, P4, P6, P8, P11, P12, P18, P19)
Patches applied:
  P3: thread-safe replanning via replanning: bool param (not mutable instance var)
  P7: _execute_tools() returns {tool_use_id: result} dict — position-independent
  P8: dynamic coverage threshold (broad vs specific queries)
Token optimizations:
  Opt 3: reflection only on analytics + forecast query types
  Opt 4: Haiku/8b-instant for planning + reflection; Sonnet/70b for synthesis only
"""
import asyncio
import json
import logging
import os
import time
from typing import AsyncGenerator

from openai import AsyncOpenAI
from agent.prompt import build_system_prompt
from agent.tools import TOOL_SCHEMAS, execute_tool
from agent.memory import MemoryStore
from agent.guardrails import validate_output

logger = logging.getLogger(__name__)

# Token Opt 4: model split
PLANNER_MODEL   = "llama-3.1-8b-instant"    # fast, cheap — just picks tools
SYNTHESIS_MODEL = "llama-3.3-70b-versatile"  # full power — final answer only
CRITIC_MODEL    = "llama-3.1-8b-instant"    # just needs YES/NO

# Token Opt 3: only run reflection for these types
REFLECTION_REQUIRED = {"analytics", "forecast"}

memory = MemoryStore()


class Orchestrator:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=os.getenv("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1",
        )

    async def run(
        self,
        session_id: str,
        query: str,
        replanning: bool = False,  # Patch 3: param, not mutable instance var
    ) -> AsyncGenerator[str, None]:
        start = time.time()
        trace_id = f"{session_id[:8]}-{int(start)}"

        # P2: Route — classify query type
        query_type = self._classify(query)

        # P8: Memory — get conversation history
        history = memory.get(session_id)

        # P1 + P14: Build system prompt with query-type context
        system = build_system_prompt(query_type)

        messages: list[dict] = history + [{"role": "user", "content": query}]

        # P6: Planning — planner picks which tools to call (Opt 4)
        # Retry once on transient errors (cold-start / Groq blip)
        plan_response = None
        for attempt in range(2):
            try:
                plan_response = await self._client.chat.completions.create(
                    model=PLANNER_MODEL,
                    max_tokens=1000,
                    messages=[{"role": "system", "content": system}] + messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
                break
            except Exception as e:
                if attempt == 1:
                    yield f"I'm having trouble reaching the AI service. Please retry. ({type(e).__name__})"
                    return
                await asyncio.sleep(1.5)

        # P3: Parallelization — execute all planned tool calls simultaneously
        tool_calls = plan_response.choices[0].message.tool_calls or []
        results_map: dict[str, dict] = {}

        if tool_calls:
            # Patch 7: _execute_tools returns {id: result} — position-independent
            results_map = await self._execute_tools(tool_calls)

        results_list = list(results_map.values())

        # P11: Goal monitoring — Patch 8: dynamic threshold
        coverage = self._check_coverage(query, results_list)
        if coverage < 0.7 and not replanning:
            # Patch 3: pass replanning=True to prevent infinite loop
            async for chunk in self.run(session_id, f"[REPLAN] {query}", replanning=True):
                yield chunk
            return

        # Build messages for synthesis — OpenAI/Groq tool-calling format
        # Assistant message must include the tool_calls field from the planner response
        assistant_msg: dict = {
            "role": "assistant",
            "content": plan_response.choices[0].message.content or "",
        }
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in tool_calls
            ]

        # Tool results: role="tool" with tool_call_id (OpenAI format)
        tool_result_msgs: list[dict] = [
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(results_map.get(tc.id, {})),
            }
            for tc in tool_calls
        ]

        messages_with_results: list[dict] = (
            messages + [assistant_msg] + tool_result_msgs
        )

        # P4: Reflection — only on analytics + forecast (Token Opt 3)
        if query_type in REFLECTION_REQUIRED and results_list:
            grounded = await self._reflect(messages_with_results, results_list)
            if not grounded:
                # Append critic note silently — no user-visible message
                # (critic fires on prompt-context numbers too, causing false positives)
                # Append critic note as a new user message — safe for OpenAI format
                messages_with_results = messages_with_results + [{
                    "role": "user",
                    "content": "[CRITIC: Every number must come from tool results only. Rethink.]",
                }]

        # Final synthesis — Sonnet/70b streams to user (Token Opt 4)
        try:
            stream = await self._client.chat.completions.create(
                model=SYNTHESIS_MODEL,
                max_tokens=2048,
                messages=[{"role": "system", "content": system}] + messages_with_results,
                stream=True,
            )
        except Exception as e:
            yield f"I encountered an error generating the response. ({type(e).__name__})"
            return

        full_response = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_response += delta
                yield delta

        # P18: Post-output guardrail check — log only, never show warning to user
        # Numbers come from system prompt business context which the guardrail doesn't scan,
        # so false positives are common. Confidence is still used in logs.
        validated = validate_output(full_response, results_list)

        # P8: Update memory — await because add() is async (Patch 1)
        await memory.add(session_id, query, full_response)

        # P19: Structured log
        logger.info(json.dumps({
            "trace_id": trace_id,
            "query_type": query_type,
            "tool_calls": [tc.function.name for tc in tool_calls],
            "coverage": coverage,
            "latency_ms": round((time.time() - start) * 1000),
            "confidence": validated.get("confidence", "medium"),
            "guardrail_passed": validated["passed"],
            "replanning": replanning,
        }))

    # ── P2: Query classifier ───────────────────────────────────────────────────

    def _classify(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ("forecast", "predict", "next month", "revenue", "weighted")):
            return "forecast"
        if any(w in q for w in ("order", "work", "sla", "delivery", "overdue", "invoice")):
            return "operational"
        return "analytics"

    # ── P3 + Patch 7: parallel tool execution, position-independent result map ─

    async def _execute_tools(self, tool_calls: list) -> dict[str, dict]:
        results = await asyncio.gather(*[
            execute_tool(tc.function.name, json.loads(tc.function.arguments or "{}") or {})
            for tc in tool_calls
        ])
        return {tc.id: result for tc, result in zip(tool_calls, results)}

    # ── P11 + Patch 8: dynamic coverage threshold ─────────────────────────────

    def _check_coverage(self, query: str, results: list) -> float:
        if not results:
            return 0.0
        total_records = sum(
            r.get("quality_report", {}).get("records_used", 0)
            for r in results if isinstance(r, dict)
        )
        q = query.lower()
        expected = 50 if any(
            w in q for w in ("all", "total", "pipeline", "summary", "every")
        ) else 5
        return min(1.0, total_records / expected)

    # ── P4: Reflection critic ─────────────────────────────────────────────────

    async def _reflect(self, messages: list, results: list) -> bool:
        critic_prompt = (
            "You are a fact-checker. Reply ONLY with YES or NO. "
            "Are all numbers in the planned response directly sourced from the tool results provided? "
            "No hallucination allowed."
        )
        try:
            resp = await self._client.chat.completions.create(
                model=CRITIC_MODEL,
                max_tokens=5,
                messages=[{"role": "system", "content": critic_prompt}] + messages,
            )
            text = resp.choices[0].message.content or "NO"
            return "YES" in text.upper()
        except Exception:
            return True  # fail open — never block response for critic failure
