"""
Aria Setup — Load Shopify product catalog into Qdrant.

This script:
1. Connects to Shopify (or uses mock data)
2. Fetches all products
3. Embeds them using sentence-transformers
4. Stores them in Qdrant for semantic search

Usage:
    # With mock data (no credentials needed):
    python setup.py

    # With real Shopify store:
    set SHOPIFY_STORE_URL=aria-demo.myshopify.com
    set SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
    python setup.py

    # Force reload (delete existing collection first):
    python setup.py --reload
"""

import asyncio
import sys
import logging

from tools.shopify_client import create_shopify_client
from tools.vector_store import VectorStore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    reload = "--reload" in sys.argv

    print()
    print("=" * 60)
    print("  Aria Setup — Loading Product Catalog")
    print("=" * 60)
    print()

    # 1. Shopify client
    logger.info("Connecting to Shopify...")
    shopify = create_shopify_client()
    health = await shopify.health_check()
    logger.info(f"Shopify: {health}")

    if health["status"] != "ok":
        logger.error("Shopify connection failed! Check your credentials.")
        sys.exit(1)

    # 2. Preview products
    products = await shopify.get_products(limit=250)
    logger.info(f"Found {len(products)} products:")
    for p in products:
        logger.info(f"  -> {p.title} | {p.price_range} | {len(p.variants)} variants")
    print()

    # 3. Vector store
    logger.info("Connecting to Qdrant...")
    store = VectorStore()

    # Reload if requested
    if reload:
        logger.info("--reload flag: deleting existing collection...")
        try:
            store.delete_collection()
        except Exception:
            pass  # Collection might not exist

    # 4. Load products
    logger.info("Embedding and loading products into Qdrant...")
    count = await store.load_products(shopify)
    print()

    # 5. Verify
    stats = store.get_stats()
    logger.info(f"Collection stats: {stats}")
    print()

    # 6. Quick search test
    logger.info("Running quick search test...")
    test_queries = ["winter jacket", "casual shoes", "gift idea"]
    for q in test_queries:
        results = await store.search(q, top_k=2)
        top = results[0] if results else None
        if top:
            logger.info(f"  '{q}' -> {top['title']} (score: {top['score']:.3f})")
        else:
            logger.info(f"  '{q}' -> no results")

    print()
    print("=" * 60)
    print(f"  Setup complete! {count} products loaded into Qdrant.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())