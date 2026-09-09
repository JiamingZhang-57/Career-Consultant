from job_platforms import detect_job_platform


def test_detects_supported_job_platform_urls():
    cases = {
        "https://jobs.ashbyhq.com/acme/ashby-id?utm_source=test": (
            "ashby",
            "acme",
            "ashby-id",
            "global",
        ),
        "https://jobs.lever.co/acme/lever-id": (
            "lever",
            "acme",
            "lever-id",
            "global",
        ),
        "https://jobs.eu.lever.co/acme/lever-id": (
            "lever",
            "acme",
            "lever-id",
            "eu",
        ),
        "https://boards.greenhouse.io/acme/jobs/12345": (
            "greenhouse",
            "acme",
            "12345",
            "global",
        ),
    }

    for url, expected in cases.items():
        route = detect_job_platform(url)
        assert (
            route.platform,
            route.board_name,
            route.job_id,
            route.region,
        ) == expected


def test_uses_generic_extractor_for_unknown_platform():
    route = detect_job_platform(
        "https://careers.example.com/jobs/ml-engineer"
    )

    assert route.platform == "generic"
