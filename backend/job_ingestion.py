import asyncio
import ipaddress
import json
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


MAX_HTML_SIZE = 2 * 1024 * 1024
MAX_REDIRECTS = 3


class JobPageError(Exception):
    pass


async def validate_public_url(url: str):
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise JobPageError("Only public HTTPS URLs are supported.")

    if not parsed.hostname:
        raise JobPageError("The URL does not contain a valid hostname.")

    hostname = parsed.hostname.lower()

    if hostname == "localhost" or hostname.endswith(".local"):
        raise JobPageError("Local network URLs are not allowed.")

    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            parsed.port or 443,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as error:
        raise JobPageError(
            "The website hostname could not be resolved."
        ) from error

    for address_info in addresses:
        raw_address = address_info[4][0].split("%")[0]
        address = ipaddress.ip_address(raw_address)

        if not address.is_global:
            raise JobPageError(
                "Private or local network addresses are not allowed."
            )


async def fetch_job_html(url: str) -> tuple[str, str]:
    current_url = url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 CareerIntelligenceAssistant/0.1"
        )
    }

    timeout = httpx.Timeout(
        timeout=10.0,
        connect=5.0,
    )

    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=False,
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await validate_public_url(current_url)

            try:
                response = await client.get(current_url)
            except httpx.HTTPError as error:
                raise JobPageError(
                    f"Unable to access the job page: {error}"
                ) from error

            if response.is_redirect:
                location = response.headers.get("location")

                if not location:
                    raise JobPageError(
                        "The website returned an invalid redirect."
                    )

                current_url = urljoin(current_url, location)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise JobPageError(
                    f"The website returned HTTP {response.status_code}."
                ) from error

            content_type = response.headers.get(
                "content-type",
                ""
            ).lower()

            if "text/html" not in content_type:
                raise JobPageError(
                    "The URL did not return an HTML webpage."
                )

            if len(response.content) > MAX_HTML_SIZE:
                raise JobPageError(
                    "The webpage is larger than the 2 MB limit."
                )

            return current_url, response.text

    raise JobPageError("The website returned too many redirects.")


def find_job_posting(value):
    if isinstance(value, dict):
        item_type = value.get("@type")

        if item_type == "JobPosting":
            return value

        if (
            isinstance(item_type, list)
            and "JobPosting" in item_type
        ):
            return value

        for nested_value in value.values():
            result = find_job_posting(nested_value)

            if result:
                return result

    if isinstance(value, list):
        for item in value:
            result = find_job_posting(item)

            if result:
                return result

    return None


def value_to_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return BeautifulSoup(
            value,
            "lxml",
        ).get_text("\n", strip=True)

    if isinstance(value, list):
        return "\n".join(
            part
            for item in value
            if (part := value_to_text(item))
        )

    if isinstance(value, dict):
        if value.get("name"):
            return value_to_text(value["name"])

        return " ".join(
            part
            for key, item in value.items()
            if not key.startswith("@")
            if (part := value_to_text(item))
        )

    return str(value)


def extract_job_content(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    job_posting = None

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        raw_json = script.string or script.get_text()

        try:
            structured_data = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue

        job_posting = find_job_posting(structured_data)

        if job_posting:
            break

    if job_posting:
        title = value_to_text(job_posting.get("title"))
        company = value_to_text(
            job_posting.get("hiringOrganization")
        )
        location = value_to_text(
            job_posting.get("jobLocation")
        )
        employment_type = value_to_text(
            job_posting.get("employmentType")
        )

        sections = [
            ("Title", title),
            ("Company", company),
            ("Location", location),
            ("Employment type", employment_type),
            (
                "Description",
                value_to_text(job_posting.get("description")),
            ),
            (
                "Responsibilities",
                value_to_text(
                    job_posting.get("responsibilities")
                ),
            ),
            (
                "Qualifications",
                value_to_text(
                    job_posting.get("qualifications")
                ),
            ),
            (
                "Skills",
                value_to_text(job_posting.get("skills")),
            ),
        ]

        text = "\n\n".join(
            f"{label}\n{value}"
            for label, value in sections
            if value
        )

        return {
            "title": title,
            "company": company,
            "location": location,
            "employment_type": employment_type,
            "text": text,
            "extraction_method": "job_posting_json_ld",
        }

    title_node = soup.find("h1") or soup.find("title")
    title = (
        title_node.get_text(" ", strip=True)
        if title_node
        else ""
    )

    company_meta = soup.find(
        "meta",
        attrs={"property": "og:site_name"},
    )
    company = (
        company_meta.get("content", "").strip()
        if company_meta
        else ""
    )

    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "form",
            "noscript",
            "svg",
        ]
    ):
        tag.decompose()

    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.body
    )

    text = (
        main_content.get_text("\n", strip=True)
        if main_content
        else ""
    )

    return {
        "title": title,
        "company": company,
        "location": "",
        "employment_type": "",
        "text": text,
        "extraction_method": "html_fallback",
    }