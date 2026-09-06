import re


RESUME_SECTION_ALIASES = {
    "summary": {
        "summary",
        "profile",
        "professional summary",
        "personal profile",
        "career objective",
        "objective",
    },
    "skills": {
        "skills",
        "technical skills",
        "core skills",
        "core competencies",
        "technologies",
        "tools and technologies",
    },
    "work_experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment experience",
        "employment history",
        "career history",
    },
    "projects": {
        "projects",
        "selected projects",
        "personal projects",
        "research projects",
        "academic projects",
    },
    "education": {
        "education",
        "academic background",
        "academic qualifications",
    },
    "certifications": {
        "certifications",
        "certificates",
        "licenses and certifications",
    },
    "publications": {
        "publications",
        "research publications",
        "papers",
    },
    "awards": {
        "awards",
        "honours and awards",
        "honors and awards",
        "achievements",
    },
}


def normalize_heading(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"[:|]+$", "", normalized)
    normalized = re.sub(r"[^a-z0-9& ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def detect_resume_section(line: str) -> str | None:
    normalized_line = normalize_heading(line)

    for section_type, aliases in RESUME_SECTION_ALIASES.items():
        if normalized_line in aliases:
            return section_type

    return None


def clean_resume_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def append_section(
    sections: list[dict],
    section_type: str,
    heading: str,
    lines: list[str],
    page_numbers: set[int],
):
    text = "\n".join(lines).strip()

    if not text:
        return

    sections.append(
        {
            "section_id": (
                f"resume_section_{len(sections) + 1:03d}"
            ),
            "section_type": section_type,
            "heading": heading,
            "page_numbers": sorted(page_numbers),
            "text": text,
        }
    )


def split_resume_sections(
    pages: list[dict],
) -> list[dict]:
    sections = []

    current_type = "header"
    current_heading = "Resume header"
    current_lines = []
    current_pages = set()

    for page in pages:
        page_number = page["page_number"]

        for raw_line in page["text"].splitlines():
            line = clean_resume_line(raw_line)

            if not line:
                continue

            detected_type = detect_resume_section(line)

            if detected_type:
                append_section(
                    sections=sections,
                    section_type=current_type,
                    heading=current_heading,
                    lines=current_lines,
                    page_numbers=current_pages,
                )

                current_type = detected_type
                current_heading = line
                current_lines = []
                current_pages = set()
                continue

            current_lines.append(line)
            current_pages.add(page_number)

    append_section(
        sections=sections,
        section_type=current_type,
        heading=current_heading,
        lines=current_lines,
        page_numbers=current_pages,
    )

    return sections