"""
Test Product Agent — tests intent classification and response generation.

Run with: python tests/test_product_agent.py
(from the backend directory)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.shopify_client import ShopifyClient
from tools.vector_store import VectorStore
from agents.product_agent import ProductAgent


async def main():
    print("=" * 60)
    print("  Aria — Product Agent Tests")
    print("=" * 60)
    print()

    # --- Setup ---
    print("Setting up...")
    shopify = ShopifyClient(use_mock=True)
    store = VectorStore(use_mock=True)
    await store.load_products(shopify)
    agent = ProductAgent(vector_store=store, use_mock=True)
    print("Ready!")
    print()

    # --- Test conversations ---
    test_messages = [
        "Hi there!",
        "I'm looking for something warm for winter",
        "Do you have any shoes?",
        "How much is the leather bag?",
        "What's the difference between the sweater and the jacket?",
        "I need a gift for my friend",
        "Do you have sustainable clothing options?",
        "What sizes are available for the t-shirt?",
    ]

    for msg in test_messages:
        print(f"Customer: {msg}")
        result = await agent.answer(msg)
        print(f"Intent:   {result['intent']}")
        print(f"Aria:     {result['response']}")
        print(f"Products: {[p['title'] for p in result['products'][:2]]}")
        print("-" * 50)
        print()

    print("=" * 60)
    print("  All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())