import re

from requirement_analysis import analyse_requirement, build_requirement_retrieval_text


JOB_SECTION_ALIASES = {
    "role_overview": {
        "description",
        "about the role",
        "about this role",
        "role overview",
        "the role",
        "about the job",
        "role description"
    },

    "required_behaviours": {
        "essential behaviours",
        "required behaviours",
        "core behaviours",
        "behaviours",
    },
    "benefits": {
        "benefits",
        "perks",
        "what we offer",
        "why join us",
    },

    "responsibilities": {
        "responsibilities",
        "what you'll own",
        "what you will own",
        "what you'll do",
        "what you will do",
        "your responsibilities",
        "your role",
        "what you will be doing"
    },
    "required_qualifications": {
        "requirements",
        "required qualifications",
        "what we're looking for",
        "what we are looking for",
        "what you'll bring",
        "what you will bring",
        "what you need",
        "about you",
        "essential skills",
        "essential qualifications",
        "essential skills and qualifications",
    },
    "preferred_qualifications": {
        "preferred qualifications",
        "preferred experience",
        "ideal experience",
        "nice to have",
        "nice to haves",
        "bonus points",
        "desired skills",
        "desired qualifications",
        "desired skills and qualifications",
    },
    "technical_skills": {
        "tech stack",
        "technology stack",
        "technical skills",
        "tools and technologies",
    },
    "outcomes": {
        "outcomes",
        "expected outcomes",
        "what success looks like",
        "success measures",
    },
    "working_culture": {
        "how we work",
        "our culture",
        "working here",
        "life at the company",
    },
    "interview_process": {
        "interview process",
        "process",
        "hiring process",
        "recruitment process",
        "what to expect",
    },
}


MATCHING_RULES = {
    "role_overview": {
        "use_for_matching": False,
        "requirement_type": None,
    },
    "responsibilities": {
        "use_for_matching": True,
        "requirement_type": "required",
    },
    "required_behaviours": {
        "use_for_matching": True,
        "requirement_type": "required",
    },
    "benefits": {
        "use_for_matching": False,
        "requirement_type": None,
    },
    "required_qualifications": {
        "use_for_matching": True,
        "requirement_type": "required",
    },
    "preferred_qualifications": {
        "use_for_matching": True,
        "requirement_type": "preferred",
    },
    "technical_skills": {
        "use_for_matching": True,
        "requirement_type": "required",
    },
    "outcomes": {
        "use_for_matching": False,
        "requirement_type": None,
    },
    "working_culture": {
        "use_for_matching": False,
        "requirement_type": None,
    },
    "interview_process": {
        "use_for_matching": False,
        "requirement_type": None,
    },
    "job_metadata": {
        "use_for_matching": False,
        "requirement_type": None,
    },
}


def normalize_job_heading(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(
        r"^[#*_\s]+|[#*_:|\s]+$",
        "",
        normalized,
    )
    normalized = re.sub(
        r"[^a-z0-9'& ]+",
        " ",
        normalized,
    )
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def detect_job_section(line: str) -> str | None:
    normalized = normalize_job_heading(line)

    # Examples: "Your Role at ONI", "Your Role at Google"
    if normalized.startswith("your role at "):
        return "responsibilities"

    if normalized.startswith("essential skills"):
        return "required_qualifications"

    if normalized.startswith("essential qualifications"):
        return "required_qualifications"

    if normalized.startswith("desired skills"):
        return "preferred_qualifications"

    if normalized.startswith("desired qualifications"):
        return "preferred_qualifications"

    if normalized.startswith("essential behaviours"):
        return "required_behaviours"

    # Some job pages begin their benefits section with a sentence
    # instead of a heading.
    if (
        normalized.startswith("at ")
        and "benefit" in normalized
    ):
        return "benefits"

    for section_type, aliases in JOB_SECTION_ALIASES.items():
        if normalized in aliases:
            return section_type

    return None


def clean_job_line(line: str) -> str:
    line = line.replace("\\n", " ")
    line = re.sub(r"\s+", " ", line).strip()

    return re.sub(
        r"^(?:[-*•▪◦●]+|\d+[.)])\s*",
        "",
        line,
    ).strip()


def append_job_section(
    sections: list[dict],
    section_type: str,
    heading: str,
    lines: list[str],
):
    text = "\n".join(lines).strip()

    if not text:
        return

    rule = MATCHING_RULES[section_type]

    sections.append(
        {
            "section_id": (
                f"job_section_{len(sections) + 1:03d}"
            ),
            "section_type": section_type,
            "heading": heading,
            "text": text,
            "use_for_matching": rule["use_for_matching"],
            "requirement_type": rule["requirement_type"],
        }
    )


def split_job_sections(
    text: str,
) -> list[dict]:
    sections = []

    current_type = "job_metadata"
    current_heading = "Job metadata"
    current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        detected_type = detect_job_section(line)

        if detected_type:
            append_job_section(
                sections=sections,
                section_type=current_type,
                heading=current_heading,
                lines=current_lines,
            )

            current_type = detected_type
            current_heading = line
            current_lines = []
        else:
            cleaned_line = clean_job_line(line)

            if cleaned_line:
                current_lines.append(cleaned_line)

    append_job_section(
        sections=sections,
        section_type=current_type,
        heading=current_heading,
        lines=current_lines,
    )

    return sections


def build_job_requirements(
    sections: list[dict],
) -> list[dict]:
    requirements = []

    for section in sections:
        if not section["use_for_matching"]:
            continue

        items = [
            clean_job_line(line)
            for line in section["text"].splitlines()
            if clean_job_line(line)
        ]

        for item in items:
            requirement_number = len(requirements) + 1
            analysis = analyse_requirement(item)

            requirements.append(
                {
                    "requirement_id": (
                        f"requirement_{requirement_number:03d}"
                    ),
                    "requirement_type": (
                        section["requirement_type"]
                    ),
                    "category": section["section_type"],
                    "source_text": item,
                    "retrieval_text": (
                        f"Job requirement category: "
                        f"{section['section_type']}\n"
                        "Requirement: "
                        f"{build_requirement_retrieval_text(item, analysis)}"
                    ),
                    **analysis,
                }
            )

    return requirements
