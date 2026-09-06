from uuid import uuid4

from job_chunking import (
    build_job_requirements,
    split_job_sections,
)
from job_ingestion import (
    JobPageError,
    extract_job_content,
    fetch_job_html,
)
from vector_store import (
    EMBEDDING_MODEL_NAME,
    add_chunks,
)


async def ingest_job_url(url: str) -> dict:
    final_url, html = await fetch_job_html(url)
    job = extract_job_content(html)

    if len(job["text"]) < 200:
        raise JobPageError(
            "Unable to extract a job description from this URL."
        )

    sections = split_job_sections(job["text"])

    requirements = build_job_requirements(
        sections
    )

    if not requirements:
        raise JobPageError(
            "The job page was retrieved, but no job requirements "
            "could be identified."
        )

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
                "requirement_id": requirement[
                    "requirement_id"
                ],
                "requirement_type": requirement[
                    "requirement_type"
                ],
                "category": requirement["category"],
                "source_text": requirement["source_text"],
            }
        )

    add_chunks(
        ids=ids,
        texts=texts,
        metadatas=metadatas,
    )

    return {
        "job_id": job_id,
        "source_url": final_url,
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "employment_type": job["employment_type"],
        "extraction_method": job["extraction_method"],
        "section_count": len(sections),
        "requirement_count": len(requirements),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "sections": sections,
        "requirements": requirements,
    }