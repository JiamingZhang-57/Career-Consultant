import re

from skill_taxonomy import extract_canonical_skills


DATE_RANGE_PATTERN = re.compile(
    r"\b(?:[A-Za-z]{3,9}\.?\s+)?(?:19|20)\d{2}\s*"
    r"(?:-|–|—|to)\s*"
    r"(?:present|current|now|(?:[A-Za-z]{3,9}\.?\s+)?(?:19|20)\d{2})\b",
    re.IGNORECASE,
)


EVIDENCE_KINDS = {
    "skills": "skill_inventory",
    "work_experience": "experience_entry",
    "research_experience": "research_entry",
    "projects": "project_entry",
    "education": "education_entry",
    "certifications": "certification_entry",
    "publications": "publication_entry",
    "awards": "award_entry",
    "leadership": "leadership_entry",
    "volunteering": "volunteering_entry",
    "languages": "language_inventory",
}


def extract_resume_structure(
    section_type: str,
    source_text: str,
) -> dict:
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    heading_candidates = [
        line.lstrip("•-* ")
        for line in lines[:4]
        if not line.startswith(("•", "-", "*"))
        and len(line) <= 160
    ]

    return {
        "evidence_kind": EVIDENCE_KINDS.get(
            section_type,
            "section_evidence",
        ),
        "entry_heading": heading_candidates[0] if heading_candidates else "",
        "date_ranges": DATE_RANGE_PATTERN.findall(source_text),
        "canonical_skills": extract_canonical_skills(source_text),
    }
