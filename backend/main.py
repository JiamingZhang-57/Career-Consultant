from uuid import uuid4
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pdf_parser import PdfParsingError, parse_pdf
from chunking import split_resume_sections
from job_ingestion import JobPageError, extract_job_content, fetch_job_html
from vector_store import EMBEDDING_MODEL_NAME, add_chunks, search_chunks
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

@app.post("/documents/index")
async def index_document(file: UploadFile = File(...), document_type: str = Form("resume")):
    if document_type not in {"resume", "job"}:
        raise HTTPException(status_code=400, detail="document_type must be either 'resume' or 'job'.")
    parsed_document = await parse_document(file)
    chunks = parsed_document["chunks"]
    if not chunks:
        raise HTTPException(status_code=400, detail="No text could be extracted from this document.")

    document_id = str(uuid4())
    texts = [chunk["text"] for chunk in chunks]
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()
    ids = [f"{document_id}_{chunk['chunk_id']}"for chunk in chunks]
    metadatas = [
        { "document_id": document_id, "document_type": document_type, "filename": parsed_document["filename"], "chunk_id": chunk["chunk_id"],
        } for chunk in chunks
                ]

    add_chunks(ids=ids, texts=texts, metadatas=metadatas)

    return {
        "document_id": document_id,
        "filename": parsed_document["filename"],
        "document_type": document_type,
        "chunk_count": len(chunks),
        "embedding_model": EMBEDDING_MODEL_NAME
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


@app.post("/jobs/from-url/preview")
async def preview_job_from_url(
    request: JobUrlRequest,
):
    try:
        final_url, html = await fetch_job_html(request.url)
        job = extract_job_content(html)
    except JobPageError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    if len(job["text"]) < 200:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unable to extract a job description from this URL. "
                "Please provide a public company career-page URL."
            ),
        )

    chunks = chunk_text(job["text"])

    return {
        "source_url": final_url,
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "employment_type": job["employment_type"],
        "extraction_method": job["extraction_method"],
        "character_count": len(job["text"]),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }

@app.post("/documents/resume-structure", include_in_schema=False)
async def preview_resume_structure(
    file: UploadFile = File(...),
):
    parsed_document = await parse_document(file)

    sections = split_resume_sections(
        parsed_document["pages"]
    )

    return {
        "filename": parsed_document["filename"],
        "page_count": parsed_document["page_count"],
        "section_count": len(sections),
        "sections": sections,
    }