from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import pymupdf

app = FastAPI(title="Career Intelligence API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000" ], allow_credentials=True, allow_methods=["*"],  allow_headers=["*"])
MAX_FILE_SIZE = 10 * 1024 * 1024

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
