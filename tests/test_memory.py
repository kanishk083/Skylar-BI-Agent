import pytest
from unittest.mock import AsyncMock, patch
from agent.memory import MemoryStore


@pytest.fixture
def store():
    s = MemoryStore()
    s._store.clear()
    return s


def test_get_empty_session_returns_empty_list(store):
    assert store.get("new-session") == []


@pytest.mark.asyncio
async def test_add_stores_turns(store):
    await store.add("s1", "hello", "world")
    history = store.get("s1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "world"


@pytest.mark.asyncio
async def test_no_compression_under_window(store):
    with patch.object(store, "_compress", new_callable=AsyncMock) as mock_compress:
        for i in range(5):
            await store.add("s1", f"q{i}", f"a{i}")
        mock_compress.assert_not_called()


@pytest.mark.asyncio
async def test_compression_triggered_over_window(store):
    with patch.object(store, "_compress", new_callable=AsyncMock, return_value="summary text") as mock_compress:
        for i in range(11):
            await store.add("s1", f"q{i}", f"a{i}")
        mock_compress.assert_called()


@pytest.mark.asyncio
async def test_after_compression_history_has_summary(store):
    with patch.object(store, "_compress", new_callable=AsyncMock, return_value="Earlier: 10 turns discussed pipeline."):
        for i in range(11):
            await store.add("s1", f"question {i}", f"answer {i}")
    history = store.get("s1")
    summary_turns = [t for t in history if "Earlier" in t.get("content", "")]
    assert len(summary_turns) >= 1
