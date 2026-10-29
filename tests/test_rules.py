from backend.app.rules import is_chronological, fallback_year
from backend.app.skills import normalize_skills

def test_chronology():
    assert is_chronological("2023", "2024-05")
    assert not is_chronological("2024", "2023")
    assert not is_chronological("Unknown", "2024")

def test_fallback_year_ignores_future_years():
    assert fallback_year("Issued 2022, valid until 2031") == "2022"

def test_skill_normalization_merges_variants():
    assert normalize_skills(["ReactJS", "react", "JS"]) == ["React", "JavaScript"]