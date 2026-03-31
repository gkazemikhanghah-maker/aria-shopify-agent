"""
Test Vector Store — loads mock products and runs semantic search.

Run with: python backend/tests/test_vector_store.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.shopify_client import ShopifyClient
from tools.vector_store import VectorStore


async def test_load_and_search():
    print("=" * 60)
    print("  Aria — Vector Store Tests")
    print("=" * 60)
    print()

    # --- Setup ---
    print("⏳ Creating mock Shopify client...")
    shopify = ShopifyClient(use_mock=True)

    print("⏳ Creating vector store (in-memory)...")
    store = VectorStore(use_mock=True)

    # --- Load products ---
    print("⏳ Loading products into Qdrant (embedding, first time may take a moment)...")
    count = await store.load_products(shopify)
    print(f"✅ Loaded {count} products into vector store")
    print()

    # --- Stats ---
    stats = store.get_stats()
    print(f"📊 Collection stats: {stats}")
    print()

    # --- Search tests ---
    test_queries = [
        ("warm winter clothing", None),
        ("something casual to wear everyday", None),
        ("shoes", None),
        ("sustainable fashion", None),
        ("gift for someone", None),
        ("leather bag", None),
    ]

    for query, product_type in test_queries:
        print(f"🔍 Search: \"{query}\"")
        results = await store.search(query, top_k=3, product_type=product_type)
        for i, r in enumerate(results, 1):
            print(f"   {i}. {r['title']} ({r['price_range']}) — score: {r['score']:.3f}")
        print()

    # --- Filtered search ---
    print(f"🔍 Search: \"comfortable\" (filter: Shoes)")
    results = await store.search("comfortable", top_k=3, product_type="Shoes")
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['title']} ({r['price_range']}) — score: {r['score']:.3f}")
    print()

    print("=" * 60)
    print("  All tests passed! 🎉")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_load_and_search())