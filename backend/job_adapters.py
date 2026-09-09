from urllib.parse import quote

from job_ingestion import (
    JobPageError,
    extract_job_content,
    fetch_job_html,
    fetch_public_json,
    value_to_text,
)
from job_platforms import JobPlatformRoute, detect_job_platform


def _humanize_slug(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def _join_sections(sections: list[tuple[str, str]]) -> str:
    return "\n\n".join(
        f"{heading}\n{body.strip()}"
        for heading, body in sections
        if body and body.strip()
    )


async def _extract_ashby(route: JobPlatformRoute) -> dict:
    if not route.board_name or not route.job_id:
        raise JobPageError("The Ashby job URL is incomplete.")

    board_name = quote(route.board_name, safe="")
    api_url = (
        "https://api.ashbyhq.com/posting-api/job-board/"
        f"{board_name}?includeCompensation=true"
    )
    _, payload = await fetch_public_json(api_url)

    jobs = payload.get("jobs")

    if not isinstance(jobs, list):
        raise JobPageError(
            "Ashby returned an unexpected job-board response."
        )

    selected_job = None

    for job in jobs:
        if not isinstance(job, dict):
            continue

        if str(job.get("id", "")) == route.job_id:
            selected_job = job
            break

        candidate_urls = {
            str(job.get("jobUrl", "")),
            str(job.get("applyUrl", "")),
        }

        if any(route.job_id in url for url in candidate_urls):
            selected_job = job
            break

    if selected_job is None:
        raise JobPageError(
            "The requested Ashby job was not found on its public board."
        )

    description = value_to_text(
        selected_job.get("descriptionPlain")
        or selected_job.get("descriptionHtml")
        or selected_job.get("description")
    )
    company = value_to_text(
        payload.get("organizationName")
        or payload.get("name")
    )
    warnings = []

    if not company:
        company = _humanize_slug(route.board_name)
        warnings.append(
            "Company name was inferred from the Ashby board name."
        )

    text = _join_sections(
        [
            ("Description", description),
            ("Department", value_to_text(selected_job.get("department"))),
            ("Team", value_to_text(selected_job.get("team"))),
        ]
    )

    return {
        "title": value_to_text(selected_job.get("title")),
        "company": company,
        "location": value_to_text(selected_job.get("location")),
        "employment_type": value_to_text(
            selected_job.get("employmentType")
        ),
        "text": text,
        "extraction_method": "ashby_public_api",
        "source_platform": "ashby",
        "extraction_warnings": warnings,
    }


async def _extract_lever(route: JobPlatformRoute) -> dict:
    if not route.board_name or not route.job_id:
        raise JobPageError("The Lever job URL is incomplete.")

    api_host = (
        "api.eu.lever.co"
        if route.region == "eu"
        else "api.lever.co"
    )
    board_name = quote(route.board_name, safe="")
    job_id = quote(route.job_id, safe="")
    api_url = (
        f"https://{api_host}/v0/postings/"
        f"{board_name}/{job_id}"
    )
    _, payload = await fetch_public_json(api_url)

    categories = payload.get("categories")
    if not isinstance(categories, dict):
        categories = {}

    sections: list[tuple[str, str]] = []
    description = value_to_text(
        payload.get("descriptionPlain")
        or payload.get("description")
    )

    if description:
        sections.append(("Description", description))

    lever_lists = payload.get("lists")

    if isinstance(lever_lists, list):
        for item in lever_lists:
            if not isinstance(item, dict):
                continue

            heading = value_to_text(item.get("text")) or "Details"
            body = value_to_text(item.get("content"))

            if body:
                sections.append((heading, body))

    additional = value_to_text(
        payload.get("additionalPlain")
        or payload.get("additional")
    )

    if additional:
        sections.append(("Additional information", additional))

    return {
        "title": value_to_text(payload.get("text")),
        "company": _humanize_slug(route.board_name),
        "location": value_to_text(categories.get("location")),
        "employment_type": value_to_text(
            categories.get("commitment")
        ),
        "text": _join_sections(sections),
        "extraction_method": "lever_postings_api",
        "source_platform": "lever",
        "extraction_warnings": [
            "Company name was inferred from the Lever site name."
        ],
    }


async def _extract_greenhouse(route: JobPlatformRoute) -> dict:
    if not route.board_name or not route.job_id:
        raise JobPageError("The Greenhouse job URL is incomplete.")

    board_name = quote(route.board_name, safe="")
    job_id = quote(route.job_id, safe="")
    # Greenhouse exposes its public Job Board API through one documented
    # host, including jobs whose public board page uses the EU hostname.
    api_host = "boards-api.greenhouse.io"
    job_url = (
        f"https://{api_host}/v1/boards/"
        f"{board_name}/jobs/{job_id}"
    )
    board_url = f"https://{api_host}/v1/boards/{board_name}"

    _, payload = await fetch_public_json(job_url)
    company = _humanize_slug(route.board_name)
    warnings = [
        "Company name was inferred from the Greenhouse board name."
    ]

    try:
        _, board_payload = await fetch_public_json(board_url)
        board_company = value_to_text(board_payload.get("name"))

        if board_company:
            company = board_company
            warnings = []
    except JobPageError:
        # The job itself remains usable if board metadata is unavailable.
        pass

    location = payload.get("location")

    if isinstance(location, dict):
        location_text = value_to_text(location.get("name"))
    else:
        location_text = value_to_text(location)

    return {
        "title": value_to_text(payload.get("title")),
        "company": company,
        "location": location_text,
        "employment_type": "",
        "text": _join_sections(
            [
                (
                    "Description",
                    value_to_text(payload.get("content")),
                )
            ]
        ),
        "extraction_method": "greenhouse_job_board_api",
        "source_platform": "greenhouse",
        "extraction_warnings": warnings,
    }


async def extract_job_url(url: str) -> tuple[str, dict]:
    """Use an official platform API where possible, then HTML."""
    route = detect_job_platform(url)
    adapter_error = None

    try:
        if route.platform == "ashby":
            return url, await _extract_ashby(route)

        if route.platform == "lever":
            return url, await _extract_lever(route)

        if route.platform == "greenhouse":
            return url, await _extract_greenhouse(route)
    except JobPageError as error:
        adapter_error = str(error)

    final_url, html = await fetch_job_html(url)
    job = extract_job_content(html)
    job["source_platform"] = route.platform
    job["extraction_warnings"] = []

    if adapter_error:
        job["extraction_warnings"].append(
            "The platform API could not be used; HTML fallback was "
            f"applied. Reason: {adapter_error}"
        )

    return final_url, job
