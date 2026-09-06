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
    "skill",
    "skills",
    "technical skills",
    "core skills",
    "core competencies",
    "technologies",
    "tools and technologies"},

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

    "research_experience": {
        "research",
        "research experience",
        "selected research",
        "research projects",
    }
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

RESUME_SECTION_LABELS = {
    "header": "Candidate information",
    "summary": "Professional summary",
    "skills": "Technical skills",
    "work_experience": "Work experience",
    "projects": "Projects",
    "education": "Education",
    "certifications": "Certifications",
    "publications": "Publications",
    "awards": "Awards and achievements",
    "research_experience": "Research experience"}


def split_lines_by_size(
    text: str,
    max_chars: int = 700,
) -> list[str]:
    """
    Split only at line boundaries.

    There is deliberately no character overlap because overlap can
    duplicate evidence or split technical terms.
    """
    lines = [
        clean_resume_line(line)
        for line in text.splitlines()
        if clean_resume_line(line)
    ]

    groups = []
    current_lines = []
    current_length = 0

    for line in lines:
        additional_length = len(line)

        if current_lines:
            additional_length += 1

        if (
            current_lines
            and current_length + additional_length > max_chars
        ):
            groups.append("\n".join(current_lines))
            current_lines = [line]
            current_length = len(line)
        else:
            current_lines.append(line)
            current_length += additional_length

    if current_lines:
        groups.append("\n".join(current_lines))

    return groups

MONTH_PATTERN = re.compile(
    r"\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?"
    r")\b",
    re.IGNORECASE,
)

YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


def looks_like_date_line(line: str) -> bool:
    """
    Detect employment/project date lines such as:
    April 2026 – Now
    Dec. 2025 – Mar. 2026
    """
    normalized = line.lower().replace(".", "")

    has_year = bool(
        YEAR_PATTERN.search(normalized)
    )

    has_month = bool(
        MONTH_PATTERN.search(normalized)
    )

    has_current_word = bool(
        re.search(
            r"\b(present|current|now)\b",
            normalized,
        )
    )

    return has_year and (
        has_month or has_current_word
    )

def combine_standalone_bullets(
    lines: list[str],
) -> list[str]:
    combined = []
    bullet_pending = False

    for line in lines:
        if line in {"•", "▪", "◦", "●"}:
            bullet_pending = True
            continue

        if bullet_pending:
            combined.append(f"• {line}")
            bullet_pending = False
        else:
            combined.append(line)

    return combined

def find_entry_start(
    lines: list[str],
    date_index: int,
) -> int:
    """
    Walk backwards from a date line to find the entry header.

    Most resume entries contain approximately:
    organization/project
    location
    role
    date
    """
    start = date_index

    for _ in range(4):
        if start == 0:
            break

        previous_line = lines[start - 1]

        # A previous evidence sentence normally ends the old entry.
        if previous_line.endswith((".", ";")):
            break

        if previous_line.startswith("•"):
            break

        start -= 1

    return start


def split_experience_entries(
    text: str,
) -> list[str]:
    lines = [
        clean_resume_line(line)
        for line in text.splitlines()
        if clean_resume_line(line)
    ]

    lines = combine_standalone_bullets(lines)

    date_indexes = [
        index
        for index, line in enumerate(lines)
        if looks_like_date_line(line)
    ]

    if not date_indexes:
        return ["\n".join(lines)] if lines else []

    entry_starts = [0]

    for date_index in date_indexes[1:]:
        entry_start = find_entry_start(
            lines=lines,
            date_index=date_index,
        )

        if entry_start > entry_starts[-1]:
            entry_starts.append(entry_start)

    entries = []

    for index, start in enumerate(entry_starts):
        if index + 1 < len(entry_starts):
            end = entry_starts[index + 1]
        else:
            end = len(lines)

        entry_text = "\n".join(
            lines[start:end]
        ).strip()

        if entry_text:
            entries.append(entry_text)

    return entries

def build_resume_evidence_chunks(
    sections: list[dict],
) -> list[dict]:
    chunks = []

    for section in sections:
        section_type = section["section_type"]
        section_label = RESUME_SECTION_LABELS.get(
            section_type,
            section_type.replace("_", " ").title(),
        )

        if section_type in {
            "work_experience",
            "research_experience",
        }:
            text_groups = split_experience_entries(
                section["text"]
            )
        else:
            text_groups = split_lines_by_size(
                section["text"]
            )

        for source_text in text_groups:
            chunk_number = len(chunks) + 1

            retrieval_text = (
                f"Resume section: {section_label}\n"
                f"{source_text}"
            )

            chunks.append(
                {
                    "chunk_id": (
                        f"resume_chunk_{chunk_number:03d}"
                    ),
                    "section_id": section["section_id"],
                    "section_type": section_type,
                    "heading": section["heading"],
                    "page_numbers": section["page_numbers"],

                    # 原始证据，最终展示给用户
                    "source_text": source_text,

                    # 加上 section 上下文，用于生成 embedding
                    "retrieval_text": retrieval_text,

                    # 姓名和联系方式不能证明工作能力
                    "use_for_matching": (
                        section_type != "header"
                    ),
                    "character_count": len(source_text),
                }
            )

    return chunks