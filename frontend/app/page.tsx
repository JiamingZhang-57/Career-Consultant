"use client";

import {
  useEffect,
  useState
} from "react";

import {
  AnalysisResponse,
  JobResponse,
  MatchClassification,
  ResumeResponse,
  createAnalysis,
  createJob,
  uploadResume,
  ChatSource,
  sendChatMessage
} from "../lib/api";

type ApiStatus = "checking" | "online" | "offline";
type BusyState = "resume" | "analysis" | "chat"| null;
type DisplayClassification = | MatchClassification | "user_confirmed_gap";
interface ComparedJob {job: JobResponse; analysis: AnalysisResponse}
interface JobDisplayDetails {title: string; company: string}
interface UiChatMessage {id: string; role: "user" | "assistant"; content: string; sources?: ChatSource[]; guardrailApplied?: boolean}
const classificationLabels: Record<DisplayClassification, string> = {
  strong_match: "Strong match",
  partial_match: "Partial match",
  not_evidenced_in_resume: "Pending verification",
  user_confirmed_gap: "User confirmed gap",
};

const classificationStyles: Record<DisplayClassification, string> = {
  strong_match:
    "border-emerald-700 bg-emerald-950 text-emerald-300",
  partial_match:
    "border-amber-700 bg-amber-950 text-amber-300",
  not_evidenced_in_resume:
    "border-slate-600 bg-slate-800 text-slate-300",
  user_confirmed_gap:
  "border-red-700 bg-red-950 text-red-300",
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
  const [chatQuestion, setChatQuestion] =
    useState("");

  const [jobUrl, setJobUrl] = useState("");

  const [job, setJob] =
    useState<JobResponse | null>(null);

  const [analysis, setAnalysis] =
    useState<AnalysisResponse | null>(null);

  const [chatMessagesByJob, setChatMessagesByJob] = useState<Record<string, UiChatMessage[]>>({});
  const chatMessages = analysis ? chatMessagesByJob[analysis.job_id] ?? [] : [];

  const [busy, setBusy] =
    useState<BusyState>(null);

  const [error, setError] =
    useState<string | null>(null);

  const [confirmedGapIds, setConfirmedGapIds] =
  useState<Set<string>>(() => new Set());

  const [comparisons, setComparisons] =
  useState<ComparedJob[]>([]);

  const [jobDisplayDetails, setJobDisplayDetails,] = useState<Record<string, JobDisplayDetails>>({},);

  function getDisplayTitle(
    currentJob: JobResponse,
  ) {
    return (
      jobDisplayDetails[
        currentJob.job_id
      ]?.title.trim() ||
      currentJob.title.trim() ||
      "Job details"
    );
  }

  function getDisplayCompany(
    currentJob: JobResponse,
  ) {
    return (
      jobDisplayDetails[
        currentJob.job_id
      ]?.company.trim() ||
      currentJob.company.trim() ||
      "Unknown company"
    );
  }

  function updateJobDisplayField(
    currentJob: JobResponse,
    field: "title" | "company",
    value: string,
  ) {
    setJobDisplayDetails((current) => {
      const existing =
        current[currentJob.job_id];

      return {
        ...current,
        [currentJob.job_id]: {
          title:
            existing?.title ??
            currentJob.title,
          company:
            existing?.company ??
            currentJob.company,
          [field]: value,
        },
      };
    });
  }

  function appendChatMessage(
    jobId: string,
    message: UiChatMessage,
  ) {
    setChatMessagesByJob((current) => ({
      ...current,
      [jobId]: [
        ...(current[jobId] ?? []),
        message,
      ].slice(-20),
    }));
  }

  function toggleConfirmedGap(requirementId: string) {
  setConfirmedGapIds((current) => {
    const next = new Set(current);

    if (next.has(requirementId)) {
      next.delete(requirementId);
    } else {
      next.add(requirementId);
    }

    return next;
  });
}
  function removeComparison(jobId: string) {
  setComparisons((current) =>
    current.filter(
      (item) => item.job.job_id !== jobId,
    ),
  );
  setChatMessagesByJob((current) => {
  const updated = { ...current };
  delete updated[jobId];
  return updated});

  if (job?.job_id === jobId) {
    setJob(null);
    setAnalysis(null);
    setJobUrl("");
    setChatQuestion("");
  }
}
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
    setComparisons([]);
    setChatMessagesByJob({});
    setChatQuestion("");
    setConfirmedGapIds(new Set());

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
      setChatQuestion("");
      setComparisons((current) => {
        const withoutCurrentJob = current.filter(
          (item) => item.job.job_id !== currentJob.job_id,
        );

        const updated = [
          ...withoutCurrentJob,
          {
            job: currentJob,
            analysis: result,
          },
        ];

        return updated.sort((first, second) => {
          const firstScore =
            first.analysis.score_summary.overall_score ?? -1;

          const secondScore =
            second.analysis.score_summary.overall_score ?? -1;

          return secondScore - firstScore;
        });
      });

    } catch (analysisError) {
      setError(getErrorMessage(analysisError));
    } finally {
      setBusy(null);
    }
  }
  async function handleChat() {
      const question = chatQuestion.trim();

      if (!question) {
        return;
      }

      if (!analysis || !job) {
        setError(
          "Please analyse and select a job before using chat.",
        );
        return;
      }

      const history = chatMessages
        .slice(-10)
        .map((message) => ({
          role: message.role,
          content: message.content,
        }));

      const userMessage: UiChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: question,
      };

      appendChatMessage(analysis.job_id, userMessage);

      setChatQuestion("");
      setBusy("chat");
      setError(null);

      try {
        const response = await sendChatMessage(
          analysis.resume_document_id,
          analysis.job_id,
          question,
          history,
        );

        const assistantMessage: UiChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          guardrailApplied:
            response.guardrail_applied,
        };

        appendChatMessage(analysis.job_id, assistantMessage);
      } catch (chatError) {
        setError(getErrorMessage(chatError));
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
                setChatQuestion("");
                setAnalysis(null);
              }}
            />

            {job && (
              <div className="mt-4 rounded-lg bg-slate-800 p-4 text-sm text-slate-300">
                <p className="font-medium text-emerald-300">
                  Job page processed
                </p>

                <div className="mt-4 grid gap-3">
                  <label className="text-xs text-slate-400">
                    Display title

                    <input
                      type="text"
                      value={
                        jobDisplayDetails[job.job_id]?.title ??
                        job.title
                      }
                      placeholder="Enter job title"
                      className="mt-1 block w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-sm text-white"
                      onChange={(event) =>
                        updateJobDisplayField(
                          job,
                          "title",
                          event.target.value,
                        )
                      }
                    />
                  </label>

                  <label className="text-xs text-slate-400">
                    Company

                    <input
                      type="text"
                      value={
                        jobDisplayDetails[job.job_id]?.company ??
                        job.company
                      }
                      placeholder="Enter company name"
                      className="mt-1 block w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-sm text-white"
                      onChange={(event) =>
                        updateJobDisplayField(
                          job,
                          "company",
                          event.target.value,
                        )
                      }
                    />
                  </label>
                </div>

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

        {comparisons.length > 0 && (
            <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <h2 className="text-2xl font-semibold">
                Job comparison
              </h2>

              <p className="mt-2 text-sm text-slate-400">
                Roles are ranked by overall alignment score.
              </p>

              <div className="mt-5 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-700 text-slate-400">
                    <tr>
                      <th className="px-3 py-3">Rank</th>
                      <th className="px-3 py-3">Role</th>
                      <th className="px-3 py-3">Overall</th>
                      <th className="px-3 py-3">Required</th>
                      <th className="px-3 py-3">Preferred</th>
                      <th className="px-3 py-3"></th>
                    </tr>
                  </thead>

                  <tbody>
                    {comparisons.map((item, index) => (
                      <tr
                        key={item.job.job_id}
                        className="border-b border-slate-800"
                      >
                        <td className="px-3 py-4">
                          {index + 1}
                        </td>

                        <td className="px-3 py-4">
                          <p className="font-medium text-white">
                            {getDisplayTitle(item.job)}
                          </p>

                          <p className="text-slate-400">
                            {getDisplayCompany(item.job)}
                          </p>
                        </td>

                        <td className="px-3 py-4 text-cyan-300">
                          {displayScore(
                            item.analysis.score_summary.overall_score,
                          )}
                        </td>

                        <td className="px-3 py-4">
                          {displayScore(
                            item.analysis.score_summary.required_score,
                          )}
                        </td>

                        <td className="px-3 py-4">
                          {displayScore(
                            item.analysis.score_summary.preferred_score,
                          )}
                        </td>

                        <td className="px-3 py-4">
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setJob(item.job);
                                setJobUrl(item.job.source_url);
                                setAnalysis(item.analysis);
                                setChatQuestion("");
                              }}
                              className="rounded-lg border border-slate-600 px-3 py-2 hover:border-cyan-500"
                            >
                              View details
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                removeComparison(item.job.job_id)
                              }
                              className="rounded-lg border border-red-800 px-3 py-2 text-red-300 hover:bg-red-950"
                            >
                              Remove
                            </button>
                          </div>
                        </td>
                      {/*  xxx*/}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}


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
                const isConfirmedGap = confirmedGapIds.has(
                  result.requirement_id,
                );

                const displayClassification: DisplayClassification =
                  isConfirmedGap
                    ? "user_confirmed_gap"
                    : result.classification;

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
                            displayClassification
                          ]
                        }`}
                      >
                        {
                          classificationLabels[
                            displayClassification
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
                      <div className="mt-4">
                        <p
                          className={
                            isConfirmedGap
                              ? "text-sm text-red-300"
                              : "text-sm text-amber-300"
                          }
                        >
                          {isConfirmedGap
                            ? "The user has confirmed this as an actual skill gap."
                            : "Pending verification: the resume does not provide sufficient evidence."}
                        </p>

                        <button
                          type="button"
                          onClick={() =>
                            toggleConfirmedGap(result.requirement_id)
                          }
                          className="mt-3 rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:border-cyan-500"
                        >
                          {isConfirmedGap
                            ? "Undo confirmation"
                            : "Confirm skill gap"}
                        </button>
                      </div>
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
        {analysis && job && (
          <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-2xl font-semibold">
              Career assistant
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Ask questions about your fit, resume evidence,
              skill gaps, or interview preparation for{" "}
              <span className="text-cyan-300">
                {getDisplayTitle(job)}
              </span>
            </p>

            <div className="mt-6 space-y-4">
              {chatMessages.length === 0 && (
                <div className="rounded-xl bg-slate-950 p-4 text-sm text-slate-400">
                  Try asking: “What skills are not evidenced
                  in my resume?”
                </div>
              )}

              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={
                    message.role === "user"
                      ? "ml-auto max-w-3xl rounded-xl bg-cyan-950 p-4"
                      : "mr-auto max-w-3xl rounded-xl bg-slate-950 p-4"
                  }
                >
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                    {message.role === "user"
                      ? "You"
                      : "Career assistant"}
                  </p>

                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-200">
                    {message.content}
                  </p>

                  {message.sources &&
                    message.sources.length > 0 && (
                      <details className="mt-4">
                        <summary className="cursor-pointer text-xs text-cyan-400">
                          View supporting sources
                        </summary>

                        <div className="mt-3 space-y-3">
                          {message.sources.map((source) => (
                            <blockquote
                              key={source.source_id}
                              className="rounded-lg border-l-2 border-cyan-700 bg-slate-900 p-3 text-xs leading-5 text-slate-400"
                            >
                              <p className="mb-1 text-cyan-300">
                                {source.source_id} ·{" "}
                                {source.section_type}
                              </p>

                              {source.text}
                            </blockquote>
                          ))}
                        </div>
                      </details>
                    )}

                  {message.guardrailApplied && (
                    <p className="mt-3 text-xs text-amber-400">
                      Citation guardrail was applied to this
                      response.
                    </p>
                  )}
                </div>
              ))}
            </div>

            <form
              className="mt-6 flex gap-3"
              onSubmit={(event) => {
                event.preventDefault();
                void handleChat();
              }}
            >
              <textarea
                rows={3}
                value={chatQuestion}
                disabled={busy !== null}
                placeholder="Ask about this role..."
                className="min-h-24 flex-1 resize-y rounded-xl border border-slate-700 bg-slate-950 p-3 text-sm outline-none focus:border-cyan-500 disabled:cursor-wait disabled:opacity-50"
                onChange={(event) =>
                  setChatQuestion(event.target.value)
                }
              />

              <button
                type="submit"
                disabled={
                  busy !== null ||
                  !chatQuestion.trim()
                }
                className="self-end rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy === "chat"
                  ? "Thinking..."
                  : "Send"}
              </button>
            </form>
          </section>
        )}
      </div>
    </main>
  );
}