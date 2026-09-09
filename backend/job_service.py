from uuid import uuid4
import json

from job_chunking import (
    build_job_requirements,
    split_job_sections,
)
from job_adapters import extract_job_url
from job_ingestion import JobPageError
from job_quality import assess_job_extraction
from vector_store import (
    EMBEDDING_MODEL_NAME,
    add_chunks,
)


def prepare_job_content(final_url: str, job: dict) -> dict:
    sections = split_job_sections(job["text"])
    requirements = build_job_requirements(
        sections
    )
    quality = assess_job_extraction(
        job=job,
        sections=sections,
        requirements=requirements,
    )

    return {
        "source_url": final_url,
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "employment_type": job["employment_type"],
        "text": job["text"],
        "extraction_method": job["extraction_method"],
        "source_platform": job.get("source_platform", "generic"),
        "extraction_quality": quality,
        "sections": sections,
        "requirements": requirements,
    }


async def preview_job_url(url: str) -> dict:
    final_url, job = await extract_job_url(url)
    return prepare_job_content(final_url, job)


def ingest_job_content(job: dict) -> dict:
    prepared = prepare_job_content(job["source_url"], job)
    quality = prepared["extraction_quality"]

    if quality["status"] == "rejected":
        reasons = " ".join(quality["issues"])
        raise JobPageError(
            "Job extraction quality check failed. "
            f"{reasons} Please review the URL or edit the extracted "
            "job details manually."
        )

    final_url = prepared["source_url"]
    sections = prepared["sections"]
    requirements = prepared["requirements"]

    job_id = str(uuid4())

    ids = []
    texts = []
    metadatas = []

    # Section chunks support future conversational retrieval.
    for section in sections:
        ids.append(
            f"{job_id}_{section['section_id']}"
        )

        texts.append(
            f"Job title: {job['title']}\n"
            f"Job section: {section['section_type']}\n"
            f"{section['text']}"
        )

        metadatas.append(
            {
                "document_id": job_id,
                "document_type": "job",
                "record_type": "job_section",
                "source_url": final_url,
                "title": job["title"],
                "company": job["company"],
                "source_platform": job["source_platform"],
                "extraction_method": job["extraction_method"],
                "section_id": section["section_id"],
                "section_type": section["section_type"],
                "source_text": section["text"],
                "use_for_matching": section[
                    "use_for_matching"
                ],
            }
        )

    # Atomic requirements support resume-to-job matching.
    for requirement in requirements:
        ids.append(
            f"{job_id}_{requirement['requirement_id']}"
        )

        texts.append(
            f"Job title: {job['title']}\n"
            f"{requirement['retrieval_text']}"
        )

        metadatas.append(
            {
                "document_id": job_id,
                "document_type": "job",
                "record_type": "job_requirement",
                "source_url": final_url,
                "title": job["title"],
                "company": job["company"],
                "source_platform": job["source_platform"],
                "extraction_method": job["extraction_method"],
                "requirement_id": requirement[
                    "requirement_id"
                ],
                "requirement_type": requirement[
                    "requirement_type"
                ],
                "category": requirement["category"],
                "source_text": requirement["source_text"],
                "canonical_skills": ",".join(
                    requirement["canonical_skills"]
                ),
                "years_constraints": json.dumps(
                    requirement["years_constraints"]
                ),
                "scale_constraints": ",".join(
                    requirement["scale_constraints"]
                ),
                "industry_constraints": ",".join(
                    requirement["industry_constraints"]
                ),
            }
        )

    add_chunks(
        ids=ids,
        texts=texts,
        metadatas=metadatas,
    )

    return {
        "job_id": job_id,
        "source_url": prepared["source_url"],
        "title": prepared["title"],
        "company": prepared["company"],
        "location": prepared["location"],
        "employment_type": prepared["employment_type"],
        "extraction_method": prepared["extraction_method"],
        "source_platform": prepared["source_platform"],
        "extraction_quality": quality,
        "section_count": len(sections),
        "requirement_count": len(requirements),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "sections": sections,
        "requirements": requirements,
    }


async def ingest_job_url(url: str) -> dict:
    prepared = await preview_job_url(url)
    return ingest_job_content(prepared)
