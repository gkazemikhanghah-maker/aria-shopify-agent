<div align="center">

# Architecture — Aria

A technical deep dive into how Aria works under the hood.

</div>

---

## Why This Architecture

The e-commerce chatbot market (Dori, Rep AI, Tidio, etc.) has converged on a standard pattern: embed a chat widget, connect it to an LLM, feed it the product catalog. It works. But it has a fundamental limitation.

**Every session starts from zero.**

A customer can spend 20 minutes exploring winter jackets, asking about sizes, comparing prices — and when they come back the next day, the chatbot has no memory of any of it. The conversation resets. The relationship is lost.

Aria was designed specifically to solve this. The architecture has three layers: intelligence, knowledge, and memory — each serving a distinct role.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  CUSTOMER BROWSER                                                │
│                                                                  │
│  React Chat Widget                                               │
│  ├── WebSocket (real-time, primary)                              │
│  └── REST API (automatic fallback)                               │
│                                                                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Product Agent                            │  │
│  │                                                             │  │
│  │  Message In                                                 │  │
│  │     │                                                       │  │
│  │     ├─→ ① Classify Intent (Claude Haiku)        ~200ms     │  │
│  │     ├─→ ② Search Products (Qdrant / keywords)   ~100ms     │  │
│  │     ├─→ ③ Load Memory Context (Redis)           ~50ms      │  │
│  │     ├─→ ④ Generate Response (Claude Sonnet)     ~1.5s      │  │
│  │     └─→ ⑤ Update Memory (Redis)                ~50ms       │  │
│  │                                                             │  │
│  │  Response Out                                               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────┐    ┌────────────┐    ┌─────────────────┐        │
│  │  Shopify   │    │  Qdrant    │    │  Redis           │        │
│  │  Client    │    │  Vector DB │    │  Memory Store    │        │
│  │            │    │            │    │                   │        │
│  │  • Catalog │    │  • 384-dim │    │  • Sessions       │        │
│  │  • Prices  │    │  • Cosine  │    │  • Preferences    │        │
│  │  • Variants│    │  • MiniLM  │    │  • History        │        │
│  │  • Mock    │    │  • Keyword │    │  • Viewed products│        │
│  │    fallback│    │    fallback│    │  • 30-day TTL     │        │
│  └────────────┘    └────────────┘    └─────────────────┘        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Intelligence

### The Two-Model Strategy

Not every customer message needs the same level of reasoning.

**Claude Haiku** handles intent classification — a lightweight task that needs speed, not depth. A customer says "How much is the leather bag?" and Haiku returns `price_inquiry` in ~200ms. This classification shapes how the agent responds and what memory gets updated.

**Claude Sonnet** handles the actual response. It receives three inputs: the classified intent, the matched products from vector search, and the customer's memory context. With all three, it generates a response that's natural, personalized, and commercially aware.

The system prompt instructs Sonnet to behave like a real store associate — mentioning prices naturally, comparing options when relevant, and acknowledging returning customers without being creepy about it.

### Intent Categories

| Intent | Example | Agent Behavior |
|:--|:--|:--|
| `greeting` | "Hey there" | Welcome message, show suggestions |
| `product_search` | "Something warm for winter" | Vector search, top matches |
| `price_inquiry` | "How much is the bag?" | Price focus, track as cart interest |
| `product_detail` | "What sizes do you have?" | Specific product info |
| `comparison` | "Sweater vs jacket?" | Side-by-side comparison |
| `objection` | "That's too expensive" | Handle objection, suggest alternatives |
| `general_question` | "Do you ship internationally?" | General store info |

---

## Layer 2: Knowledge

### Semantic Search with Qdrant

Every product in the Shopify catalog gets transformed into a 384-dimensional vector using `all-MiniLM-L6-v2`. The embedding captures semantic meaning — not just keywords.

This is why "something warm for winter" matches a recycled nylon puffer jacket, even though those exact words never appear in the product description. The vector space understands that "warm" and "winter" are semantically close to "puffer," "insulated," and "water-resistant."

**The embedding pipeline:**
```
Product title + type + vendor + price + tags + description
         ↓
   sentence-transformers (all-MiniLM-L6-v2)
         ↓
   384-dim vector → stored in Qdrant
         ↓
   Customer query embedded in same space
         ↓
   Cosine similarity → top K matches
```

**Production constraint:** The embedding model + PyTorch require ~800MB RAM. Render's free tier offers 512MB. Solution: fall back to keyword matching in production, let Claude compensate with its reasoning ability. Locally, full vector search runs via Qdrant.

### Shopify Integration

The Shopify client connects to any store via the Admin API. It normalizes products into a clean data model with variants, images, pricing, and tags. Every product can generate a `to_rag_text()` representation optimized for embedding.

For development, a mock catalog of 6 fashion products (T-shirts, chinos, sweaters, sneakers, bags, jackets) allows the full system to run without any API credentials.

---

## Layer 3: Memory

### The Differentiator

This is what separates Aria from Dori, Rep AI, and every other Shopify chatbot. Customer memory persists across sessions.

**What gets stored per customer:**

```json
{
  "session_id": "a3f8c2d1",
  "visit_count": 3,
  "first_seen": "2026-03-28",
  "last_seen": "2026-03-31",
  "viewed_products": [
    {"title": "Recycled Nylon Puffer Jacket", "timestamp": "..."},
    {"title": "Canvas Sneakers", "timestamp": "..."}
  ],
  "preferences": {
    "budget": "under $150",
    "style": "casual",
    "sizes": ["M"],
    "categories": ["jackets", "shoes"]
  },
  "cart_interest": [
    {"title": "Recycled Nylon Puffer Jacket"}
  ],
  "interactions": ["last 20 messages"]
}
```

**How the agent uses it:** Before generating any response, the agent calls `get_context_summary()` which produces a natural language summary:

> *"This is a returning customer (visit #3). Previously looked at: Puffer Jacket, Canvas Sneakers. Budget: under $150. Style: casual. Size: M."*

This summary is injected into Claude's prompt alongside the product search results. The result: responses that acknowledge history naturally.

### The Visit Count Bug

Early versions incremented `visit_count` inside `get_memory()`. Since every operation — saving interactions, tracking products, updating preferences — called `get_memory()` internally, a single user message could increment the visit counter 5-10 times.

The fix was architectural: `get_memory()` only reads. A separate `bump_visit()` method is called exactly once per WebSocket connection. Simple bug. Hours to find. One line to fix.

---

## Layer 4: Interface

### WebSocket-First, REST-Fallback

The widget connects via WebSocket for real-time, bidirectional communication. Messages appear instantly. Typing indicators work naturally.

But WebSocket connections fail on corporate firewalls, some mobile carriers, and certain proxy configurations. After 3 failed connection attempts, the widget automatically switches to REST API calls (`POST /chat`). The user experience remains identical — slightly higher latency, but fully functional.

### The Widget

Built with React + Vite + Tailwind CSS. Dark theme with a purple accent palette. Components:

- **ChatWindow** — Main chat interface with auto-scroll and connection state
- **MessageBubble** — User/assistant message rendering
- **ProductCard** — Inline product results with price, type, and relevance score
- **TypingIndicator** — Animated dots during response generation
- **Suggestion chips** — Quick-start buttons for new visitors

---

## Deployment Architecture

### The Free-Tier Challenge

Running an AI application with vector search and persistent memory on free infrastructure requires compromises. Here's how:

| Service | Local | Production |
|:--|:--|:--|
| Vector search | Qdrant (Docker, full embeddings) | Keyword matching (no GPU needed) |
| Memory | Redis (Docker) | In-memory dict (mock mode) |
| AI | Claude API | Claude API (same) |
| Backend | localhost:8000 | Render free tier (512MB) |
| Frontend | localhost:5173 | Vercel (CDN) |

### Lazy Loading

The embedding model takes 20+ seconds to load. Render's port scanner times out after 60 seconds. If the model loads during startup, the server never opens a port in time.

Solution: start the server immediately, load products in a `background task`. The `/health` endpoint returns `"ready": false` until loading completes. First chat requests get a friendly "warming up" message.

---

## What Could Be Next

- **Proactive engagement** — Watch scroll depth, time on page, exit intent, and trigger conversations automatically
- **Add to cart from chat** — Direct Shopify cart integration via Storefront API
- **Multi-store support** — One backend serving multiple Shopify stores
- **Analytics dashboard** — Conversation insights, conversion tracking, popular products
- **Shopify App Store** — Package as an installable Shopify app