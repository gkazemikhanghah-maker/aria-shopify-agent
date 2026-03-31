# Aria — AI Sales Agent for Shopify

> An AI-powered shopping assistant that sits on any Shopify store, engages customers proactively, and remembers them across sessions.

🔗 **[Live Demo](https://aria-shopify-agent.vercel.app)** — Open it, click the chat bubble, and start shopping.

---

## The Problem

Most e-commerce chatbots are **reactive** — they sit in the corner waiting for customers to ask something. Real salespeople don't work that way. They approach you, remember what you liked last time, and make relevant suggestions.

**Aria bridges that gap.**

## What Makes Aria Different

| Feature | Traditional Chatbots | Aria |
|---|---|---|
| Reactive chat | ✅ | ✅ |
| Product search (RAG) | ✅ | ✅ |
| **Proactive engagement** | ❌ | ✅ |
| **Cross-session memory** | ❌ | ✅ |
| **Personalized responses** | ❌ | ✅ |

### Cross-Session Memory
Aria remembers returning customers — what they browsed, their budget, preferred sizes, and style. When they come back, Aria picks up right where they left off:

> *"Welcome back! I see you were looking at our Canvas Sneakers before — still interested in those?"*

### Intelligent Product Search
Customers describe what they want in natural language ("something warm for winter under $100"), and Aria finds the best matches from the store's catalog using semantic search.

### Powered by Claude
Aria uses Anthropic's Claude models:
- **Claude Haiku** for fast intent classification
- **Claude Sonnet** for natural, context-aware responses

---

## Architecture

```
┌─────────────┐     WebSocket / REST      ┌──────────────────┐
│  React Chat  │ ◄──────────────────────► │  FastAPI Backend  │
│   Widget     │                           │                   │
│  (Vercel)    │                           │  ┌─────────────┐  │
└─────────────┘                           │  │Product Agent │  │
                                           │  │ (Claude AI)  │  │
                                           │  └──────┬──────┘  │
                                           │         │         │
                                           │  ┌──────▼──────┐  │
                                           │  │ Vector Store │  │
                                           │  │  (Qdrant)    │  │
                                           │  └─────────────┘  │
                                           │  ┌─────────────┐  │
                                           │  │Memory Store  │  │
                                           │  │  (Redis)     │  │
                                           │  └─────────────┘  │
                                           │  (Render)         │
                                           └──────────────────┘
```

## Tech Stack

**Backend:** Python 3.11 · FastAPI · WebSocket · Anthropic Claude API
**Search:** Qdrant (vector DB) · sentence-transformers (all-MiniLM-L6-v2)
**Memory:** Redis (cross-session persistence)
**Frontend:** React · Vite · Tailwind CSS
**Deployment:** Vercel (frontend) · Render (backend)
**Data:** Shopify Admin API (with mock fallback)

## Project Structure

```
aria-shopify-agent/
├── backend/
│   ├── agents/
│   │   └── product_agent.py      # Claude-powered product agent
│   ├── api/
│   │   └── main.py               # FastAPI server (REST + WebSocket)
│   ├── tools/
│   │   ├── shopify_client.py     # Shopify Admin API client
│   │   ├── vector_store.py       # Qdrant vector search
│   │   └── memory.py             # Redis memory store
│   ├── tests/
│   │   ├── test_product_agent.py
│   │   ├── test_vector_store.py
│   │   └── test_memory.py
│   └── setup.py                  # Load catalog into Qdrant
├── widget/
│   ├── src/
│   │   ├── App.jsx               # Main widget with FAB
│   │   └── components/
│   │       ├── ChatWindow.jsx    # Chat interface
│   │       ├── MessageBubble.jsx # Message display
│   │       ├── ProductCard.jsx   # Product results
│   │       └── TypingIndicator.jsx
│   └── vite.config.js
├── requirements.txt
├── Procfile
└── railway.toml
```

## How It Works

1. **Customer opens the store** → Widget loads, WebSocket connects
2. **Customer asks a question** → Intent classified by Claude Haiku
3. **Product search** → Query embedded and matched against catalog (Qdrant)
4. **Response generated** → Claude Sonnet crafts a natural answer using product context + customer memory
5. **Memory updated** → Interaction, viewed products, and preferences saved to Redis
6. **Customer returns later** → Aria remembers them and personalizes the conversation

## Run Locally

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (for Qdrant and Redis)

### Setup

```bash
# Clone
git clone https://github.com/gkazemikhanghah-maker/aria-shopify-agent.git
cd aria-shopify-agent

# Start Qdrant and Redis
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
docker run -d --name redis -p 6379:6379 redis:alpine

# Backend
cd backend
pip install -r ../requirements.txt
pip install qdrant-client sentence-transformers
echo "ANTHROPIC_API_KEY=your-key-here" > .env
python setup.py                    # Load products into Qdrant
uvicorn api.main:app --port 8000   # Start API

# Frontend (new terminal)
cd widget
npm install
npm run dev                        # Opens at localhost:5173
```

## Build Phases

This project was built iteratively across 5 phases:

- **Phase 1:** Shopify API integration + Qdrant vector search
- **Phase 2:** Claude-powered Product Agent + FastAPI + WebSocket
- **Phase 3:** React chat widget with real-time communication
- **Phase 4:** Redis-based cross-session memory
- **Phase 5:** Production deployment (Vercel + Render)

## What I Learned

- **RAG pipelines** — Embedding product catalogs and running semantic search with Qdrant
- **Multi-model AI architecture** — Using Haiku for fast classification and Sonnet for quality responses
- **WebSocket real-time communication** — Building responsive chat with FastAPI
- **Cross-session memory design** — Separating visit tracking from memory retrieval to avoid subtle bugs
- **Production deployment** — Optimizing for free-tier constraints (lazy loading, lightweight dependencies)

## License

MIT — Built as a learning project and portfolio piece.