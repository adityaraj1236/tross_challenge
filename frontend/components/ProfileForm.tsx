"use client";

import { FormEvent, useState } from "react";

interface ProfileFormProps {
  onSubmit: (url: string) => void;
  loading: boolean;
}

export default function ProfileForm({ onSubmit, loading }: ProfileFormProps) {
  const [url, setUrl] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (url.trim()) {
      onSubmit(url.trim());
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://www.linkedin.com/in/jane-doe/"
        className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-slate-500"
        required
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Fetching..." : "Fetch Profile"}
      </button>
    </form>
  );
}
