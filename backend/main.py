from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel, Field
import chromadb
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
import pymupdf

app = FastAPI(title="Career Intelligence API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000" ], allow_credentials=True, allow_methods=["*"],  allow_headers=["*"])
MAX_FILE_SIZE = 10 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma"
CHROMA_PATH.mkdir(parents=True, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
chunks_collection = chroma_client.get_or_create_collection(name="document_chunks", metadata={"hnsw:space": "cosine"})
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer( "all-MiniLM-L6-v2")
    return _embedding_model

class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    document_id: str | None = None
    document_type: str | None = None

class EvidenceRequest(BaseModel):
    requirement: str = Field(min_length=1)
    resume_document_id: str | None = None
    top_k: int = Field(default=3, ge=1, le=10)

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

@app.post("/documents/parse")
async def parse_document(file: UploadFile = File(...)):
    filename = file.filename or "uploaded-file"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException( status_code=413, detail="File is too large. Maximum size is 10 MB.")
    if not file_content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file does not appear to be a valid PDF.")
    try:
        document = pymupdf.open(stream=file_content, filetype="pdf")
        pages = []
        for page_index in range(document.page_count):
            page_text = document[page_index].get_text("text").strip()
            pages.append({ "page_number": page_index + 1, "text": page_text})
        page_count = document.page_count
        document.close()
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {error}") from error
    full_text = "\n\n".join(page["text"] for page in pages if page["text"])
    chunks = chunk_text(full_text)
    return {
        "filename": filename,
        "page_count": page_count,
        "character_count": len(full_text),
        "text": full_text,
        "pages": pages,
        "chunk_count": len(chunks),
        "chunks": chunks
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

    chunks_collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    return {
        "document_id": document_id,
        "filename": parsed_document["filename"],
        "document_type": document_type,
        "chunk_count": len(chunks),
        "embedding_model": "all-MiniLM-L6-v2"
    }

@app.post("/search")
def search_documents(request: SearchRequest):
    """
    Here the distance indicates the spatial distance between requests and chunks in the embedding space.
    The similarity lower, more close semantically
    """
    model = get_embedding_model()
    query_embedding = model.encode([request.query], normalize_embeddings=True).tolist()[0]
    filters = []
    if request.document_id:
        filters.append({"document_id": request.document_id})
    if request.document_type:
        filters.append({"document_type": request.document_type})
    where = None
    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}
    query_arguments = {"query_embeddings": [query_embedding], "n_results": request.top_k, "include": [ "documents", "metadatas", "distances"]}
    if where:
        query_arguments["where"] = where
    results = chunks_collection.query(**query_arguments)
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    matches = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        matches.append({ "text": document, "metadata": metadata, "distance": distance, "similarity": max(0.0, min(1.0, 1 - distance)) })
    return {"query": request.query, "result_count": len(matches), "matches": matches}

@app.post("/requirements/evidence")
def retrieve_requirement_evidence(request: EvidenceRequest):
    search_request = SearchRequest(
        query=request.requirement,
        top_k=request.top_k,
        document_id=request.resume_document_id,
        document_type="resume")
    search_results = search_documents(search_request)
    return {"requirement": request.requirement, "resume_document_id": request.resume_document_id, "evidence": search_results["matches"]}