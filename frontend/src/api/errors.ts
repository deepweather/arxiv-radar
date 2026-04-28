import { AxiosError } from "axios";

export function getHttpStatus(error: unknown): number | null {
  if (error instanceof AxiosError) {
    return error.response?.status ?? null;
  }
  return null;
}

export function getErrorDetail(error: unknown): string | null {
  if (error instanceof AxiosError) {
    const data = error.response?.data;
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  }
  return null;
}

export function getRetryAfterSeconds(error: unknown): number | null {
  if (!(error instanceof AxiosError)) return null;
  const header = error.response?.headers?.["retry-after"];
  if (typeof header === "string") {
    const value = Number.parseInt(header, 10);
    if (Number.isFinite(value) && value > 0) return value;
  }
  const detail = getErrorDetail(error);
  if (detail) {
    const match = detail.match(/(\d+)\s*seconds?/i);
    if (match) {
      const value = Number.parseInt(match[1], 10);
      if (Number.isFinite(value) && value > 0) return value;
    }
  }
  return null;
}
