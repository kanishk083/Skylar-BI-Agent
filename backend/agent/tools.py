"""
tools.py — P5: 5 typed tool definitions + executors
Uses OpenAI-compatible function schema (Groq format)
"""
from integrations.monday_client import MondayClient
from agent.cleaner import clean_and_enrich

monday = MondayClient()

# P5: Strict schemas in OpenAI/Groq function-calling format
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_at_risk_deals",
            "description": (
                "Returns deals stuck in a pipeline stage longer than average. "
                "Use for risk, stale pipeline, or at-risk queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days_threshold": {
                        "type": "integer",
                        "description": "Days in stage to flag as at-risk",
                        "default": 30,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_summary",
            "description": (
                "Returns total pipeline value, count by stage, and weighted revenue forecast. "
                "Use for pipeline, funnel, or total value queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_work_orders",
            "description": (
                "Returns work orders filtered by status or SLA breach. "
                "Use for work order, delivery, invoice, or SLA queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["all", "overdue", "in_progress", "completed"],
                        "description": "Filter by work order status",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 200,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomalies",
            "description": (
                "Detects outliers vs historical baseline — "
                "deals with unusually high/low values, orders with extreme delays."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue_forecast",
            "description": (
                "Calculates weighted revenue forecast using deal probability x value. "
                "Use for forecast, projection, or expected revenue queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["this_month", "next_month", "this_quarter"],
                        "description": "Forecast period",
                    }
                },
                "required": [],
            },
        },
    },
]


async def execute_tool(name: str, inputs: dict) -> dict:
    handlers: dict = {
        "get_at_risk_deals":    monday.get_deals,
        "get_pipeline_summary": monday.get_pipeline,
        "get_work_orders":      monday.get_work_orders,
        "get_anomalies":        monday.get_anomalies,
        "get_revenue_forecast": monday.get_forecast,
    }
    # Groq may return arguments as JSON null — guard against that
    safe_inputs = inputs if isinstance(inputs, dict) else {}
    raw = await handlers[name](**safe_inputs)
    return clean_and_enrich(name, raw)
