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