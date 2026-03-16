import pytest
from unittest.mock import AsyncMock, patch


def test_all_tool_schemas_have_required_fields():
    from agent.tools import TOOL_SCHEMAS
    for tool in TOOL_SCHEMAS:
        assert "type" in tool
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert len(fn["description"]) > 10


def test_tool_names_are_the_five_expected():
    from agent.tools import TOOL_SCHEMAS
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert names == {
        "get_at_risk_deals",
        "get_pipeline_summary",
        "get_work_orders",
        "get_anomalies",
        "get_revenue_forecast",
    }


@pytest.mark.asyncio
async def test_execute_tool_returns_clean_result():
    from agent.tools import execute_tool
    mock_raw = [
        {"name": "Deal A", "deal_value": "500000", "stage": "Proposal",
         "probability": "0.5", "owner": "OWNER_001"}
    ]
    with patch("agent.tools.monday") as mock_monday:
        mock_monday.get_deals = AsyncMock(return_value=mock_raw)
        result = await execute_tool("get_at_risk_deals", {"days_threshold": 30})
    assert "data" in result
    assert "quality_report" in result
    assert "confidence" in result


@pytest.mark.asyncio
async def test_execute_tool_unknown_name_raises():
    from agent.tools import execute_tool
    with pytest.raises(KeyError):
        await execute_tool("nonexistent_tool", {})
