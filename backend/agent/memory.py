"""
memory.py — P8: Sliding window memory + async compression
Patches applied:
  P1: _compress() and add() are fully async — uses AsyncGroq, never blocks event loop
Token Opt 5: Haiku/8b-instant + max_tokens=100 for compression
"""
import os
from collections import defaultdict
from openai import AsyncOpenAI

_store: dict[str, list] = defaultdict(list)
MAX_TURNS = 10

# Token Opt 5: cheapest model, strict 100 token budget
COMPRESS_MODEL = "llama-3.1-8b-instant"


class MemoryStore:
    def __init__(self) -> None:
        self._store = _store

    def get(self, session_id: str) -> list:
        return self._store[session_id].copy()

    async def add(self, session_id: str, query: str, response: str) -> None:
        self._store[session_id].append({"role": "user", "content": query})
        self._store[session_id].append({"role": "assistant", "content": response})

        # P8: compress if over window
        if len(self._store[session_id]) > MAX_TURNS * 2:
            old = self._store[session_id][: -MAX_TURNS * 2]
            # Patch 1: await async compression — never block
            summary = await self._compress(old)
            self._store[session_id] = [
                {"role": "user", "content": f"[Earlier context summary]: {summary}"},
                {"role": "assistant", "content": "Understood. I have context from our earlier conversation."},
            ] + self._store[session_id][-MAX_TURNS * 2 :]

    async def _compress(self, turns: list) -> str:
        # Token Opt 5: truncate each turn to 150 chars before sending
        joined = "\n".join(
            f"{t['role']}: {t['content'][:150]}" for t in turns
        )
        client = AsyncOpenAI(
            api_key=os.getenv("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1",
        )
        try:
            resp = await client.chat.completions.create(
                model=COMPRESS_MODEL,
                max_tokens=100,  # strict — summary only
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Summarize in 2 sentences, keep all numbers:\n{joined}"
                        ),
                    }
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception:
            # Never let compression failure crash the request
            return "Earlier conversation context unavailable."
