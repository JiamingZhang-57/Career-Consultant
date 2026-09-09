from evaluation import evaluate_predictions


def test_calculates_labelled_evaluation_metrics():
    metrics = evaluate_predictions(
        [
            {"expected": "strong_match", "predicted": "strong_match"},
            {"expected": "partial_match", "predicted": "strong_match"},
            {
                "expected": "not_evidenced_in_resume",
                "predicted": "not_evidenced_in_resume",
            },
        ]
    )

    assert metrics["case_count"] == 3
    assert metrics["accuracy"] == 0.667
    assert metrics["per_class"]["strong_match"]["precision"] == 0.5
