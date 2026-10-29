from curses import raw
import os
import json
import httpx
import asyncio

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # fast + free-tier friendly

from backend.app.skills import normalize_skills
from backend.app.rules import CATEGORIES, parse_date, fallback_year


def _get_api_key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return key

async def call_llm(prompt: str, json_mode: bool = False, retries: int = 3) -> str:
    headers = {"Authorization": f"Bearer {_get_api_key()}", "Content-Type": "application/json"}
    body = {
        "model": os.environ.get("GROQ_MODEL", GROQ_MODEL),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(retries):
            resp = await client.post(GROQ_URL, headers=headers, json=body)
            if resp.status_code == 429 or resp.status_code >= 500:
                await asyncio.sleep(2 ** attempt)   # wait 1s, 2s, 4s, then retry
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    raise RuntimeError("LLM unavailable after retries")


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
        raw = await call_llm(prompt, json_mode=True)
        meta = json.loads(raw)
        return validate_metadata(meta, text)
    except Exception as e:
        print(f"LLM Classification Warning/Error: {str(e)}")
        return {
            "title": "Processed Document", "category": "Academics", "date": "Unknown",
            "extracted_skills": [], "summary": text[:200], "related_entities": []
        }


RELATIONSHIP_PROMPT = """
Two entries from someone's personal knowledge graph.

Entry A (earlier): "{a_title}" ({a_type}) - {a_summary}
Entry B (later): "{b_title}" ({b_type}) - {b_summary}

Does Entry A meaningfully lead to, or get built upon in, Entry B?
Return ONLY JSON: {{"relation": "LED_TO" | "BUILT_ON" | "APPLIED_IN" | "NONE", "reason": "<one short sentence citing a shared skill or topic>"}}
If there is no clear, specific connection, use NONE.
"""

async def infer_relationship(later: dict, earlier: dict) -> dict:
    prompt = RELATIONSHIP_PROMPT.format(
        a_title=earlier.get("title", ""), a_type=earlier.get("type") or earlier.get("category", ""),
        a_summary=earlier.get("summary", ""),
        b_title=later.get("title", ""), b_type=later.get("type") or later.get("category", ""),
        b_summary=later.get("summary", ""),
    )
    try:
        data = json.loads(await call_llm(prompt, json_mode=True))
        relation = str(data.get("relation", "NONE")).upper()
        if relation not in {"LED_TO", "BUILT_ON", "APPLIED_IN"}:
            return {"relation": "NONE", "reason": ""}
        return {"relation": relation, "reason": str(data.get("reason", ""))[:200]}
    except Exception as e:
        print(f"Relationship inference warning: {e}")
        return {"relation": "NONE", "reason": ""}

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

import difflib
from backend.app.skills import normalize_skills

ROLE_SKILLS = {
    "machine learning engineer": ["Python", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "scikit-learn", "SQL", "Docker", "Git"],
    "data scientist": ["Python", "SQL", "Machine Learning", "scikit-learn", "Pandas", "Statistics", "Data Visualization", "Git"],
    "full stack developer": ["JavaScript", "TypeScript", "React", "Node.js", "SQL", "REST APIs", "Docker", "Git"],
    "backend developer": ["Python", "FastAPI", "SQL", "PostgreSQL", "REST APIs", "Docker", "Git", "AWS"],
    "devops engineer": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Git", "Terraform"],
    "data analyst": ["SQL", "Excel", "Python", "Pandas", "Data Visualization", "Statistics"],
}
async def analyze_skill_gap(target_role: str, user_skills: list) -> dict:
    mine = normalize_skills(user_skills)
    mine_lower = {s.lower() for s in mine}

    match = difflib.get_close_matches(target_role.strip().lower(), ROLE_SKILLS.keys(), n=1, cutoff=0.5)
    if match:
        needed, basis, role_used = ROLE_SKILLS[match[0]], "curated", match[0]
    else:
        # Unknown role: ask the LLM for requirements, and label it honestly
        try:
            data = json.loads(await call_llm(
                f'List 8 core technical skills for the role "{target_role}". '
                f'Return ONLY JSON: {{"skills": ["..."]}}', json_mode=True))
            needed = normalize_skills(data.get("skills"))[:8]
        except Exception:
            needed = []
        basis, role_used = "ai_estimated", target_role

    have = [s for s in needed if s.lower() in mine_lower]
    missing = [s for s in needed if s.lower() not in mine_lower]
    coverage = round(100 * len(have) / len(needed)) if needed else 0

    recommendations = []
    if missing:
        try:
            data = json.loads(await call_llm(
                f"Someone targeting the role '{role_used}' is missing these skills: {missing}. "
                f'Give 2 concrete, practical project or learning ideas. '
                f'Return ONLY JSON: {{"recommendations": ["...", "..."]}}', json_mode=True))
            recommendations = [str(r)[:200] for r in data.get("recommendations", [])][:2]
        except Exception:
            pass

    return {
        "role_matched": role_used, "basis": basis, "coverage_percent": coverage,
        "have": have, "missing": missing, "recommendations": recommendations,
    }
def validate_metadata(meta: dict, text: str) -> dict:
    category = meta.get("category")
    if category not in CATEGORIES:
        category = "Academics"
    date = meta.get("date")
    if parse_date(date) is None:
        date = fallback_year(text)
    return {
        "title": str(meta.get("title") or "Untitled Document")[:120],
        "category": category,
        "date": date,
        "extracted_skills": normalize_skills(meta.get("extracted_skills")),
        "summary": str(meta.get("summary") or "")[:500],
        "related_entities": [str(e)[:80] for e in (meta.get("related_entities") or [])][:10],
    }
