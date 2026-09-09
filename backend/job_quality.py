from typing import Literal


QualityStatus = Literal["good", "warning", "rejected"]


def assess_job_extraction(
    job: dict,
    sections: list[dict],
    requirements: list[dict],
) -> dict:
    """Score whether extracted content is safe to use for matching.

    This deliberately measures extraction completeness, not candidate fit.
    A low score therefore means "review the imported job", not "poor fit".
    """
    title = str(job.get("title") or "").strip()
    company = str(job.get("company") or "").strip()
    text = str(job.get("text") or "").strip()
    method = str(job.get("extraction_method") or "")
    warnings = list(job.get("extraction_warnings") or [])

    matching_sections = [
        section
        for section in sections
        if section.get("use_for_matching")
    ]
    required_count = sum(
        requirement.get("requirement_type") == "required"
        for requirement in requirements
    )
    preferred_count = sum(
        requirement.get("requirement_type") == "preferred"
        for requirement in requirements
    )

    score = 0
    issues: list[str] = []

    if title and title.lower() not in {"job details", "unknown role"}:
        score += 10
    else:
        issues.append("The job title is missing or generic.")

    if company and company.lower() != "unknown company":
        score += 10
    else:
        issues.append("The company name could not be identified.")

    if len(text) >= 1000:
        score += 25
    elif len(text) >= 500:
        score += 18
    elif len(text) >= 200:
        score += 10
    else:
        issues.append("Less than 200 characters of job text were extracted.")

    if len(matching_sections) >= 2:
        score += 15
    elif len(matching_sections) == 1:
        score += 8
    else:
        issues.append("No matching-relevant job section was identified.")

    if len(requirements) >= 8:
        score += 25
    elif len(requirements) >= 4:
        score += 18
    elif requirements:
        score += 8
    else:
        issues.append("No individual job requirements were identified.")

    if required_count:
        score += 10
    else:
        issues.append("No required requirement was identified.")

    if method in {
        "ashby_public_api",
        "lever_postings_api",
        "greenhouse_job_board_api",
        "json_ld",
    }:
        score += 5

    if len(text) < 200 or not requirements or required_count == 0:
        status: QualityStatus = "rejected"
    elif score < 70 or issues or warnings:
        status = "warning"
    else:
        status = "good"

    return {
        "score": min(score, 100),
        "status": status,
        "required_requirement_count": required_count,
        "preferred_requirement_count": preferred_count,
        "matching_section_count": len(matching_sections),
        "issues": issues,
        "warnings": warnings,
    }
