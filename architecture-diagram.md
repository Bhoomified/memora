# Memora System Architecture
+-----------------------------------------------------------------------+
|                            FRONTEND (UI)                              |
|   Ingestion Dropzone | Vector Search Bar | Timeline | Resume Scorer   |
+-----------------------------------------------------------------------+
| HTTP API Call
v
+-----------------------------------------------------------------------+
|                         FASTAPI BACKEND                               |
|   - ingestion.py  (pdfplumber + OCR)                                  |
|   - llm_engine.py (Ollama / Llama-3.2-3B local inference)            |
|   - vector_store.py (SentenceTransformers + ChromaDB)                 |
|   - graph_engine.py (NetworkX Knowledge Graph)                        |
|   - resume_eval.py (Pattern analysis engine)                          |
+-----------------------------------------------------------------------+