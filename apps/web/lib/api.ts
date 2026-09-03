import type { ApiErrorPayload } from "@/lib/types";


const backendUrl = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${backendUrl}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError("The API is unavailable. Start FastAPI and PostgreSQL, then retry.", 503);
  }

  if (!response.ok) {
    let payload: ApiErrorPayload = {};
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      // The fallback message below is enough for non-JSON failures.
    }
    const detail = typeof payload.detail === "string" ? payload.detail : "Request failed";
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

