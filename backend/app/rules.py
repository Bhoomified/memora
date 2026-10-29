import re
from datetime import datetime

CATEGORIES = {"Projects", "Skills", "Certifications", "Internships", "Achievements", "Academics"}
_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?$")

def parse_date(d):
    m = _DATE_RE.match(str(d or "").strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)) if m.group(2) else None)

def is_chronological(earlier, later):
    """True only if both dates are known and `earlier` is not after `later`."""
    a, b = parse_date(earlier), parse_date(later)
    if a is None or b is None:
        return False
    if a[1] is None or b[1] is None:      # one side is year-only, so compare years
        return a[0] <= b[0]
    return a <= b

def fallback_year(text):
    """If the LLM couldn't find a date, use the latest plausible year in the text."""
    now = datetime.now().year
    years = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", text or "") if 1990 <= int(y) <= now]
    return str(max(years)) if years else "Unknown"