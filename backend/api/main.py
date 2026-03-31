"""
Aria API — FastAPI server with REST + WebSocket endpoints.

Endpoints:
    GET  /health          — Health check
    GET  /products        — List all products
    POST /chat            — Send a message, get a response
    WS   /ws/chat         — Real-time chat via WebSocket

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

# Load .env BEFORE anything else
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tools.shopify_client import create_shopify_client
from tools.vector_store import VectorStore
from tools.memory import create_memory_store
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
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Aria — AI Sales Agent",
    description="AI-powered shopping assistant for Shopify stores",
    version="0.2.0",
)

# CORS — allow widget from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global state (initialized on startup)
# ---------------------------------------------------------------------------

shopify_client = None
vector_store = None
memory_store = None
product_agent = None
is_ready = False


@app.on_event("startup")
async def startup():
    """Initialize services on server start. Heavy loading runs in background."""
    global shopify_client, vector_store, memory_store, product_agent

    logger.info("Starting Aria API v0.2...")

    # 1. Shopify client (instant)
    shopify_client = create_shopify_client()
    health = await shopify_client.health_check()
    logger.info(f"Shopify: {health}")

    # 2. Vector store (instant connection, products loaded in background)
    use_mock_qdrant = os.getenv("QDRANT_USE_MOCK", "false").lower() in ("true", "1")
    vector_store = VectorStore(use_mock=use_mock_qdrant)

    # 3. Memory store
    use_mock_redis = os.getenv("REDIS_USE_MOCK", "false").lower() in ("true", "1")
    if use_mock_redis:
        memory_store = create_memory_store()
    else:
        memory_store = create_memory_store()
    mem_health = await memory_store.health_check()
    logger.info(f"Memory: {mem_health}")

    # 4. Product agent
    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    product_agent = ProductAgent(
        vector_store=vector_store,
        memory_store=memory_store,
        use_mock=not has_api_key,
    )

    if has_api_key:
        logger.info("Claude API Key found — using LIVE AI responses!")
    else:
        logger.info("No API Key — using mock responses")

    logger.info("Aria API ready! (products loading in background)")

    # Load products in background so the server starts fast
    asyncio.create_task(load_products_background())


async def load_products_background():
    """Load products into vector store in background after server starts."""
    global is_ready
    try:
        stats = vector_store.get_stats()
        if stats.get("status") == "error" or stats.get("points_count", 0) == 0:
            logger.info("Loading products into vector store (background)...")
            count = await vector_store.load_products(shopify_client)
            logger.info(f"Background: loaded {count} products")
        else:
            logger.info(f"Vector store already has {stats['points_count']} products")
        is_ready = True
    except Exception as e:
        logger.error(f"Background product loading failed: {e}")
        is_ready = True  # Still mark as ready so the API works


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    products: list[dict] = []
    intent: str = ""


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    qdrant_stats = vector_store.get_stats() if vector_store else {"status": "not_initialized"}
    mem_health = await memory_store.health_check() if memory_store else {"status": "not_initialized"}
    return {
        "status": "ok",
        "service": "aria-api",
        "version": "0.2.0",
        "ready": is_ready,
        "claude": "live" if (product_agent and not product_agent.use_mock) else "mock",
        "qdrant": qdrant_stats,
        "memory": mem_health,
    }


@app.get("/products")
async def list_products():
    """List all products from Shopify."""
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
    """Send a message and get an AI response."""
    logger.info(f"Chat [{request.session_id}]: {request.message}")

    if not is_ready:
        return ChatResponse(
            response="I'm still warming up! Give me a few seconds and try again.",
            products=[],
            intent="loading",
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
    )


# ---------------------------------------------------------------------------
# WebSocket endpoint (for real-time chat in the widget)
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Real-time chat via WebSocket."""
    await websocket.accept()

    session_id = str(uuid.uuid4())[:8]
    logger.info(f"WebSocket connected — session: {session_id}")

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
                    "response": "I'm still warming up! Give me a few seconds and try again.",
                    "products": [],
                    "intent": "loading",
                    "session_id": client_session,
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
                "session_id": client_session,
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected — session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()