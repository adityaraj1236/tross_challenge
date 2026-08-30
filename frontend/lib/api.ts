import type { ApiErrorBody, ProfileResponse } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  errorCode: string;

  constructor(errorCode: string, message: string) {
    super(message);
    this.errorCode = errorCode;
  }
}

export async function fetchLinkedInProfile(url: string): Promise<ProfileResponse> {
  const response = await fetch(`${API_BASE_URL}/api/linkedin/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    let body: { detail?: ApiErrorBody } | ApiErrorBody | undefined;
    try {
      body = await response.json();
    } catch {
      throw new ApiError("UNKNOWN_ERROR", `Request failed with status ${response.status}`);
    }
    const detail = (body as { detail?: ApiErrorBody })?.detail ?? (body as ApiErrorBody);
    throw new ApiError(
      detail?.error_code ?? "UNKNOWN_ERROR",
      detail?.message ?? `Request failed with status ${response.status}`
    );
  }

  return response.json();
}
