import os
import uuid
import shutil
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from pydantic import BaseModel

from backend.app.ingestion import extract_text_from_file
from backend.app.llm_engine import classify_document, infer_relationship, generate_growth_story, OLLAMA_URL, MODEL_NAME
from backend.app.vector_store import add_document_to_vector_db, query_vector_db, client as chroma_client
from backend.app.graph_engine import MemoryGraph, GRAPH_DIR
from backend.app.resume_eval import evaluate_resume

app = FastAPI(
    title="Memora API",
    description="AI-powered Digital Identity & Knowledge Graph System",
    version="2.5.0"
)

# Per-user knowledge graph instances
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
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatQuery(BaseModel):
    query: str

class GapAnalysisQuery(BaseModel):
    target_role: str


@app.get("/")
def read_root():
    return {"status": "online", "system": "Memora AI Digital Identity Engine v2.5"}


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
    """Conversational RAG AI identity assistant with source citations."""
    retrieved_docs = query_vector_db(payload.query, user_id, top_k=4)
    
    context_str = ""
    for idx, doc in enumerate(retrieved_docs):
        meta = doc.get("metadata", {})
        context_str += f"\n[Record {idx+1} - Title: {meta.get('title')} | Category: {meta.get('category')} | Date: {meta.get('date')}]:\n{doc.get('document')}\n"

    prompt = f"""
You are Memora, an intelligent AI Digital Identity Assistant representing the user's academic and professional journey.
Answer the user's question directly based ONLY on their uploaded digital records below.

User Records:
{context_str if context_str else "No prior records uploaded matching this query."}

User Question: {payload.query}

Instructions:
- Be encouraging, precise, and concise (3-5 sentences).
- Explicitly cite the record title if available.
"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                OLLAMA_URL,
                json={"model": MODEL_NAME, "prompt": prompt, "stream": False}
            )
            answer = response.json().get("response", "Could not synthesize response.").strip()
        except Exception:
            answer = f"Found {len(retrieved_docs)} records matching your query."

    return {"answer": answer, "sources": retrieved_docs}


@app.post("/api/career/gap-analysis")
async def analyze_skill_gap(payload: GapAnalysisQuery, user_id: str = Depends(get_user_id)):
    """Compares user's graph skills against target job role requirements."""
    graph = get_graph(user_id)
    user_skills = [
        attrs.get("label") 
        for node, attrs in graph.graph.nodes(data=True) 
        if attrs.get("type") == "Skill" or node.startswith("skill:")
    ]

    prompt = f"""
You are an expert career advisor. Analyze the user's skills against their target role.

Target Role: {payload.target_role}
User's Extracted Skills: {user_skills if user_skills else "No skills logged yet."}

Tasks:
1. Identify 3 key technical skills required for '{payload.target_role}' that are MISSING from user's skills.
2. Provide 2 actionable recommendations to bridge the gap.

Return STRICT JSON format:
{{
  "missing_skills": ["MissingSkill1", "MissingSkill2", "MissingSkill3"],
  "recommendations": ["Action item 1", "Action item 2"]
}}
Respond ONLY with valid JSON.
"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                OLLAMA_URL,
                json={"model": MODEL_NAME, "prompt": prompt, "stream": False}
            )
            raw = response.json().get("response", "{}").strip()
            clean = raw.replace("```json", "").replace("```", "").strip()
            import json
            return json.loads(clean)
        except Exception:
            return {
                "missing_skills": ["System Architecture", "Production MLOps", "Distributed Computing"],
                "recommendations": ["Build a deployed open-source project.", "Complete an advanced domain certification."]
            }


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
    """Clears all session files, graph JSONs, and Chroma collection for current user."""
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