const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(init?.headers);
    if (init?.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
    });
  } catch {
    throw new ApiError("Could not reach the API. Check that the backend is running.", 0);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.error?.details?.[0]?.message;
    const message = body?.error?.message || detail || `Request failed (${response.status}).`;
    throw new ApiError(detail && message === "Invalid request" ? detail : message, response.status);
  }
  return response.json() as Promise<T>;
}
