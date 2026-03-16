from pydantic import BaseModel, Field
import uuid


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = Field(..., min_length=1, max_length=500)


class ToolResult(BaseModel):
    tool_name: str
    data: dict
    quality_report: dict  # records_used, records_excluded, exclusion_reasons
    confidence: str       # high | medium | low
