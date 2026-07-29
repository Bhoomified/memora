import os
import re
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_DATA_DIR = os.path.join(BASE_DIR, "data", "chroma_db")

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)

_collection_cache = {}

def _safe_collection_name(user_id: str) -> str:
    """Chroma collection names must be 3-63 chars, alnum/underscore/hyphen only."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", user_id)[:50]
    return f"memora_{clean}" if len(clean) >= 3 else "memora_default_user"

def get_user_collection(user_id: str):
    name = _safe_collection_name(user_id)
    if name not in _collection_cache:
        _collection_cache[name] = client.get_or_create_collection(
            name=name,
            embedding_function=embedding_fn
        )
    return _collection_cache[name]

def add_document_to_vector_db(doc_id: str, text: str, metadata: dict, user_id: str):
    collection = get_user_collection(user_id)
    cleaned_metadata = {
        "title": str(metadata.get("title", "Untitled Document")),
        "category": str(metadata.get("category", "Academics")),
        "date": str(metadata.get("date", "Unknown")),
        "skills": ", ".join(metadata.get("extracted_skills", [])),
        "summary": str(metadata.get("summary", ""))
    }
    collection.upsert(
        documents=[text[:4000]],
        metadatas=[cleaned_metadata],
        ids=[doc_id]
    )

def query_vector_db(query: str, user_id: str, top_k: int = 3) -> list:
    collection = get_user_collection(user_id)
    results = collection.query(query_texts=[query], n_results=top_k)

    formatted_results = []
    if results and results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else 0
            })
    return formatted_results