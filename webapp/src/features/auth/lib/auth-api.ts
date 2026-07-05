import { routes } from "@/lib/constants/routes";
import type {
  ChangePasswordRequestPayload,
  AuthErrorResponse,
  AuthSuccessResponse,
  LoginRequestPayload,
  RegisterRequestPayload,
} from "@/types/auth";

export class AuthApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
  }
}

function extractAuthErrorMessage(data: unknown): string | null {
  if (typeof data !== "object" || data === null) {
    return null;
  }

  const candidate = data as {
    error?: unknown;
    detail?: unknown;
    message?: unknown;
  };

  if (typeof candidate.error === "string" && candidate.error.length > 0) {
    return candidate.error;
  }

  if (typeof candidate.detail === "string" && candidate.detail.length > 0) {
    return candidate.detail;
  }

  if (typeof candidate.message === "string" && candidate.message.length > 0) {
    return candidate.message;
  }

  return null;
}

async function callAuthEndpoint<TPayload>(
  path: string,
  payload: TPayload,
): Promise<AuthSuccessResponse> {
  let response: Response;

  try {
    response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      // Hapus credentials: "include" — tidak kompatibel dengan CORS allow_origins=["*"]
    });
  } catch {
    throw new AuthApiError("Tidak dapat terhubung ke server autentikasi.", 0);
  }

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new AuthApiError(
      extractAuthErrorMessage(data) ?? "Autentikasi gagal.",
      response.status,
    );
  }

  if (typeof data !== "object" || data === null) {
    throw new AuthApiError("Response autentikasi tidak valid.", 502);
  }

  if ("error" in data) {
    throw new AuthApiError(
      extractAuthErrorMessage(data) ?? "Autentikasi gagal.",
      response.status,
    );
  }

  return data as AuthSuccessResponse;
}

export function registerUser(
  payload: RegisterRequestPayload,
): Promise<AuthSuccessResponse> {
  return callAuthEndpoint(routes.api.auth.register, payload);
}

export function loginUser(payload: LoginRequestPayload): Promise<AuthSuccessResponse> {
  return callAuthEndpoint(routes.api.auth.login, payload);
}

export function changePassword(
  payload: ChangePasswordRequestPayload,
): Promise<AuthSuccessResponse> {
  return callAuthEndpoint(routes.api.auth.changePassword, payload);
}
