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

## AI engineering decisions

- **Self-hosted open weights (`Llama-3.2-3B` via Ollama):** zero API cost, total data privacy, no rate limits during live demos.
- **Graph + Vector hybrid:** ChromaDB handles fuzzy semantic recall; NetworkX handles deterministic relational structure. Each is used for what it's actually good at.
- **Bounded LLM calls per upload:** causal inference only runs against the top few most-related documents (by shared skill count), not every document pair — keeps upload latency reasonable as the graph grows.
- **Prompt separation:** classification, relationship inference, narrative generation, chat, and gap analysis are five distinct, narrowly-scoped prompts rather than one do-everything prompt — this measurably improved JSON reliability and answer quality.

## Mapping to typical judging criteria

| Criteria | How Memora addresses it |
|---|---|
| **Innovation** | Causal relationship inference and the growth-narrative generator go beyond standard RAG search |
| **Technical depth** | Two-stage LLM pipeline, graph+vector hybrid, per-user multi-tenancy, force-directed graph rendering |
| **Completeness** | Full loop from ingestion → reasoning → visualization → conversational access → actionable career guidance |
| **Usability** | Interactive graph, chat interface, one-click reset for judges to test cleanly |
| **Presentation** | Visual graph and narrative give the demo a concrete "wow" moment instead of a features list |

## Honest limitations (worth stating up front, not hiding)

- User identity is a client-generated UUID, not real authentication — sufficient for a hackathon demo, explicitly flagged as future work.
- Skill entity resolution is exact-string based; near-duplicate skills (e.g. "Python" vs "Python programming") aren't yet merged.
- Causal inference quality depends on the local 3B model — a larger model would likely improve relationship accuracy, at the cost of speed.