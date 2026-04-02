"""
Product Agent — Answers product questions using RAG + Claude + Memory + Persona.

Now persona-driven: the same product gets recommended differently
depending on the store's configured personality.
"""

import os
import logging
from typing import Optional

from anthropic import AsyncAnthropic

from tools.vector_store import VectorStore
from tools.memory import MemoryStore
from persona.persona_engine import PersonaEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SONNET_MODEL = "claude-sonnet-4-20250514"
HAIKU_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Product Agent
# ---------------------------------------------------------------------------

class ProductAgent:
    """
    Persona-driven product agent.

    Usage:
        engine = PersonaEngine()
        agent = ProductAgent(
            vector_store=store,
            memory_store=memory,
            persona_engine=engine,
            persona_name="fashion_influencer",
        )
        response = await agent.answer("Do you have warm jackets?", session_id="abc")
    """

    def __init__(
        self,
        vector_store: VectorStore,
        memory_store: Optional[MemoryStore] = None,
        persona_engine: Optional[PersonaEngine] = None,
        persona_name: str = "fashion_influencer",
        api_key: Optional[str] = None,
        use_mock: bool = False,
    ):
        self.vector_store = vector_store
        self.memory_store = memory_store
        self.persona_engine = persona_engine or PersonaEngine()
        self.persona_name = persona_name
        self.use_mock = use_mock or not (api_key or os.getenv("ANTHROPIC_API_KEY"))

        # Get system prompt from persona
        self.system_prompt = self.persona_engine.get_system_prompt(persona_name)
        self.greeting = self.persona_engine.get_greeting(persona_name)

        if not self.use_mock:
            self.client = AsyncAnthropic(api_key=api_key)
            logger.info(f"ProductAgent using Claude API (LIVE) — persona: {persona_name}")
        else:
            self.client = None
            logger.info(f"ProductAgent in MOCK mode — persona: {persona_name}")

    def switch_persona(self, persona_name: str) -> None:
        """Switch to a different persona at runtime."""
        self.persona_name = persona_name
        self.system_prompt = self.persona_engine.get_system_prompt(persona_name)
        self.greeting = self.persona_engine.get_greeting(persona_name)
        logger.info(f"Switched persona to: {persona_name}")

    async def answer(
        self,
        question: str,
        session_id: str = "default",
        top_k: int = 3,
        conversation_history: Optional[list[dict]] = None,
    ) -> dict:
        """Answer a customer question with persona + memory context."""

        # 1. Get memory context
        memory_context = ""
        if self.memory_store:
            memory_context = await self.memory_store.get_context_summary(session_id)

        # 2. Classify intent
        intent = await self._classify_intent(question)
        logger.info(f"Intent: {intent}")

        # 3. Search for relevant products
        products = await self.vector_store.search(question, top_k=top_k)
        logger.info(f"Found {len(products)} relevant products")

        # 4. Build product context
        product_context = self._build_product_context(products)

        # 5. Generate response with persona
        response_text = await self._generate_response(
            question=question,
            product_context=product_context,
            memory_context=memory_context,
            intent=intent,
            conversation_history=conversation_history,
        )

        # 6. Save to memory
        if self.memory_store:
            await self.memory_store.save_interaction(session_id, "user", question)
            await self.memory_store.save_interaction(session_id, "assistant", response_text)
            for p in products[:2]:
                await self.memory_store.add_viewed_product(
                    session_id, p["product_id"], p["title"]
                )
            if intent == "price_inquiry":
                for p in products[:1]:
                    await self.memory_store.add_cart_interest(
                        session_id, p["product_id"], p["title"]
                    )

        return {
            "response": response_text,
            "products": products,
            "intent": intent,
            "persona": self.persona_name,
        }

    # -- Intent classification (Haiku) --------------------------------------

    async def _classify_intent(self, question: str) -> str:
        if self.use_mock:
            return self._mock_classify(question)

        try:
            response = await self.client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=50,
                system="Classify the customer intent into exactly one category: greeting, product_search, price_inquiry, product_detail, comparison, objection, or general_question. Reply with ONLY the category name.",
                messages=[{"role": "user", "content": question}],
            )
            return response.content[0].text.strip().lower()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "general_question"

    @staticmethod
    def _mock_classify(question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["price", "cost", "how much", "expensive", "cheap"]):
            return "price_inquiry"
        if any(w in q for w in ["recommend", "suggest", "looking for", "need", "want"]):
            return "product_search"
        if any(w in q for w in ["compare", "difference", "vs", "better"]):
            return "comparison"
        if any(w in q for w in ["size", "fit", "material", "color"]):
            return "product_detail"
        if any(w in q for w in ["hi", "hello", "hey"]):
            return "greeting"
        return "general_question"

    # -- Product context builder --------------------------------------------

    @staticmethod
    def _build_product_context(products: list[dict]) -> str:
        if not products:
            return "No matching products found in the catalog."

        lines = []
        for i, p in enumerate(products, 1):
            tags = ", ".join(p.get("tags", []))
            lines.append(
                f"Product {i}: {p['title']}\n"
                f"  Type: {p.get('product_type', 'N/A')}\n"
                f"  Price: {p['price_range']}\n"
                f"  Tags: {tags}\n"
                f"  Relevance: {p['score']:.2f}"
            )
        return "\n\n".join(lines)

    # -- Response generation (Sonnet + Persona) -----------------------------

    async def _generate_response(
        self,
        question: str,
        product_context: str,
        memory_context: str,
        intent: str,
        conversation_history: Optional[list[dict]] = None,
    ) -> str:
        if self.use_mock:
            return self._mock_response(question, product_context, intent)

        messages = []
        if conversation_history:
            messages.extend(conversation_history)

        user_message = f"Customer question: {question}\nIntent: {intent}\n\n"

        if memory_context and "New customer" not in memory_context:
            user_message += f"What you know about this customer:\n{memory_context}\n\n"

        user_message += (
            f"Products from the catalog:\n{product_context}\n\n"
            f"Respond in character. Keep it short and natural."
        )
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.messages.create(
                model=SONNET_MODEL,
                max_tokens=300,
                system=self.system_prompt,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "Sorry, I'm having a moment — try asking again!"

    # -- Mock response ------------------------------------------------------

    @staticmethod
    def _mock_response(question: str, product_context: str, intent: str) -> str:
        if intent == "greeting":
            return "hey! welcome to the store ✨ what are you looking for today?"

        if "No matching products" in product_context:
            return "hmm i don't think we have that right now — can you describe it differently?"

        first_product = ""
        for line in product_context.split("\n"):
            if line.startswith("Product 1:"):
                first_product = line.replace("Product 1:", "").strip()
                break

        if intent == "price_inquiry":
            return f"ooh the {first_product} is such a good pick! let me pull up the price details for you."

        if intent == "comparison":
            return f"ok so the {first_product} is definitely the standout here — want me to break down why?"

        return f"honestly the {first_product} is one of my favorites right now. want to know more about it?"