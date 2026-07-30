# Memora — Thought Process & Judging Criteria Mapping

## Problem Statement

Cloud storage and portfolio tools save raw files but understand nothing about the person behind them. A certificate, an internship letter, and a side project sit as disconnected blobs — even though, in reality, one usually *caused* the next. Memora's premise: a digital identity system should reason about growth, not just archive it.

## Why this build goes beyond a typical submission

Most entries in this space stop at: upload → OCR → keyword tag → list view. That's a CRUD app with an LLM sprinkled on top. Memora was deliberately pushed past that baseline in three specific ways:

**1. Real causal reasoning, not just tagging.**
Skill-sharing between documents is cheap to compute (set intersection). The harder, more valuable step is asking *why* two things are related — did A actually lead to B? Memora runs a second, focused LLM pass specifically to classify the relationship type (`LED_TO`, `BUILT_ON`, `APPLIED_IN`) between newly uploaded documents and their most-related existing ones. This is what lets the system answer "how did X help me get Y" instead of just "X and Y both mention Python."

**2. Multi-tenant correctness from day one.**
A demo that mixes every visitor's uploads into one shared graph looks fine in a 2-minute pitch and falls apart the moment a judge tests it themselves. Every storage layer — uploads, vector collection, and graph file — is namespaced per user at the data-access layer, so the system behaves like an actual product rather than a single-session prototype.

**3. Making the reasoning visible, not just present.**
A knowledge graph that only exists as JSON in an API response provides zero demo value. The interactive D3.js force-directed graph, the AI-generated growth narrative, and the conversational assistant all exist for the same reason: to surface the reasoning the backend is already doing, so it's something a judge can *see and interact with* in the moment, not something they have to take on faith.

**4. Shipping it live, not just runnable.**
A hackathon project that only works if the judge clones a repo, installs a local model server, and starts it correctly loses points before the idea is even evaluated. Memora is deployed as a single Dockerized container on Railway, reachable from one public URL, with zero setup required to test it.

## AI engineering decisions

- **Cloud inference via Groq (`llama-3.1-8b-instant`) instead of self-hosted Ollama:** the project started on a self-hosted `Llama-3.2-3B` model through Ollama for zero API cost and full local privacy. That's a fine choice for a laptop demo, but it doesn't survive contact with a judge opening a link on their own machine — there's no GPU, no model server, no guarantee Ollama is even installed. Switching to Groq's hosted API traded a small amount of self-hosting purity for something that actually works for anyone, anywhere, with sub-second response times and no cold start.
- **Graph + Vector hybrid:** ChromaDB handles fuzzy semantic recall; NetworkX handles deterministic relational structure. Each is used for what it's actually good at.
- **Bounded LLM calls per upload:** causal inference only runs against the top few most-related documents (by shared skill count), not every document pair — keeps upload latency reasonable as the graph grows, and keeps Groq API usage predictable.
- **Prompt separation:** classification, relationship inference, narrative generation, chat, and gap analysis are five distinct, narrowly-scoped prompts rather than one do-everything prompt — this measurably improved JSON reliability and answer quality.
- **Single-origin deployment:** collapsing frontend and backend into one FastAPI process removed an entire class of "it works locally but not when deployed" bugs (CORS, hardcoded `127.0.0.1` URLs, mismatched ports) and made the app a single Docker artifact.

## Mapping to typical judging criteria

| Criteria | How Memora addresses it |
|---|---|
| **Innovation** | Causal relationship inference and the growth-narrative generator go beyond standard RAG search |
| **Technical depth** | Two-stage LLM pipeline, graph+vector hybrid, per-user multi-tenancy, force-directed graph rendering, containerized cloud deployment |
| **Completeness** | Full loop from ingestion → reasoning → visualization → conversational access → actionable career guidance, shipped as a live, publicly reachable product |
| **Usability** | Interactive graph, chat interface, one-click reset for judges to test cleanly — and a live URL that needs zero setup to try |
| **Presentation** | Visual graph and narrative give the demo a concrete "wow" moment instead of a features list; judges can open the link mid-pitch and interact with it directly |

## Honest limitations (worth stating up front, not hiding)

- User identity is a client-generated UUID, not real authentication — sufficient for a hackathon demo, explicitly flagged as future work.
- Skill entity resolution is exact-string based; near-duplicate skills (e.g. "Python" vs "Python programming") aren't yet merged.
- Causal inference quality depends on the Groq-hosted 8B model — a larger model would likely improve relationship accuracy, at the cost of latency and Groq API usage.
- Switching from self-hosted Ollama to the Groq API means document *text* extracted during classification is sent to a third-party inference provider — documents and graph data themselves remain isolated per-user in the app's own storage, but this is a real tradeoff versus the original fully-local design, and worth being upfront about with anyone evaluating the privacy model.