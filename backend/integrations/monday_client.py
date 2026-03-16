"""
monday_client.py — P16: Resource-aware Monday.com GraphQL client
Patches applied:
  P2: 429 retry + stale cache fallback
  P9: asyncio.Semaphore(3) — max 3 concurrent requests
"""
import hashlib
import asyncio
import os
import httpx
from httpx import HTTPStatusError, TimeoutException
from integrations.cache import TTLCache

MONDAY_API = "https://api.monday.com/v2"
cache = TTLCache(ttl_seconds=300)  # 5-min TTL

# Patch 9: cap concurrent Monday.com calls at 3 to stay under rate limit
_monday_semaphore = asyncio.Semaphore(3)


class MondayClient:
    def __init__(self) -> None:
        self.token: str = os.getenv("MONDAY_API_TOKEN", "")
        self.deal_board_id: str = os.getenv("MONDAY_DEAL_BOARD_ID", "")
        self.order_board_id: str = os.getenv("MONDAY_ORDER_BOARD_ID", "")

    async def _query(self, gql: str, variables: dict = {}) -> dict:
        # Deterministic cache key — not Python's non-deterministic hash()
        cache_key = hashlib.md5(
            (gql + str(sorted(variables.items()))).encode()
        ).hexdigest()

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        async with _monday_semaphore:  # Patch 9
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        MONDAY_API,
                        json={"query": gql, "variables": variables},
                        headers={
                            "Authorization": self.token,
                            "Content-Type": "application/json",
                            "API-Version": "2024-01",
                        },
                    )
                    # Patch 2: handle 429 rate limit with one retry
                    if resp.status_code == 429:
                        wait = int(resp.headers.get("Retry-After", 2))
                        await asyncio.sleep(wait)
                        resp = await client.post(
                            MONDAY_API,
                            json={"query": gql, "variables": variables},
                            headers={
                                "Authorization": self.token,
                                "Content-Type": "application/json",
                                "API-Version": "2024-01",
                            },
                        )
                    resp.raise_for_status()
                    data = resp.json()

            except HTTPStatusError:
                # Patch 2: serve stale cache on HTTP error rather than crashing
                stale = cache.get_stale(cache_key)
                return stale if stale is not None else {}
            except TimeoutException:
                stale = cache.get_stale(cache_key)
                return stale if stale is not None else {}
            except Exception:
                stale = cache.get_stale(cache_key)
                return stale if stale is not None else {}

        cache.set(cache_key, data)
        return data

    # ── Board queries ──────────────────────────────────────────────────────────

    async def get_deals(self, days_threshold: int = 30) -> list:
        gql = """
        query ($boardId: ID!) {
          boards(ids: [$boardId]) {
            items_page(limit: 500) {
              items {
                id name
                column_values { id text value }
              }
            }
          }
        }"""
        data = await self._query(gql, {"boardId": self.deal_board_id})
        return self._parse_items(data)

    async def get_pipeline(self) -> list:
        return await self.get_deals()

    async def get_work_orders(self, status: str = "all", limit: int = 200) -> list:
        gql = """
        query ($boardId: ID!, $limit: Int!) {
          boards(ids: [$boardId]) {
            items_page(limit: $limit) {
              items {
                id name
                column_values { id text value }
              }
            }
          }
        }"""
        data = await self._query(gql, {"boardId": self.order_board_id, "limit": limit})
        return self._parse_items(data)

    async def get_anomalies(self) -> list:
        return await self.get_deals()

    async def get_forecast(self, period: str = "this_month") -> list:
        return await self.get_deals()

    # ── Column-value parser ────────────────────────────────────────────────────

    def _parse_items(self, data: dict) -> list:
        items: list[dict] = []
        try:
            for item in data["data"]["boards"][0]["items_page"]["items"]:
                row: dict = {"name": item["name"], "id": item["id"]}
                for col in item["column_values"]:
                    # prefer text (human-readable) over raw JSON value
                    row[col["id"]] = col["text"] or col["value"]
                items.append(row)
        except (KeyError, IndexError, TypeError):
            pass
        return items
