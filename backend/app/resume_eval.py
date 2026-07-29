import re

def evaluate_resume(resume_text: str, metadata: dict) -> dict:
    """
    Evaluates a resume by analyzing structural sections, quantified metrics, 
    and extracted skills, returning a score (0-100) and feedback.
    """
    score = 40  # Base starting score
    feedback = []

    text_lower = resume_text.lower()

    # 1. Structural Section Check
    key_sections = {
        "education": 10,
        "experience": 15,
        "skills": 10,
        "projects": 15,
        "certifications": 5
    }

    for section, weight in key_sections.items():
        if section in text_lower:
            score += weight
        else:
            feedback.append(f"Missing distinct '{section.capitalize()}' section header.")

    # 2. Quantified Impact Metrics Check (percentages, dollar amounts, numbers)
    impact_matches = re.findall(r'\b\d+%\b|\b\$\d+\b|\b\d+\+\b|\bby \d+\b', text_lower)
    if impact_matches:
        impact_bonus = min(len(impact_matches) * 4, 15)
        score += impact_bonus
    else:
        feedback.append("Add measurable outcomes and metrics (e.g., 'Improved speed by 30%' or 'Managed 5+ projects').")

    # 3. Extracted Skills Check
    skills = metadata.get("extracted_skills", [])
    if len(skills) >= 5:
        score += 10
    elif len(skills) > 0:
        score += 5
    else:
        feedback.append("Include more explicit technical and soft skills keywords.")

    score = min(score, 100)

    return {
        "score": score,
        "skills_detected": skills,
        "feedback": feedback if feedback else ["Great job! Resume structure and metrics look strong."],
        "summary": metadata.get("summary", "")
    }