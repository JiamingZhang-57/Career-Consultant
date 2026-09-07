from vector_store import get_chunks, search_chunks
from gemini_classifier import classify_requirements
from scoring import calculate_job_score

def build_evidence_matrix(
    resume_document_id: str,
    job_id: str,
    top_k: int = 3,
) -> dict:
    resume_filter = {
        "$and": [
            {
                "document_id": resume_document_id,
            },
            {
                "document_type": "resume",
            },
        ]
    }

    resume_chunks = get_chunks(
        where=resume_filter
    )

    if not resume_chunks:
        raise ValueError(
            "Resume document was not found."
        )

    requirement_filter = {
        "$and": [
            {
                "document_id": job_id,
            },
            {
                "document_type": "job",
            },
            {
                "record_type": "job_requirement",
            },
        ]
    }

    requirement_records = get_chunks(
        where=requirement_filter
    )

    if not requirement_records:
        raise ValueError(
            "Job requirements were not found."
        )

    requirement_records.sort(
        key=lambda record: record["metadata"].get(
            "requirement_id",
            "",
        )
    )

    results = []

    for record in requirement_records:
        requirement_metadata = record["metadata"]
        requirement_text = requirement_metadata[
            "source_text"
        ]

        matches = search_chunks(
            query=requirement_text,
            top_k=top_k,
            where=resume_filter,
        )

        evidence = []

        for match in matches:
            metadata = match["metadata"]

            evidence.append(
                {
                    "chunk_id": metadata.get(
                        "chunk_id"
                    ),
                    "section_type": metadata.get(
                        "section_type"
                    ),
                    "source_text": metadata.get(
                        "source_text",
                        match["text"],
                    ),
                    "distance": round(
                        match["distance"],
                        4,
                    ),
                    "retrieval_similarity": round(
                        match["retrieval_similarity"],
                        4,
                    ),
                }
            )

        results.append(
            {
                "requirement_id": requirement_metadata[
                    "requirement_id"
                ],
                "requirement_type": requirement_metadata[
                    "requirement_type"
                ],
                "category": requirement_metadata[
                    "category"
                ],
                "requirement": requirement_text,
                "evidence": evidence,
            }
        )

        classification_batch = classify_requirements(
            results
        )

        decisions = classification_batch["decisions"]

        for result in results:
            decision = decisions[result["requirement_id"]]

            result["classification"] = decision[
                "classification"
            ]
            result["confidence"] = decision[
                "confidence"
            ]
            result["supporting_chunk_ids"] = decision[
                "supporting_chunk_ids"
            ]
            result["explanation"] = decision[
                "explanation"
            ]
            result["guardrail_applied"] = decision[
                "guardrail_applied"
            ]
    score_summary = calculate_job_score(
        results
    )
    return {
        "resume_document_id": resume_document_id,
        "job_id": job_id,
        "requirement_count": len(results),
        "classifier_model": classification_batch["model"],
        "score_summary": score_summary,
        "results": results,
    }