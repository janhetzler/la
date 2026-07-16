"""
Serveur FastAPI exposant les agents comme des modèles OpenAI-compatible.
Chaque agent est accessible via /v1/chat/completions avec model="agent-<nom>".
"""
import time
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
from researcher_v2 import invoke_researcher_v2
from comms import invoke_comms
from supervisor import invoke_supervisor
from notes import invoke_notes
from code import invoke_code
from handoff import invoke_handoff
import asyncio


app = FastAPI(
    title="Local Agent — Agents API",
    description="OpenAI-compatible endpoint for LangGraph agents",
    version="0.1.0",
)


# ===== Schémas OpenAI-compatible =====
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


# ===== Registre des agents disponibles =====

AGENTS = {
    "agent-researcher": invoke_researcher_v2,
    "agent-comms": invoke_comms,
    "agent-notes": invoke_notes,
    "agent-code": invoke_code,
    "agent-handoff": invoke_handoff,
    "agent-local": invoke_supervisor,
}


# ===== Endpoints =====
@app.get("/v1/models")
async def list_models():
    """Open WebUI / LiteLLM appelle cet endpoint pour découvrir les modèles."""
    return {
        "object": "list",
        "data": [
            {
                "id": name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local-agent",
            }
            for name in AGENTS
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """Endpoint principal compatible OpenAI."""
    if req.model not in AGENTS:
        raise HTTPException(404, f"Unknown agent: {req.model}")
    
    # Récupère le dernier message utilisateur
    user_msg = ""
    for m in reversed(req.messages):
        if m.role == "user":
            user_msg = m.content
            break
    
    if not user_msg:
        raise HTTPException(400, "No user message found")
    
    # Invoque l'agent (synchrone pour l'instant)
    
    agent_fn = AGENTS[req.model]
    if asyncio.iscoroutinefunction(agent_fn):
        response_text = await agent_fn(user_msg)
    else:
        response_text = await asyncio.to_thread(agent_fn, user_msg)
    
    # Format OpenAI
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    
    if req.stream:
        # Streaming SSE — on envoie en un seul chunk (pas de vrai streaming pour l'instant)
        async def generate() -> AsyncIterator[str]:
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": response_text},
                    "finish_reason": None,
                }],
            }
            import json
            yield f"data: {json.dumps(chunk)}\n\n"
            
            done_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(done_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    # Non-streaming
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,  # placeholder
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok", "agents": list(AGENTS.keys())}