# 🚛 Hemut - Real-Time Logistics Collaboration Platform

A **Slack-style collaboration platform** built for logistics teams, featuring real-time messaging, channels, direct messages, shipment tracking, and AI-powered channel summarization.

![Tech Stack](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-010101?style=flat&logo=socket.io&logoColor=white)

---

## 📋 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Features](#-features)
- [AI Feature: Channel Summarization](#-ai-feature-channel-summarization)
- [Tech Stack](#-tech-stack)
- [Setup & Running](#-setup--running)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Design Decisions & Tradeoffs](#-design-decisions--tradeoffs)
- [Production Considerations](#-production-considerations)

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Next.js Frontend (:3000)            │
│    Auth (XHR) │ Channels │ Messages │ Shipments  │
│         └──── WebSocket (singleton) ─────┘       │
└──────────────────────┬───────────────────────────┘
          REST (XHR)   │   WebSocket
                       ▼
┌──────────────────────────────────────────────────┐
│            FastAPI Backend (:8000)                │
│  Auth │ Channels │ Messages │ DMs │ AI │ Presence │
│              └── Redis Pub/Sub ──┘               │
└────────┬──────────────────────────────┬──────────┘
         ▼                              ▼
   ┌──────────┐                  ┌──────────┐
   │PostgreSQL│                  │  Redis   │
   │  (data)  │                  │ (pub/sub │
   │          │                  │ + cache) │
   └──────────┘                  └──────────┘
```

### Why PostgreSQL + Redis?

- **PostgreSQL** provides durable storage for users, channels, messages, and shipments with ACID guarantees, indexed queries, and complex joins.
- **Redis** solves what Postgres can't in real-time scenarios:
  - **Pub/Sub fan-out**: When WebSocket connections are spread across multiple workers, a message posted on Worker A must reach users on Worker B. Redis pub/sub broadcasts events so all workers can fan them out.
  - **Presence**: TTL-based keys (`presence:{user_id}` with 60s expiry) provide efficient online/away/offline tracking.
  - **Caching**: AI summaries are cached for 5 minutes, unread counts are tracked in Redis for O(1) reads.

---

## ✨ Features

### Core Chat
- ✅ **User Registration & Login** — DB-backed auth with JWT tokens
- ✅ **Channels** — Create, join, leave channels (e.g., #route-east, #warehouse-mumbai)
- ✅ **Direct Messages** — 1:1 private conversations
- ✅ **Real-time Messaging** — WebSocket-powered with Redis pub/sub
- ✅ **Message History** — Cursor-based pagination
- ✅ **Unread Indicators** — Redis-backed unread counters per channel

### Logistics Context
- ✅ **`/shipment <id>` Slash Command** — Lookup shipment details inline
- ✅ **Shipment Preview Cards** — Rich cards showing origin, destination, status, carrier, ETA
- ✅ **Domain-aware Channels** — Pre-seeded with #route-east, #warehouse-mumbai, #dispatch, etc.
- ✅ **Mock Shipment Data** — Realistic Indian logistics data (6 shipments)

### Presence System
- ✅ **Online/Away/Offline** — Green/Yellow/Gray indicators
- ✅ **Heartbeat-based** — 30s client heartbeat, 60s Redis TTL
- ✅ **Real-time Updates** — Broadcast via Redis pub/sub

### AI Feature
- ✅ **Channel Summarization** — "Catch me up" on any channel
- ✅ **Streaming Support** — Progressive rendering of AI responses
- ✅ **Redis Caching** — 5-minute cache to avoid redundant API calls

### Technical
- ✅ **XMLHttpRequest** — All form validation uses raw XHR (not fetch/axios)
- ✅ **Auto-reconnect** — Exponential backoff WebSocket reconnection
- ✅ **Typing Indicators** — Real-time "user is typing..." display

---

## 🤖 AI Feature: Channel Summarization

### Why This Feature?

Logistics teams operate **24/7 across time zones**. Dispatchers coming on shift waste significant time scrolling through hundreds of overnight messages. Channel summarization solves a **real, daily pain point** by providing a concise "catch me up" digest.

**Real user pain it addresses:**
- Shift handoffs: Night dispatcher → Morning dispatcher
- Route managers catching up on #route-east after a day off
- Warehouse supervisors scanning #warehouse-mumbai for urgent issues

### How It Works

1. User clicks **"🤖 Summarize"** button or types **`/summarize`** (optionally `/summarize 12h`)
2. Backend fetches last N hours of messages from PostgreSQL (capped at 200)
3. Messages are formatted with timestamps and usernames
4. Sent to **Google Gemini** (`gemini-2.0-flash`) with a **logistics-aware system prompt** focusing on:
   - Shipment delays and status changes
   - Route diversions
   - Action items and escalations
   - Tracking IDs and PO numbers
5. Response is cached in **Redis for 5 minutes**
6. Displayed in a styled AI panel with dismiss option

### What Would Change in Production

| Aspect | Current | Production |
|--------|---------|------------|
| **Model** | Gemini 2.0 Flash | Gemini Pro or Claude for better accuracy |
| **Caching** | 5-min Redis TTL | Intelligent invalidation on new messages |
| **Token limits** | 200 message cap | Chunked summarization with map-reduce |
| **Streaming** | Via REST response | Full WebSocket streaming for progressive UX |
| **Grounding** | Raw message context | RAG with indexed chat history + BOL docs |
| **Safety** | Basic error handling | Hallucination detection, source citation, content filtering |
| **Cost** | Per-request | Batch summarization during low-traffic hours |

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14 (App Router) | React SPA with routing |
| Backend | FastAPI (Python) | Async REST API + WebSocket |
| Database | PostgreSQL 15 | Durable data storage |
| Cache/PubSub | Redis 7 | Real-time fan-out + caching |
| AI | Google Gemini | Channel summarization |
| Auth | JWT + bcrypt | Stateless authentication |
| HTTP | XMLHttpRequest | Form validation (project requirement) |
| Infrastructure | Docker Compose | Local dev environment |

---

## 🚀 Setup & Running

### Prerequisites

- **Docker Desktop** — for PostgreSQL and Redis
- **Python 3.11+** — for the backend
- **Node.js 18+** — for the frontend
- **Google Gemini API Key** — for AI summarization ([Get one here](https://aistudio.google.com/apikey))

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd Hemut

# Copy and edit environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Start Infrastructure (PostgreSQL + Redis)

```bash
docker-compose up -d
```

Verify they're running:
```bash
docker ps
# Should show hemut-postgres and hemut-redis
```

### 3. Start Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server (auto-creates tables & seeds data)
uvicorn app.main:app --reload --port 8000
```

The backend will:
- Create all database tables automatically
- Seed 7 default channels (#general, #route-east, #warehouse-mumbai, etc.)
- Seed 6 mock shipments (SHIP-1001 through SHIP-1042)

### 4. Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 5. Use the App

1. Open **http://localhost:3000** in your browser
2. **Register** a new account
3. **Join channels** and start messaging
4. Try **`/shipment SHIP-1042`** to see a shipment card
5. Try **`/summarize`** or click the **🤖 Summarize** button for AI summary
6. Open a **second browser tab**, register another user, and test real-time messaging

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_auth.py -v        # Auth: register, login, validation
pytest tests/test_channels.py -v    # Channels: CRUD, join/leave
pytest tests/test_messages.py -v    # Messages: post, pagination, ordering
pytest tests/test_ai.py -v          # AI: mocked Gemini, no API calls
```

**Test highlights:**
- Uses **in-memory SQLite** for test isolation (no Postgres needed)
- **Mock Redis** for all pub/sub and caching operations
- **Mocked Gemini API** in `test_ai.py` — deterministic, no API calls, CI-friendly
- Tests cover happy paths and error cases (duplicates, unauthorized access, validation)

---

## 📁 Project Structure

```
Hemut/
├── docker-compose.yml          # PostgreSQL + Redis
├── .env                        # Environment variables
├── README.md
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI app, lifespan, CORS
│   │   ├── config.py           # Pydantic Settings
│   │   ├── database.py         # Async SQLAlchemy
│   │   ├── redis_client.py     # Redis connection
│   │   ├── dependencies.py     # Auth dependency (JWT)
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response
│   │   ├── routers/            # API route handlers
│   │   ├── services/           # Business logic layer
│   │   └── websocket/          # WS manager + handlers
│   └── tests/                  # pytest test suite
│
└── frontend/
    └── src/
        ├── app/
        │   ├── layout.js       # Root layout + AuthProvider
        │   ├── login/          # Login page (XHR)
        │   ├── register/       # Register page (XHR)
        │   └── chat/           # Chat layout + channel view
        ├── context/            # Auth + Chat React contexts
        └── lib/
            ├── xhr.js          # Raw XMLHttpRequest wrapper
            ├── auth.js         # Token storage
            └── constants.js    # API URLs
```

---

## 📡 API Documentation

Once the backend is running, visit **http://localhost:8000/docs** for interactive Swagger documentation.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/channels/` | List joined channels |
| POST | `/api/channels/` | Create channel |
| GET | `/api/channels/{id}/messages` | Paginated history |
| POST | `/api/channels/{id}/messages` | Send message |
| POST | `/api/dm/{user_id}` | Start/get DM |
| GET | `/api/shipments/{id}` | Lookup shipment |
| POST | `/api/ai/summarize` | AI channel summary |
| WS | `/ws?token=<jwt>` | Real-time connection |

---

## 🧠 Design Decisions & Tradeoffs

### 1. Single WebSocket Connection per Client
**Decision:** One persistent WS connection multiplexed across all channels.
**Why:** Reduces connection overhead. Channel subscriptions are managed server-side via `subscribe_channel` messages.
**Tradeoff:** Requires careful message routing; all events flow through one pipe.

### 2. Redis Pub/Sub for Fan-out (Not DB Polling)
**Decision:** Messages are published to Redis channels, not polled from Postgres.
**Why:** Sub-millisecond delivery. Scales horizontally when multiple FastAPI workers run behind a load balancer.
**Tradeoff:** Messages must still be persisted to Postgres for durability; Redis is ephemeral.

### 3. XHR for Forms, Fetch/WS for Everything Else
**Decision:** Auth forms use raw XMLHttpRequest as required. All other HTTP calls use a thin XHR wrapper (not fetch/axios).
**Why:** Project requirement. The XHR wrapper handles progress, abort, timeout, and error lifecycle events directly.

### 4. Cursor-based Pagination (not offset)
**Decision:** Messages are paginated using `before=<timestamp>` cursor, not `page=N`.
**Why:** Offset pagination breaks when new messages arrive. Cursor-based pagination is stable under concurrent writes.

### 5. UUID Primary Keys
**Decision:** All tables use UUID v4 primary keys.
**Why:** No sequential ID leakage, safe for distributed systems, no auto-increment conflicts.

### 6. DM Channels as Regular Channels with `is_dm=true`
**Decision:** DMs reuse the same channel/membership/message tables.
**Why:** Unified message model. No separate DM table or query path needed.

---

## 🏭 Production Considerations

1. **Horizontal Scaling:** FastAPI behind Gunicorn/Uvicorn workers with sticky sessions for WebSocket. Redis pub/sub ensures cross-worker message delivery.

2. **Message Delivery Guarantees:** On reconnect, clients request `messages?before=<last_seen_timestamp>` to catch up on missed messages.

3. **Database Migrations:** Use Alembic for versioned schema migrations instead of auto-create.

4. **Security:**
   - JWT with short-lived access tokens + refresh tokens
   - XSS prevention: escape all user content on render
   - CSRF: token-based protection for state-changing requests
   - Message spoofing prevention: sender derived from JWT, never from client

5. **Rate Limiting:** Redis-backed rate limiters per endpoint per user.

6. **Monitoring:** Structured logging, Prometheus metrics, distributed tracing.

---

## 📝 Commit History

This project was built incrementally with meaningful commits. Key milestones:
1. Infrastructure setup (Docker, env config)
2. Backend models and database
3. Auth system (JWT + bcrypt)
4. Channel and message APIs
5. WebSocket real-time system
6. Frontend auth pages
7. Chat UI with real-time messaging
8. Shipment slash command
9. AI summarization
10. Tests and documentation

---

Built with ❤️ for the Hemut trial project.
