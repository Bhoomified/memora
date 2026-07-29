```markdown
# Memora — Thought Process & Architecture Sheet

## Problem Statement Addressal
Traditional cloud platforms save raw files without understanding personal growth. Memora bridges this gap by creating a structured digital identity that links experiences through shared skills and chronological timelines.

## AI Engineering Decisions
1. **Self-Hosted Open Weights:** We selected `Llama-3.2-3B` running locally via Ollama. This guarantees zero API costs and total privacy for student data.
2. **Graph + Vector Hybrid:** While ChromaDB handles semantic questions ("Find cloud projects"), NetworkX builds deterministic relational paths ("How did learning Python lead to my internship?").