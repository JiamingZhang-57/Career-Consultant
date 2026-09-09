from collections import Counter


LABELS = (
    "strong_match",
    "partial_match",
    "not_evidenced_in_resume",
)


def evaluate_predictions(cases: list[dict]) -> dict:
    """Calculate metrics for cases labelled by a human reviewer."""
    if not cases:
        return {
            "case_count": 0,
            "accuracy": None,
            "per_class": {},
            "confusion_matrix": {},
        }

    correct = sum(
        case["expected"] == case["predicted"] for case in cases
    )
    confusion = Counter(
        (case["expected"], case["predicted"]) for case in cases
    )
    per_class = {}

    for label in LABELS:
        true_positive = confusion[(label, label)]
        predicted_count = sum(confusion[(actual, label)] for actual in LABELS)
        expected_count = sum(confusion[(label, predicted)] for predicted in LABELS)
        precision = (
            true_positive / predicted_count if predicted_count else None
        )
        recall = true_positive / expected_count if expected_count else None
        per_class[label] = {
            "precision": round(precision, 3) if precision is not None else None,
            "recall": round(recall, 3) if recall is not None else None,
            "support": expected_count,
        }

    return {
        "case_count": len(cases),
        "accuracy": round(correct / len(cases), 3),
        "per_class": per_class,
        "confusion_matrix": {
            expected: {
                predicted: confusion[(expected, predicted)]
                for predicted in LABELS
            }
            for expected in LABELS
        },
    }
