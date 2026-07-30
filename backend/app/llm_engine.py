import httpx
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

SYSTEM_PROMPT = """
You are an expert AI Data Identity System named Memora. 
Analyze the document text provided and extract metadata into a strict JSON object.

Output JSON format strictly:
{
  "title": "<A concise, descriptive title of the document>",
  "category": "<Must be ONE of: Projects | Skills | Certifications | Internships | Achievements | Academics>",
  "date": "<YYYY or YYYY-MM if available in document, otherwise 'Unknown'>",
  "extracted_skills": ["Skill1", "Skill2", "Skill3"],
  "summary": "<2 sentence summary of what this document represents>",
  "related_entities": ["Organization, Company, Institution, or Key Project Name"]
}

Rules:
- Output ONLY valid raw JSON.
- Do NOT wrap in markdown code blocks like ```json.
- Do NOT include commentary outside the JSON object.
"""

async def classify_document(text: str) -> dict:
    """
    Passes extracted document text to the local Ollama LLM 
    and returns parsed JSON metadata.
    """
    if not text.strip():
        return {
            "title": "Empty Document",
            "category": "Academics",
            "date": "Unknown",
            "extracted_skills": [],
            "summary": "No text could be extracted from this document.",
            "related_entities": []
        }

    prompt = f"{SYSTEM_PROMPT}\n\nDocument Text Content:\n{text[:2500]}"
    
    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False
                }
            )
            res_data = response.json()
            raw_output = res_data.get("response", "{}").strip()
            
            # Sanitize markdown formatting if Ollama accidentally adds backticks
            clean_json = raw_output.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"LLM Classification Warning/Error: {str(e)}")
            return {
                "title": "Processed Document",
                "category": "Academics",
                "date": "Unknown",
                "extracted_skills": [],
                "summary": text[:200],
                "related_entities": []
            }
RELATIONSHIP_PROMPT = """
You are analyzing two entries in someone's personal knowledge graph to detect a causal or developmental relationship between them.

Entry A (earlier): "{a_title}" ({a_type}) - {a_summary}
Entry B (newer): "{b_title}" ({b_type}) - {b_summary}

Does Entry A meaningfully connect to Entry B? Answer with ONLY one word from this list:
LED_TO   (A directly enabled or caused B)
BUILT_ON (B is a continuation or deeper application of A)
APPLIED_IN (skills/knowledge from A were applied practically in B)
NONE     (no meaningful causal connection)

Answer with exactly one word, nothing else.
"""

async def infer_relationship(new_doc: dict, existing_doc: dict) -> str:
    """Asks the local LLM if existing_doc causally leads to new_doc. Returns LED_TO/BUILT_ON/APPLIED_IN/NONE."""
    prompt = RELATIONSHIP_PROMPT.format(
        a_title=existing_doc.get("title", ""), a_type=existing_doc.get("type", ""),
        a_summary=existing_doc.get("summary", ""),
        b_title=new_doc.get("title", ""), b_type=new_doc.get("category", ""),
        b_summary=new_doc.get("summary", "")
    )
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False})
            raw = response.json().get("response", "NONE").strip().upper()
            for valid in ["LED_TO", "BUILT_ON", "APPLIED_IN", "NONE"]:
                if valid in raw:
                    return valid
            return "NONE"
        except Exception as e:
            print(f"Relationship inference warning: {e}")
            return "NONE"


STORY_PROMPT = """
You are Memora, an AI that writes short, warm, first-person-style growth narratives from a timeline of someone's documents.

Timeline (chronological):
{timeline}

Write a short narrative (4-6 sentences) describing this person's growth journey, explicitly connecting how earlier entries led to or enabled later ones. Speak directly to them as "you". Do not invent facts not present in the timeline.
"""

async def generate_growth_story(documents: list) -> str:
    if not documents:
        return "Upload a few documents to unlock your personalized growth story."
    timeline_text = "\n".join(
        f"- [{d.get('date','Unknown')}] {d.get('title')} ({d.get('type')}): {d.get('summary','')}"
        for d in documents
    )
    prompt = STORY_PROMPT.format(timeline=timeline_text[:3000])
    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False})
            return response.json().get("response", "").strip()
        except Exception as e:
            print(f"Story generation warning: {e}")
            return "Your growth story couldn't be generated right now — try again shortly."