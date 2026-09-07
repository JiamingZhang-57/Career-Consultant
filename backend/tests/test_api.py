from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "career-intelligence-api",
    }


def test_analysis_endpoint_saves_result(
    monkeypatch,
):
    fake_analysis = {
        "resume_document_id": "resume-001",
        "job_id": "job-001",
        "requirement_count": 0,
        "classifier_model": "test-model",
        "score_summary": {},
        "results": [],
    }

    saved_analyses = []

    def fake_build_evidence_matrix(
        resume_document_id: str,
        job_id: str,
        top_k: int,
    ):
        assert resume_document_id == "resume-001"
        assert job_id == "job-001"
        assert top_k == 3

        return fake_analysis

    def fake_save_analysis(analysis: dict):
        saved_analyses.append(analysis)

    monkeypatch.setattr(
        main,
        "build_evidence_matrix",
        fake_build_evidence_matrix,
    )

    monkeypatch.setattr(
        main,
        "save_analysis",
        fake_save_analysis,
    )

    response = client.post(
        "/analyses",
        json={
            "resume_document_id": "resume-001",
            "job_id": "job-001",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    assert response.json() == fake_analysis
    assert saved_analyses == [fake_analysis]


def test_analysis_endpoint_returns_404(
    monkeypatch,
):
    def fake_build_evidence_matrix(**kwargs):
        raise ValueError(
            "Resume document was not found."
        )

    monkeypatch.setattr(
        main,
        "build_evidence_matrix",
        fake_build_evidence_matrix,
    )

    response = client.post(
        "/analyses",
        json={
            "resume_document_id": "missing-resume",
            "job_id": "job-001",
            "top_k": 3,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": (
            "Resume document was not found."
        )
    }


def test_chat_endpoint_returns_answer(
    monkeypatch,
):
    expected_response = {
        "answer": "The resume provides relevant evidence.",
        "sources": [
            {
                "source_id": "resume:chunk-001",
                "source_type": "resume",
                "section_type": "experience",
                "text": "Built production ML systems.",
            }
        ],
        "model": "test-model",
        "guardrail_applied": False,
    }

    def fake_answer_career_question(
        resume_document_id: str,
        job_id: str,
        question: str,
        history: list[dict],
    ):
        assert resume_document_id == "resume-001"
        assert job_id == "job-001"
        assert question == "How does my experience align?"
        assert history == []

        return expected_response

    monkeypatch.setattr(
        main,
        "answer_career_question",
        fake_answer_career_question,
    )

    response = client.post(
        "/chat",
        json={
            "resume_document_id": "resume-001",
            "job_id": "job-001",
            "question": (
                "How does my experience align?"
            ),
            "history": [],
        },
    )

    assert response.status_code == 200
    assert response.json() == expected_response


def test_chat_endpoint_returns_409_without_analysis(
    monkeypatch,
):
    def fake_answer_career_question(**kwargs):
        raise ValueError(
            "No cached analysis was found."
        )

    monkeypatch.setattr(
        main,
        "answer_career_question",
        fake_answer_career_question,
    )

    response = client.post(
        "/chat",
        json={
            "resume_document_id": "resume-001",
            "job_id": "job-001",
            "question": "What are my gaps?",
            "history": [],
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "No cached analysis was found."
    }


def test_chat_rejects_empty_question():
    response = client.post(
        "/chat",
        json={
            "resume_document_id": "resume-001",
            "job_id": "job-001",
            "question": "",
            "history": [],
        },
    )

    assert response.status_code == 422