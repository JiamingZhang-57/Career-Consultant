import json
from types import SimpleNamespace

import pytest

import gemini_classifier


class FakeModels:
    def __init__(self, payload: dict):
        self.payload = payload

    def generate_content(self, **kwargs):
        return SimpleNamespace(
            text=json.dumps(self.payload)
        )


class FakeClient:
    def __init__(self, payload: dict):
        self.models = FakeModels(payload)


def configure_fake_gemini(
    monkeypatch,
    payload: dict,
):
    monkeypatch.setattr(
        gemini_classifier,
        "get_gemini_client",
        lambda: FakeClient(payload),
    )

    monkeypatch.setattr(
        gemini_classifier,
        "get_settings",
        lambda: SimpleNamespace(
            gemini_model="test-model"
        ),
    )


def make_requirement() -> dict:
    return {
        "requirement_id": "requirement_001",
        "requirement": (
            "Experience building production ML systems."
        ),
        "requirement_type": "required",
        "evidence": [
            {
                "chunk_id": "resume_chunk_001",
                "section_type": "experience",
                "source_text": (
                    "Built and deployed a production "
                    "computer vision pipeline."
                ),
            }
        ],
    }


def test_accepts_valid_supporting_citation(
    monkeypatch,
):
    configure_fake_gemini(
        monkeypatch,
        {
            "decisions": [
                {
                    "requirement_id": (
                        "requirement_001"
                    ),
                    "classification": (
                        "strong_match"
                    ),
                    "confidence": 0.9,
                    "supporting_chunk_ids": [
                        "resume_chunk_001"
                    ],
                    "explanation": (
                        "The resume provides direct "
                        "production deployment evidence."
                    ),
                }
            ]
        },
    )

    result = (
        gemini_classifier.classify_requirements(
            [make_requirement()]
        )
    )

    decision = result["decisions"][
        "requirement_001"
    ]

    assert (
        decision["classification"]
        == "strong_match"
    )
    assert decision["supporting_chunk_ids"] == [
        "resume_chunk_001"
    ]
    assert decision["guardrail_applied"] is False


def test_rejects_invalid_supporting_citation(
    monkeypatch,
):
    configure_fake_gemini(
        monkeypatch,
        {
            "decisions": [
                {
                    "requirement_id": (
                        "requirement_001"
                    ),
                    "classification": (
                        "strong_match"
                    ),
                    "confidence": 0.95,
                    "supporting_chunk_ids": [
                        "invented_chunk"
                    ],
                    "explanation": (
                        "Unsupported model claim."
                    ),
                }
            ]
        },
    )

    result = (
        gemini_classifier.classify_requirements(
            [make_requirement()]
        )
    )

    decision = result["decisions"][
        "requirement_001"
    ]

    assert (
        decision["classification"]
        == "not_evidenced_in_resume"
    )
    assert decision["confidence"] == 0.0
    assert decision["supporting_chunk_ids"] == []
    assert decision["guardrail_applied"] is True


def test_rejects_incomplete_model_output(
    monkeypatch,
):
    configure_fake_gemini(
        monkeypatch,
        {
            "decisions": [],
        },
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Gemini did not classify "
            "every requirement"
        ),
    ):
        gemini_classifier.classify_requirements(
            [make_requirement()]
        )