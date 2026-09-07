CLASSIFICATION_VALUES = {
    "strong_match": 1.0,
    "partial_match": 0.5,
    "not_evidenced_in_resume": 0.0,
}

REQUIREMENT_WEIGHTS = {
    "required": 2.0,
    "preferred": 1.0,
}


def percentage(
    earned: float,
    possible: float,
) -> float | None:
    if possible == 0:
        return None

    return round(
        earned / possible * 100,
        1,
    )


def calculate_job_score(
    results: list[dict],
) -> dict:
    total_earned = 0.0
    total_possible = 0.0

    required_earned = 0.0
    required_possible = 0.0

    preferred_earned = 0.0
    preferred_possible = 0.0

    classification_counts = {
        "strong_match": 0,
        "partial_match": 0,
        "not_evidenced_in_resume": 0,
    }

    for result in results:
        classification = result["classification"]
        requirement_type = result["requirement_type"]

        match_value = CLASSIFICATION_VALUES[
            classification
        ]

        requirement_weight = REQUIREMENT_WEIGHTS.get(
            requirement_type,
            1.0,
        )

        earned = match_value * requirement_weight

        total_earned += earned
        total_possible += requirement_weight

        classification_counts[classification] += 1

        if requirement_type == "required":
            required_earned += earned
            required_possible += requirement_weight

        elif requirement_type == "preferred":
            preferred_earned += earned
            preferred_possible += requirement_weight

    return {
        "overall_score": percentage(
            total_earned,
            total_possible,
        ),
        "required_score": percentage(
            required_earned,
            required_possible,
        ),
        "preferred_score": percentage(
            preferred_earned,
            preferred_possible,
        ),
        "classification_counts": classification_counts,
        "pending_verification_count": (
            classification_counts[
                "not_evidenced_in_resume"
            ]
        ),
        "guardrail_count": sum(
            1
            for result in results
            if result.get("guardrail_applied", False)
        ),
        "scoring_policy": {
            "classification_values": (
                CLASSIFICATION_VALUES
            ),
            "requirement_weights": (
                REQUIREMENT_WEIGHTS
            ),
            "confidence_used_in_score": False,
        },
    }