import os
import json
import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # fast + free-tier friendly

def _get_api_key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return key

async def call_llm(prompt: str) -> str:
    """Generic call to Groq's OpenAI-compatible chat completions endpoint."""
    headers = {"Authorization": f"Bearer {_get_api_key()}", "Content-Type": "application/json"}
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GROQ_URL, headers=headers, json=body)
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


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
    if not text.strip():
        return {
            "title": "Empty Document", "category": "Academics", "date": "Unknown",
            "extracted_skills": [], "summary": "No text could be extracted from this document.",
            "related_entities": []
        }
    prompt = f"{SYSTEM_PROMPT}\n\nDocument Text Content:\n{text[:2500]}"
    try:
        raw = await call_llm(prompt)
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        print(f"LLM Classification Warning/Error: {str(e)}")
        return {
            "title": "Processed Document", "category": "Academics", "date": "Unknown",
            "extracted_skills": [], "summary": text[:200], "related_entities": []
        }


RELATIONSHIP_PROMPT = """
You are analyzing two entries in someone's personal knowledge graph to detect a causal or developmental relationship between them.

Entry A (earlier): "{a_title}" ({a_type}) - {a_summary}
Entry B (newer): "{b_title}" ({b_type}) - {b_summary}

Does Entry A meaningfully connect to Entry B? Answer with ONLY one word from this list:
LED_TO
BUILT_ON
APPLIED_IN
NONE

Answer with exactly one word, nothing else.
"""

async def infer_relationship(new_doc: dict, existing_doc: dict) -> str:
    prompt = RELATIONSHIP_PROMPT.format(
        a_title=existing_doc.get("title", ""), a_type=existing_doc.get("type", ""),
        a_summary=existing_doc.get("summary", ""),
        b_title=new_doc.get("title", ""), b_type=new_doc.get("category", ""),
        b_summary=new_doc.get("summary", "")
    )
    try:
        raw = (await call_llm(prompt)).strip().upper()
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
    try:
        return await call_llm(prompt)
    except Exception as e:
        print(f"Story generation warning: {e}")
        return "Your growth story couldn't be generated right now — try again shortly."


async def chat_with_context(query: str, context_str: str) -> str:
    prompt = f"""
You are Memora, an intelligent AI Digital Identity Assistant representing the user's academic and professional journey.
Answer the user's question directly based ONLY on their uploaded digital records below.

User Records:
{context_str if context_str else "No prior records uploaded matching this query."}

User Question: {query}

Instructions:
- Be encouraging, precise, and concise (3-5 sentences).
- Explicitly cite the record title if available.
"""
    try:
        return await call_llm(prompt)
    except Exception:
        return "Could not synthesize response right now."


async def analyze_skill_gap(target_role: str, user_skills: list) -> dict:
    prompt = f"""
You are an expert career advisor. Analyze the user's skills against their target role.

Target Role: {target_role}
User's Extracted Skills: {user_skills if user_skills else "No skills logged yet."}

Tasks:
1. Identify 3 key technical skills required for '{target_role}' that are MISSING from user's skills.
2. Provide 2 actionable recommendations to bridge the gap.

Return STRICT JSON format:
{{
  "missing_skills": ["MissingSkill1", "MissingSkill2", "MissingSkill3"],
  "recommendations": ["Action item 1", "Action item 2"]
}}
Respond ONLY with valid JSON.
"""
    try:
        raw = await call_llm(prompt)
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return {
            "missing_skills": ["System Architecture", "Production MLOps", "Distributed Computing"],
            "recommendations": ["Build a deployed open-source project.", "Complete an advanced domain certification."]
        }