import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.ingestion import extract_text_from_file
from backend.app.llm_engine import classify_document, infer_relationship, generate_growth_story
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
# Per-user knowledge graph instances (cached in memory)
graph_instances: dict[str, MemoryGraph] = {}

def get_graph(user_id: str) -> MemoryGraph:
    if user_id not in graph_instances:
        graph_instances[user_id] = MemoryGraph(user_id=user_id)
    return graph_instances[user_id]

def get_user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    return x_user_id.strip()

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
async def upload_document(file: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    """
    Module 1 & 2: Ingests file, extracts text, categorizes via local LLM, 
    stores in ChromaDB, and updates the Knowledge Graph. Scoped per user.
    """
    try:
        contents = await file.read()
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"

        # Save raw file inside a per-user folder
        user_upload_dir = os.path.join(UPLOAD_DIR, user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        file_path = os.path.join(user_upload_dir, f"{doc_id}_{file.filename}")
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

        # Step 3: Embed in Vector Store (ChromaDB) — scoped to this user
        add_document_to_vector_db(doc_id, extracted_text, metadata, user_id)

        # Step 4: Add to this user's Knowledge Graph (NetworkX)
        # Step 4: Add to this user's Knowledge Graph + auto-link docs sharing skills
        graph = get_graph(user_id)
        related_doc_ids = graph.add_document_node(doc_id, metadata)

        # Step 5: Ask local LLM to infer causal relationships (capped to top 4 related docs)
        for other_id in related_doc_ids[:4]:
            other_doc = graph.get_document(other_id)
            if other_doc:
                relation = await infer_relationship(metadata, other_doc)
                if relation != "NONE":
                    graph.add_causal_edge(other_id, doc_id, relation)

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": file.filename,
            "metadata": metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.post("/api/search")
async def search_identity(payload: ChatQuery, user_id: str = Depends(get_user_id)):
    """
    Module 5: Natural language semantic retrieval across this user's digital footprint.
    """
    results = query_vector_db(payload.query, user_id, top_k=5)
    return {
        "query": payload.query,
        "results": results
    }


@app.get("/api/timeline")
def get_timeline(user_id: str = Depends(get_user_id)):
    """
    Module 4: Digital Journey Timeline sorted chronologically, per user.
    """
    graph_data = get_graph(user_id).get_all_graph_data()


@app.get("/api/graph")
def get_knowledge_graph(user_id: str = Depends(get_user_id)):
    """
    Module 3: Graph endpoints returning all nodes & dynamic edge connections, per user.
    """
    return get_graph(user_id).get_all_graph_data()


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
@app.get("/api/graph/story")
async def get_growth_story(user_id: str = Depends(get_user_id)):
    """
    Generates an LLM narrative describing how the user's documents connect and build on each other.
    """
    graph = get_graph(user_id)
    documents = graph.get_documents_summary()
    story = await generate_growth_story(documents)
    return {"story": story}