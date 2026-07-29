import os
import chromadb
from chromadb.utils import embedding_functions

# Define path to local persistent vector storage
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_DATA_DIR = os.path.join(BASE_DIR, "data", "chroma_db")

# Use local lightweight embedding model (all-MiniLM-L6-v2 runs locally on CPU)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Initialize ChromaDB persistent client
client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)
collection = client.get_or_create_collection(
    name="memora_documents",
    embedding_function=embedding_fn
)

def add_document_to_vector_db(doc_id: str, text: str, metadata: dict):
    """
    Embeds document text and stores vector + metadata in ChromaDB.
    """
    # ChromaDB metadata requires primitive data types (str, int, float, bool)
    cleaned_metadata = {
        "title": str(metadata.get("title", "Untitled Document")),
        "category": str(metadata.get("category", "Academics")),
        "date": str(metadata.get("date", "Unknown")),
        "skills": ", ".join(metadata.get("extracted_skills", [])),
        "summary": str(metadata.get("summary", ""))
    }

    collection.upsert(
        documents=[text[:4000]],  # Store chunk for semantic matching
        metadatas=[cleaned_metadata],
        ids=[doc_id]
    )

def query_vector_db(query: str, top_k: int = 3) -> list:
    """
    Performs semantic search across all indexed user files.
    """
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )

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