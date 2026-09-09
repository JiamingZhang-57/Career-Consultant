from resume_structure import extract_resume_structure
from skill_taxonomy import extract_canonical_skills
from chunking import split_resume_sections


def test_extracts_structured_experience_metadata():
    structure = extract_resume_structure(
        "work_experience",
        "ML Engineer\nJanuary 2022 - Present\nBuilt PyTorch and OpenCV models.",
    )

    assert structure["evidence_kind"] == "experience_entry"
    assert structure["entry_heading"] == "ML Engineer"
    assert structure["date_ranges"] == ["January 2022 - Present"]
    assert structure["canonical_skills"] == ["opencv", "pytorch"]


def test_skill_aliases_do_not_treat_incidental_c_as_c_language():
    skills = extract_canonical_skills(
        "Built GANs with Python and C++ for computer vision."
    )

    assert "gan" in skills
    assert "python" in skills
    assert "c++" in skills
    assert "c" not in skills


def test_parses_inline_resume_section_heading():
    sections = split_resume_sections(
        [
            {
                "page_number": 1,
                "text": "Skills: Python, PyTorch",
            }
        ]
    )

    assert sections[0]["section_type"] == "skills"
    assert sections[0]["text"] == "Python, PyTorch"
