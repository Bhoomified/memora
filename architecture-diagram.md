# Memora System Architecture

```
+---------------------------------------------------------------------------------+
|                                  FRONTEND (UI)                                  |
|   Ingestion  |  Knowledge Graph (D3.js)  |  AI Assistant  |  Skill Gap          |
|   Timeline + Growth Story  |  Resume Scorer  |  Reset Session                   |
+---------------------------------------------------------------------------------+
        | every request carries header: X-User-Id: <client-generated UUID>
        | relative API base "/api" — same origin as the UI, no CORS to configure
        v
+---------------------------------------------------------------------------------+
|                SINGLE-ORIGIN FASTAPI BACKEND (Dockerized, on Railway)           |
|                                                                                   |
|  /                 --> serves the static frontend (StaticFiles mount at root)   |
|  /api/health       --> deployment health check for Railway                       |
|                                                                                   |
|  /api/upload -------------------------------------------------------------+     |
|     1. pdfplumber / Tesseract OCR  --> raw text        (ingestion.py)      |     |
|     2. Groq llama-3.1-8b-instant classify --> title/category/skills        |     |
|        (llm_engine.py)                                                     |     |
|     3. Embed + upsert into PER-USER Chroma collection  (vector_store.py)  |     |
|     4. Add node to PER-USER NetworkX graph + auto-link                    |     |
|        docs sharing skills (RELATES_TO)                (graph_engine.py) |     |
|     5. LLM causal inference on related docs                              |     |
|        --> LED_TO / BUILT_ON / APPLIED_IN edges          (llm_engine.py) |     |
|  +-------------------------------------------------------------------------+   |
|                                                                                   |
|  /api/chat        --> retrieve top-k docs (per-user) + Groq synthesis           |
|                        + cited sources                                          |
|  /api/career/gap-analysis --> compare graph skill nodes vs target role via LLM  |
|  /api/graph        --> full per-user graph (nodes + edges) for D3 rendering     |
|  /api/graph/story  --> LLM narrative generated from chronological doc summary   |
|  /api/timeline     --> chronological per-user document list                     |
|  /api/resume/evaluate --> resume scoring engine           (resume_eval.py)      |
|  /api/reset        --> wipes per-user uploads, graph file, and Chroma collection |
+---------------------------------------------------------------------------------+
        |
        v
+---------------------------------------------------------------------------------+
|                              PER-USER STORAGE                                   |
|   backend/uploads/{user_id}/            raw files                              |
|   data/graphs/{user_id}.json            NetworkX graph (documents+skills+edges) |
|   data/chroma_db/  (collection: memora_{user_id})   vector embeddings          |
+---------------------------------------------------------------------------------+
        |
        v
+---------------------------------------------------------------------------------+
|                        GROQ API (external, LPU inference)                       |
|   llama-3.1-8b-instant — classification, causal inference,                     |
|   chat synthesis, growth narrative, skill-gap analysis                          |
+---------------------------------------------------------------------------------+
```

## Deployment topology

```
GitHub repo --> Docker build (python:3.11-slim + tesseract-ocr + CPU-only torch)
             --> single container --> Railway
             --> https://memora-production-2406.up.railway.app
```

One container serves everything: the FastAPI app mounts the built frontend as static files at `/`, so there is exactly one URL, one port, and one deployable unit. `GROQ_API_KEY` is injected at runtime via Railway environment variables and loaded through `python-dotenv`; it is never committed to the repo (`.env` is gitignored).

## Key design decisions

- **Isolation by construction, not by convention.** Every storage layer (files, vectors, graph) is namespaced by `user_id` at the data-access layer, not just filtered at query time — so there's no path where one user's data can leak into another's response.
- **Two-stage LLM reasoning on upload.** Classification (what is this document) and causal inference (how does it relate to what came before) are separate LLM calls, keeping each prompt focused and the JSON output reliable.
- **Graph + Vector hybrid.** ChromaDB answers *semantic* questions ("find my cloud projects"); NetworkX answers *relational* questions ("what led to my internship"). Neither alone can do both well.
- **Cloud inference over self-hosting.** Memora originally ran on a self-hosted Ollama model for zero API cost and total local privacy. It now calls Groq's hosted API instead — the tradeoff is a small, deliberate one: judges and users get sub-second responses without needing a GPU, a locally running model server, or any setup at all. The system still keeps each user's *documents and graph data* fully isolated per-user; only the inference call itself leaves the container.
- **Single-origin deployment.** Serving the frontend and backend from the same FastAPI process eliminates CORS configuration, avoids hardcoded ports, and means the entire product is reachable from one URL — critical for a judge clicking a link cold, with no local setup.
- **Memory-conscious container.** CPU-only PyTorch and capped thread counts keep the Docker image's runtime memory low enough to run comfortably within free-tier hosting limits, which matters for a hackathon project meant to stay live and reachable after judging.