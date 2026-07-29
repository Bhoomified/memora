# Memora — AI-Powered Digital Identity & Knowledge Graph System

Memora is a local, privacy-first AI platform built for the **Memoryverse Hackathon**. It converts scattered student documents (certificates, resumes, project reports, internship letters) into an interconnected knowledge graph and searchable semantic repository.

## Features
- **AI Data Ingestion & OCR:** Extracts text from raw PDFs and images.
- **Local LLM Categorization:** Employs self-hosted `Llama-3.2-3B` via Ollama for zero-cost JSON metadata extraction.
- **RAG Semantic Search:** Embeds document contents using `sentence-transformers (all-MiniLM-L6-v2)` and ChromaDB.
- **NetworkX Relationship Engine:** Automatically maps `Certification → Skill → Project → Internship`.
- **Digital Growth Timeline:** Chronologically tracks academic and professional milestones.
- **Resume Evaluator:** Scoring engine checking formatting completeness and quantified metrics.

## Quick Start
1. Run backend server:
   ```bash
   uvicorn backend.app.main:app --reload