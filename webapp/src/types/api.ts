export interface ApiSuccess<T> {
  data: T;
  message?: string;
}

export interface ApiFailure {
  error: string;
  details?: unknown;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;
