import analysis_cache


def test_saves_and_retrieves_analysis(
    monkeypatch,
):
    monkeypatch.setattr(
        analysis_cache,
        "_analysis_cache",
        {},
    )

    analysis = {
        "resume_document_id": "resume-001",
        "job_id": "job-001",
        "results": [],
    }

    analysis_cache.save_analysis(analysis)

    retrieved = analysis_cache.get_analysis(
        resume_document_id="resume-001",
        job_id="job-001",
    )

    assert retrieved == analysis


def test_returns_independent_copy(
    monkeypatch,
):
    monkeypatch.setattr(
        analysis_cache,
        "_analysis_cache",
        {},
    )

    analysis = {
        "resume_document_id": "resume-001",
        "job_id": "job-001",
        "results": [
            {
                "classification": "strong_match",
            }
        ],
    }

    analysis_cache.save_analysis(analysis)

    first_result = analysis_cache.get_analysis(
        resume_document_id="resume-001",
        job_id="job-001",
    )

    first_result["results"][0][
        "classification"
    ] = "changed"

    second_result = analysis_cache.get_analysis(
        resume_document_id="resume-001",
        job_id="job-001",
    )

    assert (
        second_result["results"][0][
            "classification"
        ]
        == "strong_match"
    )