from scoring import calculate_job_score


def make_result(
    classification: str,
    requirement_type: str,
    guardrail_applied: bool = False,
) -> dict:
    return {
        "classification": classification,
        "requirement_type": requirement_type,
        "guardrail_applied": guardrail_applied,
    }


def test_calculates_weighted_scores():
    results = [
        make_result(
            "strong_match",
            "required",
        ),
        make_result(
            "partial_match",
            "required",
        ),
        make_result(
            "not_evidenced_in_resume",
            "preferred",
            guardrail_applied=True,
        ),
        make_result(
            "strong_match",
            "preferred",
        ),
    ]

    summary = calculate_job_score(results)

    assert summary["overall_score"] == 66.7
    assert summary["required_score"] == 75.0
    assert summary["preferred_score"] == 50.0

    assert summary["classification_counts"] == {
        "strong_match": 2,
        "partial_match": 1,
        "not_evidenced_in_resume": 1,
    }

    assert summary["pending_verification_count"] == 1
    assert summary["guardrail_count"] == 1


def test_returns_none_when_no_required_criteria():
    results = [
        make_result(
            "strong_match",
            "preferred",
        ),
        make_result(
            "partial_match",
            "preferred",
        ),
    ]

    summary = calculate_job_score(results)

    assert summary["overall_score"] == 75.0
    assert summary["required_score"] is None
    assert summary["preferred_score"] == 75.0


def test_handles_empty_results():
    summary = calculate_job_score([])

    assert summary["overall_score"] is None
    assert summary["required_score"] is None
    assert summary["preferred_score"] is None
    assert summary["pending_verification_count"] == 0
    assert summary["guardrail_count"] == 0