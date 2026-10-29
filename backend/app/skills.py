import re

ALIASES = {
    "js": "JavaScript", "javascript": "JavaScript", "ts": "TypeScript", "typescript": "TypeScript",
    "py": "Python", "python3": "Python", "python": "Python",
    "ml": "Machine Learning", "machine learning": "Machine Learning",
    "dl": "Deep Learning", "deep learning": "Deep Learning",
    "nlp": "Natural Language Processing", "natural language processing": "Natural Language Processing",
    "reactjs": "React", "react.js": "React", "react": "React",
    "node": "Node.js", "nodejs": "Node.js", "node.js": "Node.js",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn", "scikit-learn": "scikit-learn",
    "tf": "TensorFlow", "tensorflow": "TensorFlow", "pytorch": "PyTorch", "torch": "PyTorch",
    "k8s": "Kubernetes", "kubernetes": "Kubernetes", "docker": "Docker",
    "cpp": "C++", "c plus plus": "C++", "c++": "C++",
    "fastapi": "FastAPI", "sql": "SQL", "git": "Git", "github": "Git",
    "aws": "AWS", "gcp": "Google Cloud", "google cloud": "Google Cloud",
}

def normalize_skill(raw):
    if not isinstance(raw, str):
        return None
    key = re.sub(r"\s+", " ", raw.strip().lower())
    if not key or len(key) > 40:
        return None
    return ALIASES.get(key, raw.strip() if raw.strip()[:1].isupper() else raw.strip().title())

def normalize_skills(skills, limit=15):
    seen, out = set(), []
    for s in skills or []:
        n = normalize_skill(s)
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out[:limit]