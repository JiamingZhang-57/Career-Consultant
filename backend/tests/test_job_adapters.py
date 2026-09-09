import asyncio

import job_adapters


def test_ashby_adapter_normalises_public_api_payload(monkeypatch):
    async def fake_fetch_public_json(url: str):
        assert "posting-api/job-board/acme" in url
        return url, {
            "organizationName": "Acme AI",
            "jobs": [
                {
                    "id": "job-id",
                    "title": "ML Engineer",
                    "location": "London",
                    "employmentType": "Full-time",
                    "descriptionPlain": (
                        "Requirements\n- Strong Python experience.\n"
                        "Responsibilities\n- Build production ML systems."
                    ),
                }
            ],
        }

    monkeypatch.setattr(
        job_adapters,
        "fetch_public_json",
        fake_fetch_public_json,
    )

    _, job = asyncio.run(
        job_adapters.extract_job_url(
            "https://jobs.ashbyhq.com/acme/job-id"
        )
    )

    assert job["title"] == "ML Engineer"
    assert job["company"] == "Acme AI"
    assert job["source_platform"] == "ashby"
    assert job["extraction_method"] == "ashby_public_api"


def test_lever_adapter_preserves_list_headings(monkeypatch):
    async def fake_fetch_public_json(url: str):
        return url, {
            "text": "Computer Vision Engineer",
            "categories": {
                "location": "Cambridge",
                "commitment": "Full-time",
            },
            "descriptionPlain": "Role overview text.",
            "lists": [
                {
                    "text": "What you will do",
                    "content": "<li>Build vision models.</li>",
                },
                {
                    "text": "Requirements",
                    "content": "<li>Strong Python experience.</li>",
                },
            ],
        }

    monkeypatch.setattr(
        job_adapters,
        "fetch_public_json",
        fake_fetch_public_json,
    )

    _, job = asyncio.run(
        job_adapters.extract_job_url(
            "https://jobs.lever.co/acme/job-id"
        )
    )

    assert "What you will do\nBuild vision models." in job["text"]
    assert "Requirements\nStrong Python experience." in job["text"]
    assert job["source_platform"] == "lever"
