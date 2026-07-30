# 🧠 Memora — AI-Powered Digital Identity & Knowledge Graph Engine

Memora turns scattered personal records — certificates, resumes, internship letters, project reports — into a **living, reasoning knowledge graph** of a person's growth. It doesn't just store your documents. It understands how they connect, why one led to another, and where you should go next.

Built for the **Memoryverse Hackathon** — live, cloud-deployed, and running on Groq's LPU inference engine for sub-second AI responses.

🔗 **Live demo:** [https://memora-production-2406.up.railway.app](https://memora-production-2406.up.railway.app)

---

## ✨ What makes Memora different

Most "document management" hackathon projects stop at upload → categorize → search. Memora goes further:

| Capability | What it actually does |
|---|---|
| 🔐 **Per-user isolated identity spaces** | Every user gets their own vector collection, knowledge graph, and file storage — no data ever crosses between users |
| 🕸️ **Causal Relationship Engine** | Doesn't just tag skills — an LLM reasons over related documents to infer real `LED_TO`, `BUILT_ON`, and `APPLIED_IN` relationships between them |
| 📖 **AI-Generated Growth Narrative** | Reads your entire timeline and writes a personalized story of how your journey connects, in plain human language |
| 🕹️ **Interactive Knowledge Graph** | A live, force-directed D3.js graph you can drag, zoom, and explore — not a static list |
| 💬 **Conversational Identity Assistant** | A RAG-powered chat agent that answers questions about *your* history with cited sources, instead of a plain keyword search box |
| 🧭 **Career Skill Gap Analyzer** | Compares your extracted skill graph against any target role and tells you exactly what's missing and what to build next |
| 📄 **Intelligent Resume Evaluator** | LLM-driven scoring on completeness, quantified impact, and keyword strength |
| ♻️ **One-click Session Reset** | Lets anyone (including judges testing live) wipe their data and start clean instantly |
| ⚡ **Sub-second AI responses** | Powered by Groq's `llama-3.1-8b-instant` — no local GPU, no cold-start delay, works the same for every judge who opens the link |

---

## 🏗️ Architecture

```
FRONTEND (Tailwind + Vanilla JS + D3.js)
   Ingestion · Knowledge Graph · AI Assistant · Skill Gap · Timeline · Resume Analyzer
              │  HTTP (X-User-Id header scopes every request)
              ▼
SINGLE-ORIGIN FASTAPI SERVER (Dockerized, deployed on Railway)
   ingestion.py     → pdfplumber + Tesseract OCR (PDF/image → raw text)
   llm_engine.py    → Groq API (llama-3.1-8b-instant) — classification, causal inference, narrative + chat generation
   vector_store.py  → SentenceTransformers + ChromaDB, ONE collection PER USER
   graph_engine.py  → NetworkX knowledge graph, ONE graph PER USER (documents + skills + causal edges)
   resume_eval.py   → Resume scoring engine
              │
              ▼
   data/graphs/{user_id}.json   ·   data/chroma_db/   ·   backend/uploads/{user_id}/
```

Every user is identified by a UUID generated client-side and persisted in `localStorage`, sent as an `X-User-Id` header on every request. This is what turns Memora from a shared demo into something that behaves like a real multi-tenant product.

The frontend and backend are served from **one single origin** — FastAPI mounts the static UI directly at `/`, and `frontend/app.js` talks to the API via a relative `/api` base path. There's nothing to configure, no CORS juggling, no separate deployment for UI vs API: the Railway URL above *is* the whole app.

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Deployment health check |
| `POST` | `/api/upload` | Ingest a document → extract, classify, embed, graph, auto-link |
| `POST` | `/api/search` | Semantic vector search over the user's documents |
| `POST` | `/api/chat` | Conversational RAG assistant with cited sources |
| `GET` | `/api/timeline` | Chronological growth timeline |
| `GET` | `/api/graph` | Full graph (nodes + edges) for visualization |
| `GET` | `/api/graph/story` | AI-generated growth narrative |
| `POST` | `/api/career/gap-analysis` | Skill gap analysis against a target role |
| `POST` | `/api/resume/evaluate` | Resume scoring and feedback |
| `DELETE` | `/api/reset` | Wipe the current user's session data |

All endpoints except `/` and `/api/health` require an `X-User-Id` header.

---

## 🚀 Quick Start

### Try it live (no setup)
Just open **[memora-production-2406.up.railway.app](https://memora-production-2406.up.railway.app)** — everything runs in the browser and on Railway. Nothing to install.

### Run it locally

**1. Get a free Groq API key**
Create one at [console.groq.com](https://console.groq.com) — Groq's free tier is more than enough for local development and demos.

**2. Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# create backend/.env with:
# GROQ_API_KEY=your_key_here

uvicorn backend.app.main:app --reload
```

**3. Frontend**

Nothing to run separately — visit `http://127.0.0.1:8000` and FastAPI serves the full UI alongside the API.

---

## 🧪 Try It

Upload a chain of related documents (e.g. a programming certification → an internship that used that skill → a project that built on it) and watch:
- The **Knowledge Graph** tab draw causal edges between them automatically
- The **Timeline** tab generate a growth narrative connecting the dots
- The **AI Assistant** answer "how did my certification help my internship?" with cited sources
- The **Skill Gap** tab tell you what's missing for a role like *"AI Research Engineer"*

---

## 🛠️ Tech Stack

`FastAPI` · `Groq (Llama-3.1-8B-Instant)` · `ChromaDB` · `SentenceTransformers` · `NetworkX` · `pdfplumber` · `Tesseract OCR` · `D3.js` · `Tailwind CSS` · `Docker` · `Railway`

---

## ☁️ Deployment

Memora ships as a single Docker container:
- **Base image:** `python:3.11-slim`
- **CPU-only PyTorch** to keep the container lean on memory-constrained free tiers
- **Tesseract OCR** installed at the system level for scanned PDF/image support
- **Single-origin serving** — one container, one port, one URL for both UI and API
- **Live on Railway:** [memora-production-2406.up.railway.app](https://memora-production-2406.up.railway.app)

---

## 📌 Roadmap / Future Work

- Shareable public "digital identity card" export
- Entity resolution / skill deduplication via embedding similarity
- Persistent auth (replace client-generated UUID with real accounts)
- Multi-graph comparison (e.g. benchmark your growth against peers, anonymized)