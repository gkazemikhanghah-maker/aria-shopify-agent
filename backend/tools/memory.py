"""
Memory Store — Cross-session customer memory using Redis.

This is Aria's key differentiator vs Dori:
- Remembers what customers asked about
- Remembers preferences (size, style, budget)
- Enables personalized greetings on return visits

Each customer gets a session_id (cookie-based in the widget).
Memory is stored as a JSON object in Redis with TTL.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MEMORY_TTL = 60 * 60 * 24 * 30  # 30 days
MEMORY_PREFIX = "aria:memory:"
MAX_INTERACTIONS = 20  # Keep last N interactions


# ---------------------------------------------------------------------------
# Customer Memory Data
# ---------------------------------------------------------------------------

def empty_memory() -> dict:
    """Create a fresh memory object for a new customer."""
    return {
        "session_id": "",
        "first_seen": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
        "visit_count": 0,
        "interactions": [],
        "viewed_products": [],
        "preferences": {
            "budget": None,
            "style": None,
            "sizes": [],
            "categories": [],
        },
        "cart_interest": [],
    }


# ---------------------------------------------------------------------------
# Memory Store
# ---------------------------------------------------------------------------

class MemoryStore:
    """
    Manages cross-session customer memory in Redis.

    Usage:
        store = MemoryStore()
        store = MemoryStore(use_mock=True)

        memory = await store.get_memory("session_123")
        await store.bump_visit("session_123")
        await store.save_interaction("session_123", "user", "Do you have sneakers?")
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        use_mock: bool = False,
    ):
        self.use_mock = use_mock

        if use_mock:
            logger.info("MemoryStore running in MOCK mode (in-memory dict)")
            self._mock_data: dict[str, dict] = {}
            self.client = None
        else:
            logger.info(f"MemoryStore connecting to Redis at {url}")
            self.client = redis.from_url(url, decode_responses=True)

    # -- Core CRUD ----------------------------------------------------------

    async def get_memory(self, session_id: str) -> dict:
        """Get or create memory for a session. Does NOT increment visit_count."""
        if self.use_mock:
            if session_id not in self._mock_data:
                mem = empty_memory()
                mem["session_id"] = session_id
                self._mock_data[session_id] = mem
            return self._mock_data[session_id]

        key = f"{MEMORY_PREFIX}{session_id}"
        raw = await self.client.get(key)

        if raw:
            return json.loads(raw)

        # New customer
        mem = empty_memory()
        mem["session_id"] = session_id
        await self._save(session_id, mem)
        return mem

    async def _save(self, session_id: str, memory: dict) -> None:
        """Save memory to Redis with TTL."""
        memory["last_seen"] = datetime.now().isoformat()

        if self.use_mock:
            self._mock_data[session_id] = memory
            return

        key = f"{MEMORY_PREFIX}{session_id}"
        await self.client.set(key, json.dumps(memory), ex=MEMORY_TTL)

    # -- Visit tracking -----------------------------------------------------

    async def bump_visit(self, session_id: str) -> dict:
        """Increment visit count. Call once per new session/connection."""
        mem = await self.get_memory(session_id)
        mem["visit_count"] = mem.get("visit_count", 0) + 1
        await self._save(session_id, mem)
        return mem

    # -- Interactions -------------------------------------------------------

    async def save_interaction(
        self, session_id: str, role: str, content: str
    ) -> None:
        """Save a chat interaction to memory."""
        mem = await self.get_memory(session_id)

        mem["interactions"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep only last N
        if len(mem["interactions"]) > MAX_INTERACTIONS:
            mem["interactions"] = mem["interactions"][-MAX_INTERACTIONS:]

        await self._save(session_id, mem)

    # -- Product tracking ---------------------------------------------------

    async def add_viewed_product(
        self, session_id: str, product_id: int, title: str
    ) -> None:
        """Track that a customer viewed/asked about a product."""
        mem = await self.get_memory(session_id)

        existing_ids = [p["id"] for p in mem["viewed_products"]]
        if product_id not in existing_ids:
            mem["viewed_products"].append({
                "id": product_id,
                "title": title,
                "timestamp": datetime.now().isoformat(),
            })

        await self._save(session_id, mem)

    async def add_cart_interest(
        self, session_id: str, product_id: int, title: str
    ) -> None:
        """Track strong interest (asked about price, size, availability)."""
        mem = await self.get_memory(session_id)

        existing_ids = [p["id"] for p in mem["cart_interest"]]
        if product_id not in existing_ids:
            mem["cart_interest"].append({
                "id": product_id,
                "title": title,
                "timestamp": datetime.now().isoformat(),
            })

        await self._save(session_id, mem)

    # -- Preferences --------------------------------------------------------

    async def update_preference(
        self, session_id: str, key: str, value
    ) -> None:
        """Update a customer preference."""
        mem = await self.get_memory(session_id)

        if key in mem["preferences"]:
            if isinstance(mem["preferences"][key], list):
                if value not in mem["preferences"][key]:
                    mem["preferences"][key].append(value)
            else:
                mem["preferences"][key] = value

        await self._save(session_id, mem)

    # -- Context builder (for the agent) ------------------------------------

    async def get_context_summary(self, session_id: str) -> str:
        """Build a natural language summary for the agent."""
        mem = await self.get_memory(session_id)

        parts = []

        # Returning customer?
        if mem["visit_count"] > 1:
            parts.append(f"This is a returning customer (visit #{mem['visit_count']}).")

        # Previous interests
        if mem["viewed_products"]:
            product_names = [p["title"] for p in mem["viewed_products"][-5:]]
            parts.append(f"Previously looked at: {', '.join(product_names)}.")

        # Cart interest
        if mem["cart_interest"]:
            interested = [p["title"] for p in mem["cart_interest"]]
            parts.append(f"Showed strong interest in: {', '.join(interested)}.")

        # Preferences
        prefs = mem["preferences"]
        if prefs["budget"]:
            parts.append(f"Budget preference: {prefs['budget']}.")
        if prefs["style"]:
            parts.append(f"Style preference: {prefs['style']}.")
        if prefs["sizes"]:
            parts.append(f"Sizes: {', '.join(prefs['sizes'])}.")
        if prefs["categories"]:
            parts.append(f"Interested in: {', '.join(prefs['categories'])}.")

        # Recent conversation
        recent = mem["interactions"][-4:]
        if recent:
            convo = "\n".join(f"  {m['role']}: {m['content']}" for m in recent)
            parts.append(f"Recent conversation:\n{convo}")

        if not parts:
            return "New customer, no previous history."

        return "\n".join(parts)

    # -- Health check -------------------------------------------------------

    async def health_check(self) -> dict:
        """Check Redis connection."""
        if self.use_mock:
            return {
                "status": "ok",
                "mode": "mock",
                "sessions": len(self._mock_data),
            }

        try:
            await self.client.ping()
            return {"status": "ok", "mode": "live"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_memory_store() -> MemoryStore:
    """Create a MemoryStore from environment variables."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    use_mock = os.getenv("REDIS_USE_MOCK", "false").lower() in ("true", "1")

    if use_mock:
        return MemoryStore(use_mock=True)

    return MemoryStore(url=redis_url)