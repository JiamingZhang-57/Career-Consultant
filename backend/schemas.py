from pydantic import BaseModel, Field
from typing import Literal

class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    document_id: str | None = None
    document_type: str | None = None


class JobUrlRequest(BaseModel):
    url: str = Field(min_length=8)


class JobContentRequest(BaseModel):
    source_url: str = Field(min_length=8)
    title: str = Field(default="", max_length=300)
    company: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=300)
    employment_type: str = Field(default="", max_length=100)
    text: str = Field(min_length=200, max_length=100_000)
    extraction_method: str = Field(default="manual_review")
    source_platform: str = Field(default="generic")


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

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(
        min_length=1,
        max_length=2000,
    )


class ChatRequest(BaseModel):
    resume_document_id: str
    job_id: str
    question: str = Field(
        min_length=2,
        max_length=1000,
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=10,
    )
