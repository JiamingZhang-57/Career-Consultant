from requirement_analysis import analyse_requirement


def test_extracts_skill_year_scale_and_industry_constraints():
    analysis = analyse_requirement(
        "5+ years of production PyTorch experience in healthcare; "
        "experience with Docker at scale."
    )

    assert analysis["canonical_skills"] == ["docker", "pytorch"]
    assert analysis["years_constraints"][0]["minimum"] == 5
    assert analysis["scale_constraints"] == ["large_scale", "production"]
    assert analysis["industry_constraints"] == ["healthcare"]
    assert len(analysis["material_criteria"]) >= 2
