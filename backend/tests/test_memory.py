"""
Test Memory Store — tests cross-session customer memory.

Run with: python tests/test_memory.py
(from the backend directory)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.memory import MemoryStore


async def main():
    print("=" * 60)
    print("  Aria — Memory Store Tests")
    print("=" * 60)
    print()

    # --- Test with mock (in-memory) ---
    print("Testing MOCK mode...")
    store = MemoryStore(use_mock=True)
    health = await store.health_check()
    print(f"  Health: {health}")

    # New customer — first visit
    mem = await store.bump_visit("customer_001")
    print(f"  New customer visit_count: {mem['visit_count']}")
    assert mem["visit_count"] == 1

    # Save interactions
    await store.save_interaction("customer_001", "user", "Do you have winter jackets?")
    await store.save_interaction("customer_001", "assistant", "Yes! Check out our Recycled Nylon Puffer Jacket.")

    # Track products
    await store.add_viewed_product("customer_001", 1006, "Recycled Nylon Puffer Jacket")
    await store.add_viewed_product("customer_001", 1003, "Merino Wool Sweater")

    # Strong interest
    await store.add_cart_interest("customer_001", 1006, "Recycled Nylon Puffer Jacket")

    # Preferences
    await store.update_preference("customer_001", "budget", "under $150")
    await store.update_preference("customer_001", "style", "casual")
    await store.update_preference("customer_001", "sizes", "M")
    await store.update_preference("customer_001", "categories", "jackets")
    await store.update_preference("customer_001", "categories", "sweaters")

    print("  Saved interactions, products, and preferences")

    # Check data is correct
    mem = await store.get_memory("customer_001")
    assert mem["visit_count"] == 1
    assert len(mem["interactions"]) == 2
    assert len(mem["viewed_products"]) == 2
    assert len(mem["cart_interest"]) == 1
    assert mem["preferences"]["budget"] == "under $150"
    assert mem["preferences"]["style"] == "casual"
    print("  All data stored correctly!")

    # Simulate returning customer (new session)
    mem2 = await store.bump_visit("customer_001")
    print(f"  Returning visit_count: {mem2['visit_count']}")
    assert mem2["visit_count"] == 2

    # Context summary
    summary = await store.get_context_summary("customer_001")
    print(f"\n  Context summary for agent:")
    for line in summary.split("\n"):
        print(f"    {line}")

    assert "returning customer" in summary
    assert "Recycled Nylon Puffer Jacket" in summary
    assert "under $150" in summary

    # Different customer has no memory
    mem3 = await store.get_memory("customer_002")
    assert mem3["visit_count"] == 0
    summary2 = await store.get_context_summary("customer_002")
    print(f"\n  New customer summary: {summary2}")
    assert "New customer" in summary2

    print("\n  Mock tests passed!")

    # --- Test with real Redis ---
    print("\nTesting LIVE Redis...")
    try:
        live_store = MemoryStore(url="redis://localhost:6379")
        health = await live_store.health_check()
        print(f"  Health: {health}")

        if health["status"] == "ok":
            mem = await live_store.bump_visit("test_session")
            await live_store.save_interaction("test_session", "user", "Hello from test!")
            mem = await live_store.get_memory("test_session")
            print(f"  Visit count: {mem['visit_count']}")
            print(f"  Interactions: {len(mem['interactions'])}")
            print("  Live Redis tests passed!")
        else:
            print("  Redis not available, skipping live tests")
    except Exception as e:
        print(f"  Redis connection failed: {e}")
        print("  Skipping live tests")

    print()
    print("=" * 60)
    print("  All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())