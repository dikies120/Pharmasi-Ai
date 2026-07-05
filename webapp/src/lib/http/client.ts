import { env } from "@/lib/env";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type ApiRequestOptions = Omit<RequestInit, "method" | "body"> & {
  method?: HttpMethod;
  body?: BodyInit | Record<string, unknown> | unknown[];
};

export class HttpError extends Error {
  status: number;
  responseBody: unknown;

  constructor(status: number, message: string, responseBody: unknown) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.responseBody = responseBody;
  }
}

function resolveUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  return new URL(path, env.backendUrl).toString();
}

function normalizeBody(
  body: ApiRequestOptions["body"],
): BodyInit | undefined {
  if (body === undefined) {
    return undefined;
  }

  if (
    typeof body === "string" ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof Blob ||
    body instanceof ArrayBuffer ||
    ArrayBuffer.isView(body)
  ) {
    return body;
  }

  return JSON.stringify(body);
}

async function parseResponse(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { method = "GET", body, headers, ...rest } = options;
  const normalizedBody = normalizeBody(body);
  const requestHeaders = new Headers(headers);

  if (
    normalizedBody !== undefined &&
    !requestHeaders.has("Content-Type") &&
    !(body instanceof FormData)
  ) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(resolveUrl(path), {
    ...rest,
    method,
    headers: requestHeaders,
    body: normalizedBody,
  });

  const parsedBody = await parseResponse(response);

  if (!response.ok) {
    throw new HttpError(
      response.status,
      `Request failed with status ${response.status}`,
      parsedBody,
    );
  }

  return parsedBody as T;
}
