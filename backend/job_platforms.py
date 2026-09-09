from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qs, urlparse


JobPlatform = Literal[
    "ashby",
    "lever",
    "greenhouse",
    "generic",
]


@dataclass(frozen=True)
class JobPlatformRoute:
    platform: JobPlatform
    board_name: str | None = None
    job_id: str | None = None
    region: str = "global"


def detect_job_platform(url: str) -> JobPlatformRoute:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    path_parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if hostname == "jobs.ashbyhq.com" and len(path_parts) >= 2:
        return JobPlatformRoute(
            platform="ashby",
            board_name=path_parts[0],
            job_id=path_parts[1],
        )

    if hostname in {
        "jobs.lever.co",
        "jobs.eu.lever.co",
    } and len(path_parts) >= 2:
        return JobPlatformRoute(
            platform="lever",
            board_name=path_parts[0],
            job_id=path_parts[1],
            region=(
                "eu"
                if hostname == "jobs.eu.lever.co"
                else "global"
            ),
        )

    greenhouse_hosts = {
        "boards.greenhouse.io",
        "boards.eu.greenhouse.io",
        "job-boards.greenhouse.io",
    }

    if hostname in greenhouse_hosts:
        query = parse_qs(parsed.query)

        if "jobs" in path_parts:
            jobs_index = path_parts.index("jobs")

            if jobs_index > 0 and jobs_index + 1 < len(path_parts):
                return JobPlatformRoute(
                    platform="greenhouse",
                    board_name=path_parts[0],
                    job_id=path_parts[jobs_index + 1],
                    region=(
                        "eu"
                        if ".eu." in hostname
                        else "global"
                    ),
                )

        # Some embedded Greenhouse URLs expose only a job token. Without
        # the board token the public job API cannot be addressed reliably,
        # so the generic page extractor remains the safe fallback.
        if "token" in query:
            return JobPlatformRoute(
                platform="generic",
                job_id=query["token"][0],
            )

    return JobPlatformRoute(platform="generic")
