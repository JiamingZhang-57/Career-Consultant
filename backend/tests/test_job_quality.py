from job_quality import assess_job_extraction


def test_rejects_job_without_required_requirements():
    quality = assess_job_extraction(
        job={
            "title": "ML Engineer",
            "company": "Example",
            "text": "x" * 1200,
            "extraction_method": "json_ld",
        },
        sections=[
            {
                "use_for_matching": True,
            }
        ],
        requirements=[
            {
                "requirement_type": "preferred",
            }
        ],
    )

    assert quality["status"] == "rejected"
    assert quality["required_requirement_count"] == 0
    assert "No required requirement was identified." in quality["issues"]


def test_accepts_complete_job_extraction():
    quality = assess_job_extraction(
        job={
            "title": "ML Engineer",
            "company": "Example",
            "text": "x" * 1200,
            "extraction_method": "ashby_public_api",
        },
        sections=[
            {"use_for_matching": True},
            {"use_for_matching": True},
        ],
        requirements=[
            {"requirement_type": "required"}
            for _ in range(8)
        ],
    )

    assert quality["status"] == "good"
    assert quality["score"] == 100
