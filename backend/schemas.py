from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    document_id: str | None = None
    document_type: str | None = None


class JobUrlRequest(BaseModel):
    url: str = Field(min_length=8)


class EvidenceRequest(BaseModel):
    requirement: str = Field(min_length=1)
    resume_document_id: str | None = None
    top_k: int = Field(default=3, ge=1, le=10)

class AnalysisRequest(BaseModel):
    resume_document_id: str
    job_id: str
    top_k: int = Field(
        default=3,
        ge=1,
        le=5,
    )