# Architecture Deep Dive — Aria

## System Overview

Aria is a full-stack AI sales agent with three main layers:

### 1. Intelligence Layer (Claude AI)
- **Intent Classification (Haiku):** Every customer message is first classified into categories: `greeting`, `product_search`, `price_inquiry`, `product_detail`, `comparison`, `objection`, or `general_question`. Haiku handles this in ~200ms at 1/5th the cost of Sonnet.
- **Response Generation (Sonnet):** The classified intent, matched products, and customer memory context are sent to Sonnet, which generates a natural, conversational response.

### 2. Knowledge Layer (RAG + Memory)
- **Product Search (Qdrant):** Product descriptions are embedded using `all-MiniLM-L6-v2` (384-dim vectors). Customer queries are embedded and matched via cosine similarity. This enables natural language search like "something warm for winter" matching a puffer jacket.
- **Customer Memory (Redis):** Each session stores: interaction history, viewed products, preferences (budget, style, sizes), and cart interest. Memory persists for 30 days with automatic TTL.

### 3. Interface Layer (React + WebSocket)
- **Real-time Chat:** WebSocket connection enables instant message delivery without polling.
- **REST Fallback:** If WebSocket fails (common on some networks), the widget automatically falls back to REST API calls.
- **Suggestion Chips:** First-time visitors see quick-action buttons to reduce friction.

## Key Design Decisions

### Why Haiku + Sonnet (not just one model)?
Cost optimization. Intent classification is a simple task — Haiku handles it in 50 tokens. The expensive Sonnet call only happens once per message for the actual response. This reduces API costs by ~60%.

### Why separate `get_memory` from `bump_visit`?
Early versions incremented visit count inside `get_memory`, but since multiple operations call `get_memory` internally (save_interaction, add_viewed_product, etc.), a single user action could increment visits 5-10 times. Separating these into distinct methods fixed the bug.

### Why keyword search in production?
The free tier on Render has 512MB RAM. Loading `sentence-transformers` + PyTorch requires ~800MB. The solution: use full vector search locally (with Qdrant), but fall back to keyword matching in production. Claude's intelligence compensates for the simpler search.

### Why WebSocket + REST fallback?
WebSocket provides the best UX (instant responses, typing indicators). But some corporate networks and mobile carriers block WebSocket connections. The automatic REST fallback ensures Aria works everywhere.