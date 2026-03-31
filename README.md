<div align="center">

# ✦ Aria

**The AI Sales Agent That Remembers Your Customers**

Most Shopify chatbots answer questions. Aria closes sales.

[Live Demo](https://aria-shopify-agent.vercel.app) · [How It Works](#how-it-works) · [Architecture](ARCHITECTURE.md)

---

</div>

## The Problem

**68% of online shopping carts are abandoned.** Shoppers leave because they can't find answers fast enough, don't get relevant recommendations, or simply lose interest with no one to guide them.

Traditional chatbots don't help. They sit in the corner, wait for a question, give a scripted response, and forget the customer ever existed. Come back tomorrow — *"Hi! How can I help you?"* — like you never spoke.

**Real salespeople don't work that way.** They remember what you liked. They suggest things based on what they know about you. They approach you at the right time.

That's what Aria does.

<br>

## What Aria Does Differently

### 🧠 Cross-Session Memory
Every other chatbot starts from zero. Aria picks up where you left off.

Browse winter jackets on Monday, come back on Thursday — Aria already knows:

> *"Still thinking about that puffer jacket? It's still in stock — and it pairs great with those chinos you were looking at."*

Aria tracks viewed products, budget preferences, sizes, style choices, and conversation history — all persisted across sessions.

### 🔍 Natural Language Product Search
Customers don't search in keywords. They search in intent:

- *"Something warm for winter under $100"*
- *"I need a gift for my friend"*
- *"Casual shoes that go with everything"*

Aria uses semantic search (RAG) to understand what customers *mean*, not just what they type. The product catalog is embedded into a vector database — every query is matched by meaning, not string matching.

### 💬 AI That Sells, Not Just Responds
Powered by Claude, Aria generates responses that feel like talking to a knowledgeable store associate — not reading a product spec sheet. It compares products, handles objections, suggests complementary items, and includes prices naturally.

<br>

## How It Works

```
Customer: "Do you have warm jackets?"

  ① Intent classified             → product_search         (Claude Haiku, ~200ms)
  ② Catalog searched              → Puffer Jacket, Sweater  (Qdrant vector search)
  ③ Customer memory loaded        → Returning, likes casual  (Redis)
  ④ Response generated            → Personalized answer      (Claude Sonnet)
  ⑤ Memory updated                → Interaction saved        (Redis)
```

Five steps. Sub-second. Every message.

<br>

## Tech Stack

| Layer | Technology | Why |
|:--|:--|:--|
| **AI** | Claude Sonnet + Haiku | Sonnet for quality responses, Haiku for fast classification |
| **Search** | Qdrant + sentence-transformers | Semantic product matching that understands intent |
| **Memory** | Redis | 30-day persistent customer memory across sessions |
| **Backend** | Python · FastAPI · WebSocket | Real-time chat with REST fallback |
| **Frontend** | React · Vite · Tailwind CSS | Beautiful, responsive chat widget |
| **Data** | Shopify Admin API | Direct catalog access with mock fallback |
| **Deploy** | Vercel + Render | Frontend CDN + backend hosting |

<br>

## What Most Chatbots Don't Do

✅ Product Q&A and natural language search — standard stuff.

What's not standard: **cross-session memory**, **personalization based on browsing history**, and **responses that actually sound human**. Most solutions on the market reset every session. Aria doesn't.

<br>

## Project Structure

```
aria-shopify-agent/
│
├── backend/
│   ├── agents/
│   │   └── product_agent.py          → AI agent (Claude + RAG + Memory)
│   ├── api/
│   │   └── main.py                   → FastAPI server + WebSocket
│   ├── tools/
│   │   ├── shopify_client.py         → Shopify Admin API + mock catalog
│   │   ├── vector_store.py           → Qdrant semantic search
│   │   └── memory.py                 → Redis cross-session memory
│   ├── tests/                        → Full test suite
│   └── setup.py                      → Catalog → Qdrant loader
│
├── widget/
│   └── src/
│       ├── App.jsx                   → Chat widget with FAB trigger
│       └── components/
│           ├── ChatWindow.jsx        → Real-time chat interface
│           ├── MessageBubble.jsx     → Message rendering
│           ├── ProductCard.jsx       → Product result cards
│           └── TypingIndicator.jsx   → Typing animation
│
├── requirements.txt
├── ARCHITECTURE.md
└── README.md
```

<br>

## Run Locally

**Prerequisites:** Python 3.11+ · Node.js 20+ · Docker

```bash
# Clone
git clone https://github.com/gkazemikhanghah-maker/aria-shopify-agent.git
cd aria-shopify-agent

# Infrastructure
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
docker run -d --name redis -p 6379:6379 redis:alpine

# Backend
cd backend
pip install -r ../requirements.txt
pip install qdrant-client sentence-transformers
echo "ANTHROPIC_API_KEY=your-key" > .env
python setup.py
uvicorn api.main:app --port 8000

# Frontend (new terminal)
cd widget && npm install && npm run dev
```

Open **http://localhost:5173** → click the chat bubble → start shopping.

<br>

## The Build Journey

This wasn't a tutorial project. It was built from an idea to a live product, phase by phase:

| Phase | What Got Built | One-liner |
|:--:|:--|:--|
| **1** | Shopify API + Qdrant vector search | Products embedded into vectors — first time the system understood *meaning*, not keywords. |
| **2** | Claude AI agent + FastAPI + WebSocket | The brain. Intent classification + natural responses + real-time chat. |
| **3** | React chat widget | Dark-themed UI with product cards, typing indicators, and suggestion chips. |
| **4** | Redis cross-session memory | The differentiator — and where the hardest bug lived (visit counts inflating 10x). |
| **5** | Production deploy (Vercel + Render) | 512MB server, 800MB model. Constraints forced better architecture. |

<br>

## What I Learned Building This

**Docker isn't scary — it's liberating.** Running Qdrant and Redis locally with two commands changed how I think about infrastructure.

**RAG is only as good as your embeddings.** Bad chunking = bad search results, no matter how smart your LLM is.

**Memory bugs are silent.** Combining "read" and "write" in one function inflated visit counts by 10x. Hours to find. One line to fix.

**Free-tier constraints breed creativity.** When your embedding model needs 800MB RAM but your server has 512MB, you learn to architect differently — and the result is often better.

**Shipping beats perfecting.** Five phases. Idea to production. Every decision documented. Every bug a lesson.

<br>

---

<div align="center">

**[→ Try the live demo](https://aria-shopify-agent.vercel.app)** · **[→ Read the architecture](ARCHITECTURE.md)**

Built end-to-end with AI tools. From zero to production.

</div>