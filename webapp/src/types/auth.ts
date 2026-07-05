export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: "admin" | "pharmacist" | "patient";
  nik?: string;
}

export interface RegisterRequestPayload {
  name: string;
  email: string;
  password: string;
  nik?: string;
}

export interface LoginRequestPayload {
  email: string;
  password: string;
}

export interface ChangePasswordRequestPayload {
  email: string;
  new_password: string;
}

export interface AuthSuccessResponse {
  message: string;
  user: AuthUser;
  access_token?: string;
  token_type?: string;
}

export interface AuthErrorResponse {
  error: string;
}
