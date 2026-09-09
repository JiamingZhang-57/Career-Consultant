import re

from skill_taxonomy import (
    extract_canonical_skills,
    related_skill_terms,
)


YEARS_PATTERN = re.compile(
    r"\b(?P<minimum>\d{1,2})(?:\s*[-–]\s*(?P<maximum>\d{1,2}))?\+?"
    r"\s+years?\b",
    re.IGNORECASE,
)

SCALE_TERMS = {
    "production": {"production", "production-grade"},
    "large_scale": {"large scale", "large-scale", "at scale"},
    "enterprise": {"enterprise", "enterprise-scale"},
    "high_traffic": {"high traffic", "high-traffic"},
    "gpu_scale": {"multi-gpu", "distributed training", "gpu cluster"},
}

INDUSTRY_TERMS = {
    "healthcare": {"healthcare", "medical", "clinical"},
    "finance": {"finance", "financial services", "fintech", "banking"},
    "scientific_software": {
        "scientific software",
        "microscopy",
        "laboratory",
        "life sciences",
    },
    "automotive": {"automotive", "autonomous driving"},
    "robotics": {"robotics", "robotic"},
    "cybersecurity": {"cybersecurity", "information security"},
}


def _matching_labels(text: str, vocabulary: dict[str, set[str]]) -> list[str]:
    lowered = text.lower()
    return sorted(
        label
        for label, terms in vocabulary.items()
        if any(term in lowered for term in terms)
    )


def _material_clauses(text: str) -> list[str]:
    clauses = [
        clause.strip(" .")
        for clause in re.split(r";|\n", text)
        if clause.strip(" .")
    ]
    return clauses or [text.strip()]


def analyse_requirement(text: str) -> dict:
    skills = extract_canonical_skills(text)
    years = []

    for match in YEARS_PATTERN.finditer(text):
        years.append(
            {
                "minimum": int(match.group("minimum")),
                "maximum": (
                    int(match.group("maximum"))
                    if match.group("maximum")
                    else None
                ),
                "source_text": match.group(0),
            }
        )

    scale = _matching_labels(text, SCALE_TERMS)
    industries = _matching_labels(text, INDUSTRY_TERMS)
    clauses = _material_clauses(text)
    material_criteria = list(clauses)
    material_criteria.extend(f"Explicit skill: {skill}" for skill in skills)
    material_criteria.extend(
        f"Experience duration: {item['source_text']}" for item in years
    )
    material_criteria.extend(f"Scale context: {item}" for item in scale)
    material_criteria.extend(
        f"Industry context: {item}" for item in industries
    )

    return {
        "material_criteria": list(dict.fromkeys(material_criteria)),
        "canonical_skills": skills,
        "related_skill_terms": related_skill_terms(skills),
        "years_constraints": years,
        "scale_constraints": scale,
        "industry_constraints": industries,
    }


def build_requirement_retrieval_text(text: str, analysis: dict) -> str:
    parts = [text]
    if analysis["canonical_skills"]:
        parts.append("Skills: " + ", ".join(analysis["canonical_skills"]))
    if analysis["related_skill_terms"]:
        parts.append(
            "Related retrieval concepts: "
            + ", ".join(analysis["related_skill_terms"])
        )
    if analysis["years_constraints"]:
        parts.append(
            "Experience duration constraints: "
            + ", ".join(
                item["source_text"]
                for item in analysis["years_constraints"]
            )
        )
    return "\n".join(parts)
