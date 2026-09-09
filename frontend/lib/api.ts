const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000";

export type MatchClassification =
  | "strong_match"
  | "partial_match"
  | "not_evidenced_in_resume";

export interface ResumeResponse {
  document_id: string;
  document_type: "resume";
  filename: string;
  page_count: number;
  section_count: number;
  chunk_count: number;
  embedding_model: string;
  extraction_method: string;
  ocr_page_numbers: number[];
  extraction_warnings: string[];
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSource {
  source_id: string;
  source_type: string;
  section_type: string;
  text: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  model: string;
  guardrail_applied: boolean;
}

export interface JobResponse {
  job_id: string;
  source_url: string;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  section_count: number;
  requirement_count: number;
  embedding_model: string;
  extraction_method: string;
  source_platform: string;
  extraction_quality: JobExtractionQuality;
}

export interface JobExtractionQuality {
  score: number;
  status: "good" | "warning" | "rejected";
  required_requirement_count: number;
  preferred_requirement_count: number;
  matching_section_count: number;
  issues: string[];
  warnings: string[];
}

export interface JobPreviewResponse {
  source_url: string;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  text: string;
  extraction_method: string;
  source_platform: string;
  extraction_quality: JobExtractionQuality;
}

export interface Evidence {
  chunk_id: string;
  section_type: string;
  source_text: string;
  distance: number;
  retrieval_similarity: number;
}

export interface RequirementResult {
  requirement_id: string;
  requirement_type: "required" | "preferred";
  category: string;
  requirement: string;
  evidence: Evidence[];
  classification: MatchClassification;
  confidence: number;
  supporting_chunk_ids: string[];
  explanation: string;
  guardrail_applied: boolean;
}

export interface ScoreSummary {
  overall_score: number | null;
  required_score: number | null;
  preferred_score: number | null;
  classification_counts: Record<
    MatchClassification,
    number
  >;
  pending_verification_count: number;
  guardrail_count: number;
}

export interface AnalysisResponse {
  resume_document_id: string;
  job_id: string;
  requirement_count: number;
  classifier_model: string;
  score_summary: ScoreSummary;
  results: RequirementResult[];
}

async function readResponse<T>(
  response: Response,
): Promise<T> {
  const data = await response.json();

  if (!response.ok) {
    const message =
      typeof data.detail === "string"
        ? data.detail
        : "The API request failed.";

    throw new Error(message);
  }

  return data as T;
}

export async function uploadResume(
  file: File,
): Promise<ResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/resumes`,
    {
      method: "POST",
      body: formData,
    },
  );

  return readResponse<ResumeResponse>(response);
}

export async function createJob(
  url: string,
): Promise<JobResponse> {
  const response = await fetch(
    `${API_BASE_URL}/jobs`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    },
  );

  return readResponse<JobResponse>(response);
}

export async function createAnalysis(
  resumeDocumentId: string,
  jobId: string,
): Promise<AnalysisResponse> {
  const response = await fetch(
    `${API_BASE_URL}/analyses`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        resume_document_id: resumeDocumentId,
        job_id: jobId,
        top_k: 3,
      }),
    },
  );

  return readResponse<AnalysisResponse>(response);
}

export async function sendChatMessage(
  resumeDocumentId: string,
  jobId: string,
  question: string,
  history: ChatHistoryMessage[],
): Promise<ChatResponse> {
  const response = await fetch(
    `${API_BASE_URL}/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        resume_document_id: resumeDocumentId,
        job_id: jobId,
        question,
        history,
      }),
    },
  );

  return readResponse<ChatResponse>(response);
}

export async function previewJob(
  url: string,
): Promise<JobPreviewResponse> {
  const response = await fetch(
    `${API_BASE_URL}/jobs/preview`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    },
  );

  return readResponse<JobPreviewResponse>(response);
}

export async function confirmJob(
  preview: JobPreviewResponse,
): Promise<JobResponse> {
  const response = await fetch(
    `${API_BASE_URL}/jobs/confirm`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(preview),
    },
  );

  return readResponse<JobResponse>(response);
}
