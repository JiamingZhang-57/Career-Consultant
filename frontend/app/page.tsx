"use client";

import { useEffect, useState } from "react";

type ApiStatus = "checking" | "online" | "offline";

export default function Home() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    async function checkApi() {
      try {
        const response = await fetch("http://127.0.0.1:8000/health");

        if (!response.ok) {
          throw new Error("API request failed");
        }

        setApiStatus("online");
      } catch {
        setApiStatus("offline");
      }
    }

    checkApi();
  }, []);

  const statusText = {
    checking: "Checking backend...",
    online: "Backend connected",
    offline: "Backend unavailable",
  }[apiStatus];

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-white">
      <div className="mx-auto max-w-5xl">
        <div className="mb-16">
          <p className="mb-4 text-sm font-medium uppercase tracking-[0.3em] text-cyan-400">
            Career Intelligence
          </p>

          <h1 className="max-w-3xl text-5xl font-semibold leading-tight">
            Understand how your experience aligns with real opportunities.
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Upload a resume and job descriptions to identify evidence-backed
            matches, partial matches, and skills that need verification.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Resume evidence</h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Retrieve relevant experience from the uploaded resume.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Requirement matching</h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Compare each job requirement with supporting evidence.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Pending verification</h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Separate actual skill gaps from missing resume evidence.
            </p>
          </div>
        </div>

        <div className="mt-10 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm text-slate-400">System status</p>
          <p
            className={`mt-2 text-lg font-medium ${
              apiStatus === "online" ? "text-emerald-400" : "text-amber-400"
            }`}
          >
            {statusText}
          </p>
        </div>
      </div>
    </main>
  );
}