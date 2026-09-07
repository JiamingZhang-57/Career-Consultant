"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  AnalysisResponse,
  JobResponse,
  MatchClassification,
  ResumeResponse,
  createAnalysis,
  createJob,
  uploadResume,
} from "../lib/api";

type ApiStatus = "checking" | "online" | "offline";
type BusyState = "resume" | "analysis" | null;

const classificationLabels: Record<
  MatchClassification,
  string
> = {
  strong_match: "Strong match",
  partial_match: "Partial match",
  not_evidenced_in_resume: "Pending verification",
};

const classificationStyles: Record<
  MatchClassification,
  string
> = {
  strong_match:
    "border-emerald-700 bg-emerald-950 text-emerald-300",
  partial_match:
    "border-amber-700 bg-amber-950 text-amber-300",
  not_evidenced_in_resume:
    "border-slate-600 bg-slate-800 text-slate-300",
};

function displayScore(score: number | null) {
  return score === null ? "N/A" : `${score}%`;
}

function getErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "An unexpected error occurred.";
}

export default function Home() {
  const [apiStatus, setApiStatus] =
    useState<ApiStatus>("checking");

  const [resume, setResume] =
    useState<ResumeResponse | null>(null);

  const [jobUrl, setJobUrl] = useState("");

  const [job, setJob] =
    useState<JobResponse | null>(null);

  const [analysis, setAnalysis] =
    useState<AnalysisResponse | null>(null);

  const [busy, setBusy] =
    useState<BusyState>(null);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    async function checkApi() {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/health",
        );

        setApiStatus(
          response.ok ? "online" : "offline",
        );
      } catch {
        setApiStatus("offline");
      }
    }

    checkApi();
  }, []);

  async function handleResumeSelection(
    file: File | null,
  ) {
    setResume(null);
    setAnalysis(null);

    if (!file) {
      return;
    }

    setBusy("resume");
    setError(null);

    try {
      const uploadedResume = await uploadResume(
        file,
      );

      setResume(uploadedResume);
    } catch (uploadError) {
      setError(getErrorMessage(uploadError));
    } finally {
      setBusy(null);
    }
  }

  async function handleAnalysis() {
    if (!resume) {
      setError("Please choose a resume PDF first.");
      return;
    }

    if (!jobUrl.trim()) {
      setError("Please enter an official job URL.");
      return;
    }

    setBusy("analysis");
    setError(null);
    setAnalysis(null);

    try {
      let currentJob = job;

      if (!currentJob) {
        currentJob = await createJob(
          jobUrl.trim(),
        );

        setJob(currentJob);
      }

      const result = await createAnalysis(
        resume.document_id,
        currentJob.job_id,
      );

      setAnalysis(result);
    } catch (analysisError) {
      setError(getErrorMessage(analysisError));
    } finally {
      setBusy(null);
    }
  }

  const statusText = {
    checking: "Checking backend...",
    online: "Backend connected",
    offline: "Backend unavailable",
  }[apiStatus];

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 text-white">
      <div className="mx-auto max-w-6xl">
        <header className="mb-10">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">
              Career Intelligence
            </p>

            <p
              className={
                apiStatus === "online"
                  ? "text-sm text-emerald-400"
                  : "text-sm text-amber-400"
              }
            >
              {statusText}
            </p>
          </div>

          <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-tight md:text-5xl">
            Evidence-backed job alignment
          </h1>

          <p className="mt-4 max-w-2xl text-slate-300">
            Choose your resume, paste an official job
            URL, and compare every requirement against
            evidence from your resume.
          </p>
        </header>

        {error && (
          <div className="mb-6 rounded-xl border border-red-800 bg-red-950 p-4 text-red-200">
            {error}
          </div>
        )}

        <section className="grid gap-6 md:grid-cols-2">
          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-cyan-400">
              Step 1
            </p>

            <h2 className="mt-2 text-xl font-semibold">
              Choose resume
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Choose a PDF file. It will be processed
              automatically.
            </p>

            <input
              type="file"
              accept=".pdf,application/pdf"
              disabled={busy !== null}
              className="mt-5 block w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm disabled:cursor-wait disabled:opacity-50"
              onChange={(event) => {
                const file =
                  event.target.files?.[0] ?? null;

                void handleResumeSelection(file);
              }}
            />

            {busy === "resume" && (
              <p className="mt-4 text-sm text-cyan-300">
                Reading and indexing resume...
              </p>
            )}

            {resume && (
              <div className="mt-4 rounded-lg bg-slate-800 p-4 text-sm text-slate-300">
                <p className="font-medium text-emerald-300">
                  Resume ready
                </p>

                <p className="mt-1">
                  {resume.filename}
                </p>

                <p>
                  {resume.chunk_count} evidence chunks
                </p>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-cyan-400">
              Step 2
            </p>

            <h2 className="mt-2 text-xl font-semibold">
              Enter job description URL
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Paste an official company or recruitment
              platform URL. It will be fetched when you
              start the analysis.
            </p>

            <input
              type="url"
              value={jobUrl}
              placeholder="https://company.com/careers/job..."
              disabled={busy !== null}
              className="mt-5 block w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm outline-none focus:border-cyan-500 disabled:cursor-wait disabled:opacity-50"
              onChange={(event) => {
                setJobUrl(event.target.value);
                setJob(null);
                setAnalysis(null);
              }}
            />

            {job && (
              <div className="mt-4 rounded-lg bg-slate-800 p-4 text-sm text-slate-300">
                <p className="font-medium text-emerald-300">
                  Job page processed
                </p>

                <p className="mt-1">
                  {job.title} · {job.company}
                </p>

                <p>
                  {job.requirement_count} requirements
                </p>
              </div>
            )}
          </section>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-cyan-400">
            Step 3
          </p>

          <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">
                Analyse alignment
              </h2>

              <p className="mt-1 text-sm text-slate-400">
                The job page will be fetched and compared
                with the selected resume automatically.
              </p>
            </div>

            <button
              type="button"
              disabled={busy !== null}
              onClick={handleAnalysis}
              className="rounded-lg bg-emerald-400 px-5 py-3 font-semibold text-slate-950 disabled:cursor-wait disabled:opacity-50"
            >
              {busy === "analysis"
                ? "Fetching job and analysing..."
                : "Analyse match"}
            </button>
          </div>
        </section>

        {analysis && (
          <section className="mt-8">
            <h2 className="text-2xl font-semibold">
              Alignment results
            </h2>

            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              {[
                [
                  "Overall",
                  analysis.score_summary.overall_score,
                ],
                [
                  "Required",
                  analysis.score_summary.required_score,
                ],
                [
                  "Preferred",
                  analysis.score_summary.preferred_score,
                ],
              ].map(([label, score]) => (
                <div
                  key={String(label)}
                  className="rounded-2xl border border-slate-800 bg-slate-900 p-5"
                >
                  <p className="text-sm text-slate-400">
                    {label}
                  </p>

                  <p className="mt-2 text-3xl font-semibold text-cyan-300">
                    {displayScore(
                      score as number | null,
                    )}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-6 space-y-4">
              {analysis.results.map((result) => {
                const supportingEvidence =
                  result.evidence.filter((item) =>
                    result.supporting_chunk_ids.includes(
                      item.chunk_id,
                    ),
                  );

                return (
                  <article
                    key={result.requirement_id}
                    className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-wider text-slate-500">
                          {result.requirement_type} ·{" "}
                          {result.category}
                        </p>

                        <h3 className="mt-2 font-medium">
                          {result.requirement}
                        </h3>
                      </div>

                      <span
                        className={`rounded-full border px-3 py-1 text-xs font-medium ${
                          classificationStyles[
                            result.classification
                          ]
                        }`}
                      >
                        {
                          classificationLabels[
                            result.classification
                          ]
                        }
                      </span>
                    </div>

                    <p className="mt-4 text-sm leading-6 text-slate-300">
                      {result.explanation}
                    </p>

                    <p className="mt-2 text-xs text-slate-500">
                      Classification confidence:{" "}
                      {Math.round(
                        result.confidence * 100,
                      )}
                      %
                    </p>

                    {supportingEvidence.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                          Supporting resume evidence
                        </p>

                        {supportingEvidence.map(
                          (evidence) => (
                            <blockquote
                              key={evidence.chunk_id}
                              className="rounded-lg border-l-2 border-cyan-500 bg-slate-950 p-3 text-sm leading-6 text-slate-300"
                            >
                              {evidence.source_text}
                            </blockquote>
                          ),
                        )}
                      </div>
                    )}

                    {result.classification ===
                      "not_evidenced_in_resume" && (
                      <p className="mt-4 text-sm text-amber-300">
                        Pending verification: the resume
                        does not provide sufficient evidence.
                      </p>
                    )}

                    {result.guardrail_applied && (
                      <p className="mt-3 text-xs text-slate-500">
                        Evidence citation guardrail applied.
                      </p>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}