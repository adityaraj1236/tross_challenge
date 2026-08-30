"use client";

import { useState } from "react";
import { ApiError, fetchLinkedInProfile } from "@/lib/api";
import type { ProfileResponse } from "@/lib/types";
import ProfileForm from "@/components/ProfileForm";
import ProfileResult from "@/components/ProfileResult";

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProfileResponse | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  async function handleSubmit(url: string) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetchLinkedInProfile(url);
      setResult(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ code: err.errorCode, message: err.message });
      } else {
        setError({ code: "UNKNOWN_ERROR", message: "Something went wrong. Please try again." });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-12">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">LinkedIn Profile API</h1>
        <p className="mt-1 text-sm text-slate-500">
          Paste a LinkedIn profile URL to fetch structured data via a browserless, direct-HTTP backend.
        </p>
      </header>

      <ProfileForm onSubmit={handleSubmit} loading={loading} />

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <p className="font-medium">{error.code}</p>
          <p>{error.message}</p>
        </div>
      )}

      {loading && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
          Fetching profile from LinkedIn...
        </div>
      )}

      {result && <ProfileResult result={result} />}
    </main>
  );
}
