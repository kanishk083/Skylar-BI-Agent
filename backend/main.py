"""
main.py — FastAPI app, routes, CORS, startup
P19: Structured JSON logging configured here
"""
import json
import logging
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

from models.schemas import ChatRequest
from agent.orchestrator import Orchestrator

# P19: Configure structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

app = FastAPI(title="Skylark BI Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()


@app.post("/chat")
async def chat(req: ChatRequest, x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")

    async def stream():
        try:
            async for chunk in orchestrator.run(req.session_id, req.query):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'chunk': f'Error: {type(e).__name__} — please retry.'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Skylark BI Agent"}


@app.get("/briefing")
async def briefing(x_api_key: str = Header(...)):
    """P11 differentiator: auto-generates founder morning briefing — no query needed."""
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")

    import uuid
    session_id = str(uuid.uuid4())
    query = (
        "Give me a complete founder morning briefing: "
        "pipeline health, at-risk deals, overdue work orders, and revenue forecast this month."
    )

    async def stream():
        try:
            async for chunk in orchestrator.run(session_id, query):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'chunk': f'Briefing error: {type(e).__name__}'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
