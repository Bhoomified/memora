# Memora System Architecture 

```
+---------------------------------------------------------------------------------+
|                                  FRONTEND (UI)                                  |
|   Ingestion  |  Knowledge Graph (D3.js)  |  AI Assistant  |  Skill Gap          |
|   Timeline + Growth Story  |  Resume Scorer  |  Reset Session                   |
+---------------------------------------------------------------------------------+
        | every request carries header: X-User-Id: <client-generated UUID>
        v
+---------------------------------------------------------------------------------+
|                              FASTAPI BACKEND                                    |
|                                                                                   |
|  /api/upload -------------------------------------------------------------+     |
|     1. pdfplumber / Tesseract OCR  --> raw text        (ingestion.py)      |     |
|     2. Ollama Llama-3.2-3B classify --> title/category/skills (llm_engine) |     |
|     3. Embed + upsert into PER-USER Chroma collection  (vector_store.py)  |     |
|     4. Add node to PER-USER NetworkX graph + auto-link                    |     |
|        docs sharing skills (RELATES_TO)                (graph_engine.py) |     |
|     5. LLM causal inference on related docs                              |     |
|        --> LED_TO / BUILT_ON / APPLIED_IN edges          (llm_engine.py) |     |
|  +-------------------------------------------------------------------------+   |
|                                                                                   |
|  /api/chat        --> retrieve top-k docs (per-user) + Ollama synthesis         |
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
```

## Key design decisions

- **Isolation by construction, not by convention.** Every storage layer (files, vectors, graph) is namespaced by `user_id` at the data-access layer, not just filtered at query time — so there's no path where one user's data can leak into another's response.
- **Two-stage LLM reasoning on upload.** Classification (what is this document) and causal inference (how does it relate to what came before) are separate LLM calls, keeping each prompt focused and the JSON output reliable.
- **Graph + Vector hybrid.** ChromaDB answers *semantic* questions ("find my cloud projects"); NetworkX answers *relational* questions ("what led to my internship"). Neither alone can do both well.
- **Everything local.** No paid API calls anywhere in the pipeline — classification, causal inference, chat, gap analysis, and narrative generation all run through a self-hosted Ollama model.