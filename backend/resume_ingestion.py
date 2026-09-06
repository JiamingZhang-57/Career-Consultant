from uuid import uuid4

from chunking import (
    build_resume_evidence_chunks,
    split_resume_sections,
)
from pdf_parser import parse_pdf
from vector_store import (
    EMBEDDING_MODEL_NAME,
    add_chunks,
)


def ingest_resume(
    filename: str,
    file_content: bytes,
) -> dict:
    parsed_document = parse_pdf(
        filename=filename,
        file_content=file_content,
    )

    sections = split_resume_sections(
        parsed_document["pages"]
    )

    chunks = build_resume_evidence_chunks(
        sections
    )

    # 姓名和联系方式不作为工作能力证据
    indexable_chunks = [
        chunk
        for chunk in chunks
        if chunk["use_for_matching"]
    ]

    if not indexable_chunks:
        raise ValueError(
            "No usable resume evidence was found."
        )

    document_id = str(uuid4())

    ids = [
        f"{document_id}_{chunk['chunk_id']}"
        for chunk in indexable_chunks
    ]

    # retrieval_text 用于生成 embedding
    texts = [
        chunk["retrieval_text"]
        for chunk in indexable_chunks
    ]

    metadatas = [
        {
            "document_id": document_id,
            "document_type": "resume",
            "filename": filename,
            "chunk_id": chunk["chunk_id"],
            "section_id": chunk["section_id"],
            "section_type": chunk["section_type"],
            "heading": chunk["heading"],
            "page_numbers": ",".join(
                str(number)
                for number in chunk["page_numbers"]
            ),
            "source_text": chunk["source_text"],
            "use_for_matching": True,
        }
        for chunk in indexable_chunks
    ]

    add_chunks(
        ids=ids,
        texts=texts,
        metadatas=metadatas,
    )

    return {
        "document_id": document_id,
        "document_type": "resume",
        "filename": filename,
        "page_count": parsed_document["page_count"],
        "section_count": len(sections),
        "chunk_count": len(indexable_chunks),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "chunks": indexable_chunks,
    }