from copy import deepcopy
from threading import Lock


_analysis_cache: dict[
    tuple[str, str],
    dict,
] = {}

_cache_lock = Lock()


def save_analysis(analysis: dict) -> None:
    key = (
        analysis["resume_document_id"],
        analysis["job_id"],
    )

    with _cache_lock:
        _analysis_cache[key] = deepcopy(analysis)


def get_analysis(
    resume_document_id: str,
    job_id: str,
) -> dict | None:
    key = (
        resume_document_id,
        job_id,
    )

    with _cache_lock:
        analysis = _analysis_cache.get(key)

        if analysis is None:
            return None

        return deepcopy(analysis)