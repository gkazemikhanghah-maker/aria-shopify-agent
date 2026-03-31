"""
Product Agent — Answers product questions using RAG + Claude + Memory.

This is the core agent that:
1. Takes a customer question
2. Loads customer memory (returning customer? preferences?)
3. Searches the vector store for relevant products
4. Sends context + question to Claude for a natural answer
"""

import os
import logging
from typing import Optional

from anthropic import AsyncAnthropic

from tools.vector_store import VectorStore
from tools.memory import MemoryStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SONNET_MODEL = "claude-sonnet-4-20250514"
HAIKU_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are Aria, a friendly and knowledgeable AI shopping assistant.

Your job is to help customers find the perfect products. You are:
- Warm, helpful, and conversational (not robotic)
- Knowledgeable about the products in the store
- Honest — if something isn't available or doesn't match, say so
- Proactive — suggest complementary products when relevant
- Concise — keep answers short and scannable (2-4 sentences max)

When answering:
- Use the product information provided to give accurate answers
- Include prices when mentioning products
- If multiple products match, briefly compare them
- If nothing matches well, say so honestly and suggest alternatives
- Never make up product details that aren't in the context
- If this is a returning customer, acknowledge their previous interests naturally
  (e.g. "Still thinking about that jacket?" or "Welcome back!")

Format: Use plain text. No markdown headers or bullet points.
Keep it conversational, like a real store associate would talk."""


# ---------------------------------------------------------------------------
# Product Agent
# ---------------------------------------------------------------------------

class ProductAgent:
    """
    Answers product questions using RAG (vector search) + Claude + Memory.

    Usage:
        agent = ProductAgent(vector_store=store, memory_store=memory)
        response = await agent.answer("Do you have warm jackets?", session_id="abc")
    """

    def __init__(
        self,
        vector_store: VectorStore,
        memory_store: Optional[MemoryStore] = None,
        api_key: Optional[str] = None,
        use_mock: bool = False,
    ):
        self.vector_store = vector_store
        self.memory_store = memory_store
        self.use_mock = use_mock or not (api_key or os.getenv("ANTHROPIC_API_KEY"))

        if not self.use_mock:
            self.client = AsyncAnthropic(api_key=api_key)
            logger.info("ProductAgent using Claude API (LIVE)")
        else:
            self.client = None
            logger.info("ProductAgent running in MOCK mode")

    async def answer(
        self,
        question: str,
        session_id: str = "default",
        top_k: int = 3,
        conversation_history: Optional[list[dict]] = None,
    ) -> dict:
        """
        Answer a customer question with memory context.
        """
        # 1. Get memory context
        memory_context = ""
        if self.memory_store:
            memory_context = await self.memory_store.get_context_summary(session_id)
            logger.info(f"Memory context: {memory_context[:100]}...")

        # 2. Classify intent
        intent = await self._classify_intent(question)
        logger.info(f"Intent: {intent}")

        # 3. Search for relevant products
        products = await self.vector_store.search(question, top_k=top_k)
        logger.info(f"Found {len(products)} relevant products")

        # 4. Build context from products
        product_context = self._build_product_context(products)

        # 5. Generate response
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

            # Track viewed products
            for p in products[:2]:
                await self.memory_store.add_viewed_product(
                    session_id, p["product_id"], p["title"]
                )

            # Track preferences from intent
            if intent == "price_inquiry":
                for p in products[:1]:
                    await self.memory_store.add_cart_interest(
                        session_id, p["product_id"], p["title"]
                    )

        return {
            "response": response_text,
            "products": products,
            "intent": intent,
        }

    # -- Intent classification (fast, uses Haiku) ---------------------------

    async def _classify_intent(self, question: str) -> str:
        """Classify the customer's intent using Haiku (fast + cheap)."""
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
                f"  Relevance score: {p['score']:.2f}"
            )
        return "\n\n".join(lines)

    # -- Response generation (uses Sonnet) ----------------------------------

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

        # Build messages
        messages = []

        if conversation_history:
            messages.extend(conversation_history)

        # Add current question with all context
        user_message = f"Customer question: {question}\n\nCustomer intent: {intent}\n\n"

        if memory_context and "New customer" not in memory_context:
            user_message += f"Customer memory (what we know about them):\n{memory_context}\n\n"

        user_message += (
            f"Relevant products from our catalog:\n{product_context}\n\n"
            f"Please answer the customer's question based on the products and memory above."
        )
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.messages.create(
                model=SONNET_MODEL,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "I'm sorry, I'm having trouble right now. Could you try asking again?"

    # -- Mock response ------------------------------------------------------

    @staticmethod
    def _mock_response(question: str, product_context: str, intent: str) -> str:
        if intent == "greeting":
            return "Hey there! Welcome to our store. I'm Aria, your shopping assistant. What are you looking for today?"

        if "No matching products" in product_context:
            return "I couldn't find anything matching that in our catalog. Could you describe what you're looking for differently?"

        first_product = ""
        for line in product_context.split("\n"):
            if line.startswith("Product 1:"):
                first_product = line.replace("Product 1:", "").strip()
                break

        if intent == "price_inquiry":
            return f"Great question! Our {first_product} is a popular choice. Check the product details for the latest pricing and available sizes."

        if intent == "comparison":
            return f"Good question! Let me help you compare. The {first_product} stands out for its quality. Want me to go into more detail on the differences?"

        return f"Based on what you're looking for, I'd recommend checking out our {first_product}. It's one of our most popular items! Want to know more about it?"