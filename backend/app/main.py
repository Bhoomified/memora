import os
import uuid
import shutil
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.ingestion import extract_text_from_file
from backend.app.llm_engine import classify_document, infer_relationship, generate_growth_story, chat_with_context, analyze_skill_gap
from backend.app.vector_store import add_document_to_vector_db, query_vector_db, client as chroma_client
from backend.app.graph_engine import MemoryGraph, GRAPH_DIR
from backend.app.resume_eval import evaluate_resume

app = FastAPI(
    title="Memora API",
    description="AI-powered Digital Identity & Knowledge Graph System",
    version="3.0.0"
)
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Memora API",
    description="AI-powered Digital Identity & Knowledge Graph System",
    version="3.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-user knowledge graph instances cached in memory
graph_instances: dict[str, MemoryGraph] = {}

def get_graph(user_id: str) -> MemoryGraph:
    if user_id not in graph_instances:
        graph_instances[user_id] = MemoryGraph(user_id=user_id)
    return graph_instances[user_id]

def get_user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    return x_user_id.strip()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "backend", "uploads")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatQuery(BaseModel):
    query: str

class GapAnalysisQuery(BaseModel):
    target_role: str


@app.get("/api/health")
def health_check():
    return {"status": "online", "system": "Memora AI Engine v3.0 (Groq Powered)"}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    try:
        contents = await file.read()
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"

        user_upload_dir = os.path.join(UPLOAD_DIR, user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        file_path = os.path.join(user_upload_dir, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(contents)

        extracted_text = extract_text_from_file(contents, file.filename)
        if not extracted_text:
            extracted_text = f"Document title: {file.filename}"

        metadata = await classify_document(extracted_text)
        metadata["filename"] = file.filename
        metadata["file_path"] = file_path

        add_document_to_vector_db(doc_id, extracted_text, metadata, user_id)

        graph = get_graph(user_id)
        related_doc_ids = graph.add_document_node(doc_id, metadata)

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


@app.post("/api/chat")
async def chat_identity_assistant(payload: ChatQuery, user_id: str = Depends(get_user_id)):
    retrieved_docs = query_vector_db(payload.query, user_id, top_k=4)
    context_str = ""
    for idx, doc in enumerate(retrieved_docs):
        meta = doc.get("metadata", {})
        context_str += f"\n[Record {idx+1} - Title: {meta.get('title')} | Category: {meta.get('category')} | Date: {meta.get('date')}]:\n{doc.get('document')}\n"
    answer = await chat_with_context(payload.query, context_str)
    return {"answer": answer, "sources": retrieved_docs}


@app.post("/api/career/gap-analysis")
async def analyze_skill_gap_endpoint(payload: GapAnalysisQuery, user_id: str = Depends(get_user_id)):
    graph = get_graph(user_id)
    user_skills = [
        attrs.get("label") for node, attrs in graph.graph.nodes(data=True)
        if attrs.get("type") == "Skill" or node.startswith("skill:")
    ]
    return await analyze_skill_gap(payload.target_role, user_skills)


@app.get("/api/graph")
def get_knowledge_graph(user_id: str = Depends(get_user_id)):
    return get_graph(user_id).get_all_graph_data()


@app.get("/api/graph/story")
async def get_growth_story(user_id: str = Depends(get_user_id)):
    graph = get_graph(user_id)
    documents = graph.get_documents_summary()
    story = await generate_growth_story(documents)
    return {"story": story}


@app.get("/api/timeline")
def get_timeline(user_id: str = Depends(get_user_id)):
    graph_data = get_graph(user_id).get_all_graph_data()
    doc_nodes = [node for node in graph_data["nodes"] if not str(node.get("id")).startswith("skill:")]
    sorted_timeline = sorted(doc_nodes, key=lambda x: str(x.get("date", "Unknown")), reverse=True)
    return {"timeline": sorted_timeline}


@app.delete("/api/reset")
def reset_user_session(user_id: str = Depends(get_user_id)):
    global graph_instances
    try:
        user_upload_dir = os.path.join(UPLOAD_DIR, user_id)
        if os.path.exists(user_upload_dir):
            shutil.rmtree(user_upload_dir)

        graph_json_file = os.path.join(GRAPH_DIR, f"{user_id}.json")
        if os.path.exists(graph_json_file):
            os.remove(graph_json_file)

        if user_id in graph_instances:
            del graph_instances[user_id]

        collection_name = f"memora_{user_id[:50]}"
        try:
            chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass

        return {"success": True, "message": "User session data reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@app.post("/api/resume/evaluate")
async def evaluate_resume_endpoint(file: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    contents = await file.read()
    text = extract_text_from_file(contents, file.filename)
    metadata = await classify_document(text)
    score_result = evaluate_resume(text, metadata)
    return {"filename": file.filename, "evaluation": score_result}


# MUST BE THE LAST LINE: Serve frontend static files from root URL
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")