"""
Aria API v0.3 — Now with configurable personas.

New:
    GET  /personas         — List available personas
    POST /persona/switch   — Switch active persona
    Persona-driven responses in chat

Usage:
    cd backend
    uvicorn api.main:app --reload --port 8000
"""

import os
import json
import logging
import uuid
import asyncio

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tools.shopify_client import create_shopify_client
from tools.vector_store import VectorStore
from tools.memory import create_memory_store
from persona.persona_engine import PersonaEngine
from agents.product_agent import ProductAgent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Aria — AI Sales Agent",
    description="Persona-driven AI shopping assistant",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

shopify_client = None
vector_store = None
memory_store = None
persona_engine = None
product_agent = None
is_ready = False


@app.on_event("startup")
async def startup():
    global shopify_client, vector_store, memory_store, persona_engine, product_agent

    logger.info("Starting Aria API v0.3...")

    # 1. Shopify
    shopify_client = create_shopify_client()
    health = await shopify_client.health_check()
    logger.info(f"Shopify: {health}")

    # 2. Vector store
    use_mock_qdrant = os.getenv("QDRANT_USE_MOCK", "false").lower() in ("true", "1")
    vector_store = VectorStore(use_mock=use_mock_qdrant)

    # 3. Memory
    memory_store = create_memory_store()
    mem_health = await memory_store.health_check()
    logger.info(f"Memory: {mem_health}")

    # 4. Persona Engine
    persona_engine = PersonaEngine()
    default_persona = os.getenv("ARIA_PERSONA", "fashion_influencer")
    logger.info(f"Personas available: {persona_engine.list_personas()}")
    logger.info(f"Default persona: {default_persona}")

    # 5. Product Agent
    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    product_agent = ProductAgent(
        vector_store=vector_store,
        memory_store=memory_store,
        persona_engine=persona_engine,
        persona_name=default_persona,
        use_mock=not has_api_key,
    )

    if has_api_key:
        logger.info("Claude API Key found — LIVE AI responses!")
    else:
        logger.info("No API Key — mock responses")

    logger.info("Aria API v0.3 ready!")
    asyncio.create_task(load_products_background())


async def load_products_background():
    global is_ready
    try:
        stats = vector_store.get_stats()
        if stats.get("status") == "error" or stats.get("points_count", 0) == 0:
            logger.info("Loading products (background)...")
            count = await vector_store.load_products(shopify_client)
            logger.info(f"Loaded {count} products")
        else:
            logger.info(f"Already have {stats['points_count']} products")
        is_ready = True
    except Exception as e:
        logger.error(f"Product loading failed: {e}")
        is_ready = True


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    products: list[dict] = []
    intent: str = ""
    persona: str = ""


class SwitchPersonaRequest(BaseModel):
    persona: str


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    qdrant_stats = vector_store.get_stats() if vector_store else {}
    mem_health = await memory_store.health_check() if memory_store else {}
    return {
        "status": "ok",
        "service": "aria-api",
        "version": "0.3.0",
        "ready": is_ready,
        "persona": product_agent.persona_name if product_agent else None,
        "claude": "live" if (product_agent and not product_agent.use_mock) else "mock",
        "qdrant": qdrant_stats,
        "memory": mem_health,
    }


@app.get("/personas")
async def list_personas():
    """List all available personas."""
    personas = []
    for name in persona_engine.list_personas():
        config = persona_engine.get_persona(name)
        personas.append({
            "name": name,
            "role": config.get("role", ""),
            "tone": config.get("tone", ""),
            "greeting": config.get("greeting", ""),
            "active": name == product_agent.persona_name,
        })
    return {"personas": personas, "active": product_agent.persona_name}


@app.post("/persona/switch")
async def switch_persona(request: SwitchPersonaRequest):
    """Switch the active persona."""
    available = persona_engine.list_personas()
    if request.persona not in available:
        return {"error": f"Persona '{request.persona}' not found", "available": available}

    product_agent.switch_persona(request.persona)
    return {
        "status": "ok",
        "persona": request.persona,
        "greeting": product_agent.greeting,
    }


@app.get("/products")
async def list_products():
    products = await shopify_client.get_products()
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "title": p.title,
                "price_range": p.price_range,
                "product_type": p.product_type,
                "image": p.primary_image,
            }
            for p in products
        ],
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    logger.info(f"Chat [{request.session_id}]: {request.message}")

    if not is_ready:
        return ChatResponse(
            response="Give me a sec, I'm warming up! ✨",
            products=[],
            intent="loading",
            persona=product_agent.persona_name,
        )

    result = await product_agent.answer(
        question=request.message,
        session_id=request.session_id,
        top_k=3,
    )

    return ChatResponse(
        response=result["response"],
        products=result["products"],
        intent=result["intent"],
        persona=result["persona"],
    )


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())[:8]
    logger.info(f"WS connected — session: {session_id}")

    if memory_store:
        await memory_store.bump_visit(session_id)

    conversation_history = []

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            client_session = message_data.get("session_id", session_id)

            if not user_message:
                continue

            logger.info(f"WS [{client_session}]: {user_message}")

            if not is_ready:
                await websocket.send_json({
                    "type": "response",
                    "response": "Give me a sec, I'm warming up! ✨",
                    "products": [],
                    "intent": "loading",
                    "persona": product_agent.persona_name,
                })
                continue

            result = await product_agent.answer(
                question=user_message,
                session_id=client_session,
                top_k=3,
                conversation_history=conversation_history,
            )

            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": result["response"]})
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]

            await websocket.send_json({
                "type": "response",
                "response": result["response"],
                "products": result["products"],
                "intent": result["intent"],
                "persona": result["persona"],
                "session_id": client_session,
            })

    except WebSocketDisconnect:
        logger.info(f"WS disconnected — session: {session_id}")
    except Exception as e:
        logger.error(f"WS error: {e}")
        await websocket.close()