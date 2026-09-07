from job_chunking import (
    build_job_requirements,
    detect_job_section,
    split_job_sections,
)


def test_detects_common_job_headings():
    headings = {
        "Role description": "role_overview",
        "What you will be doing": "responsibilities",
        "What You Need": "required_qualifications",
        "Nice To Have": "preferred_qualifications",
        "What we offer": "benefits",
        "Process": "interview_process",
    }

    for heading, expected in headings.items():
        assert detect_job_section(heading) == expected


def test_builds_atomic_requirements():
    job_text = """
Title
Deep Learning Research Engineer

Role description
Build machine learning products.

What you will be doing
- Develop production computer vision models.

What You Need
- Strong Python experience.
- Experience with PyTorch.

Nice To Have
- Experience with modern C++.

What we offer
- Competitive salary.

Process
Technical interview.
"""

    sections = split_job_sections(job_text)
    requirements = build_job_requirements(sections)

    section_types = [
        section["section_type"]
        for section in sections
    ]

    assert section_types == [
        "job_metadata",
        "role_overview",
        "responsibilities",
        "required_qualifications",
        "preferred_qualifications",
        "benefits",
        "interview_process",
    ]

    assert len(requirements) == 4

    assert [
        requirement["requirement_type"]
        for requirement in requirements
    ] == [
        "required",
        "required",
        "required",
        "preferred",
    ]

    assert [
        requirement["category"]
        for requirement in requirements
    ] == [
        "responsibilities",
        "required_qualifications",
        "required_qualifications",
        "preferred_qualifications",
    ]

    assert requirements[0]["source_text"] == (
        "Develop production computer vision models."
    )

    assert requirements[3]["source_text"] == (
        "Experience with modern C++."
    )


def test_excludes_non_matching_sections():
    job_text = """
Role description
This is an overview of the company.

What we offer
Competitive salary and annual leave.

Process
Two technical interviews.
"""

    sections = split_job_sections(job_text)
    requirements = build_job_requirements(sections)

    assert requirements == []