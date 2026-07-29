import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.ingestion import extract_text_from_file
from backend.app.llm_engine import classify_document
from backend.app.vector_store import add_document_to_vector_db, query_vector_db
from backend.app.graph_engine import MemoryGraph
from backend.app.resume_eval import evaluate_resume

app = FastAPI(
    title="Memora API",
    description="AI-powered Digital Identity & Knowledge Graph System for Memoryverse",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize knowledge graph instance
graph_db = MemoryGraph()

# Directory configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "backend", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatQuery(BaseModel):
    query: str


@app.get("/")
def read_root():
    return {"status": "online", "system": "Memora Digital Identity Engine"}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Module 1 & 2: Ingests file, extracts text, categorizes via local LLM, 
    stores in ChromaDB, and updates the Knowledge Graph.
    """
    try:
        contents = await file.read()
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        # Save raw file untouched
        file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(contents)

        # Step 1: Extract Text
        extracted_text = extract_text_from_file(contents, file.filename)
        if not extracted_text:
            extracted_text = f"Document title: {file.filename}"

        # Step 2: Categorize & Extract Metadata via local LLM
        metadata = await classify_document(extracted_text)
        metadata["filename"] = file.filename
        metadata["file_path"] = file_path

        # Step 3: Embed in Vector Store (ChromaDB)
        add_document_to_vector_db(doc_id, extracted_text, metadata)

        # Step 4: Add to Knowledge Graph (NetworkX)
        graph_db.add_document_node(doc_id, metadata)

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": file.filename,
            "metadata": metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@app.post("/api/search")
async def search_identity(payload: ChatQuery):
    """
    Module 5: Natural language semantic retrieval across digital footprint.
    """
    results = query_vector_db(payload.query, top_k=5)
    return {
        "query": payload.query,
        "results": results
    }


@app.get("/api/timeline")
def get_timeline():
    """
    Module 4: Digital Journey Timeline sorted chronologically.
    """
    graph_data = graph_db.get_all_graph_data()
    doc_nodes = [node for node in graph_data["nodes"] if node.get("type") != "Skill"]
    
    # Sort by date
    sorted_timeline = sorted(doc_nodes, key=lambda x: str(x.get("date", "Unknown")), reverse=True)
    return {"timeline": sorted_timeline}


@app.get("/api/graph")
def get_knowledge_graph():
    """
    Module 3: Graph endpoints returning all nodes & dynamic edge connections.
    """
    return graph_db.get_all_graph_data()


@app.post("/api/resume/evaluate")
async def evaluate_resume_endpoint(file: UploadFile = File(...)):
    """
    Resume Evaluator: Parses uploaded resume and returns scoring & suggestions.
    """
    contents = await file.read()
    text = extract_text_from_file(contents, file.filename)
    metadata = await classify_document(text)
    score_result = evaluate_resume(text, metadata)
    
    return {
        "filename": file.filename,
        "evaluation": score_result
    }