
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pdf_parser import PdfParsingError, parse_pdf
from chunking import build_resume_evidence_chunks,split_resume_sections
from job_ingestion import JobPageError
from job_service import ingest_job_url
from vector_store import search_chunks
from resume_ingestion import ingest_resume
from schemas import EvidenceRequest, JobUrlRequest, SearchRequest


app = FastAPI(title="Career Intelligence API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000" ], allow_credentials=True, allow_methods=["*"],  allow_headers=["*"])

def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150):
    """
    Chunking the texts for the information Retrieval
    """
    paragraphs = [paragraph.strip() for paragraph in text.split("\n") if paragraph.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        candidate = (f"{current}\n{paragraph}".strip() if current else paragraph )
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            overlap_text = current[-overlap:] if current else ""
            current = f"{overlap_text}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return [{ "chunk_id": f"chunk_{index + 1:03d}", "text": chunk, "character_count": len(chunk) } for index, chunk in enumerate(chunks)]

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "career-intelligence-api"}

@app.post(
    "/resumes",
    tags=["Resumes"],
)
async def upload_resume(
    file: UploadFile = File(...),
):
    filename = file.filename or "uploaded-resume.pdf"
    file_content = await file.read()

    try:
        result = ingest_resume(
            filename=filename,
            file_content=file_content,
        )
    except PdfParsingError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return result



@app.post(
    "/documents/parse",
    include_in_schema=False,
)
async def parse_document(
    file: UploadFile = File(...),
):
    filename = file.filename or "uploaded-file"
    file_content = await file.read()

    try:
        parsed_document = parse_pdf(
            filename=filename,
            file_content=file_content,
        )
    except PdfParsingError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=str(error),
        ) from error

    chunks = chunk_text(parsed_document["text"])

    return {
        **parsed_document,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }



@app.post("/search", include_in_schema=False)
def search_documents(request: SearchRequest):
    filters = []

    if request.document_id:
        filters.append(
            {"document_id": request.document_id}
        )

    if request.document_type:
        filters.append(
            {"document_type": request.document_type}
        )

    where = None

    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}

    matches = search_chunks(
        query=request.query,
        top_k=request.top_k,
        where=where,
    )

    return {
        "query": request.query,
        "result_count": len(matches),
        "matches": matches,
    }

@app.post("/requirements/evidence", include_in_schema=False)
def retrieve_requirement_evidence(request: EvidenceRequest):
    search_request = SearchRequest(
        query=request.requirement,
        top_k=request.top_k,
        document_id=request.resume_document_id,
        document_type="resume")
    search_results = search_documents(search_request)
    return {"requirement": request.requirement, "resume_document_id": request.resume_document_id, "evidence": search_results["matches"]}


@app.post(
    "/jobs",
    tags=["Jobs"],
)
async def create_job(
    request: JobUrlRequest,
):
    try:
        return await ingest_job_url(
            request.url
        )
    except JobPageError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

@app.post("/documents/resume-structure", include_in_schema=False)
async def preview_resume_structure(
    file: UploadFile = File(...),
):
    parsed_document = await parse_document(file)

    sections = split_resume_sections(parsed_document["pages"])
    evidence_chunks = build_resume_evidence_chunks(sections)
    return {
        "filename": parsed_document["filename"],
        "page_count": parsed_document["page_count"],
        "section_count": len(sections),
        "sections": sections,
        "evidence_chunk_count": len(evidence_chunks),
        "evidence_chunks": evidence_chunks,
    }