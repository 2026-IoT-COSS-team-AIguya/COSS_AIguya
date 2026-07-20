import { ApiError } from "@/lib/api/errors";
import type { ApiErrorBody } from "@/lib/types";

// 브라우저는 항상 현재 프론트와 같은 출처로 요청합니다. next.config.ts의 rewrite가
// Django로 전달하므로 다른 노트북도 3000번 포트 하나만 접근하면 됩니다.
const BASE_URL = "/api/v1";

// 명세 10장: Access Token은 프론트 메모리에 저장합니다.
// (localStorage에 두지 않는 것이 합의된 내용이라 모듈 스코프 변수로 보관합니다.)
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

// 401 → refresh를 여러 요청이 동시에 터뜨리지 않도록 진행 중인 갱신을 공유합니다.
let refreshInFlight: Promise<boolean> | null = null;

type RequestOptions = {
  method?: string;
  // JSON 본문. FormData를 보낼 때는 body 대신 formData를 씁니다.
  json?: unknown;
  formData?: FormData;
  signal?: AbortSignal;
  // refresh 재시도를 하지 않을 요청 (로그인, 갱신 자체)
  skipAuthRetry?: boolean;
};

async function parseError(response: Response): Promise<ApiErrorBody> {
  try {
    const body = await response.json();

    if (body && typeof body === "object" && "error" in body) {
      return (body as { error: ApiErrorBody }).error;
    }
  } catch {
    // 본문이 JSON이 아닌 경우 아래 기본값으로 넘어갑니다.
  }

  // 백엔드가 명세 형식을 못 지킨 응답(프록시 502 등)도 같은 모양으로 정규화합니다.
  return {
    code: response.status >= 500 ? "INTERNAL_SERVER_ERROR" : "VALIDATION_ERROR",
    message: `요청이 실패했습니다 (HTTP ${response.status})`,
  };
}

/** Refresh 쿠키로 Access Token을 다시 받아옵니다. 성공하면 true.
 *
 * 401 재시도(아래 request)와, 새로고침 후 세션 복구(endpoints.restoreSession)가
 * 같이 씁니다. */
export async function refreshAccessToken(): Promise<boolean> {
  // Refresh Token은 HttpOnly 쿠키라 JS가 읽지 않고, credentials로만 실려 갑니다.
  const response = await fetch(`${BASE_URL}/auth/refresh/`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    setAccessToken(null);
    return false;
  }

  const body = (await response.json()) as { access?: string };

  if (!body.access) {
    setAccessToken(null);
    return false;
  }

  setAccessToken(body.access);
  return true;
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  let body: BodyInit | undefined;

  if (options.formData) {
    // multipart 경계(boundary)는 브라우저가 붙입니다. Content-Type을 직접 넣으면 깨집니다.
    body = options.formData;
  } else if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }

  return fetch(`${BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
    signal: options.signal,
    // 명세 10장: 프론트와 백엔드 오리진이 다르면 Refresh 쿠키를 위해 필요합니다.
    credentials: "include",
  });
}

export async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  let response = await send(path, options);

  // 명세 10장: 401이면 토큰 갱신을 한 번 시도한 뒤 기존 요청을 재시도합니다.
  if (response.status === 401 && !options.skipAuthRetry) {
    refreshInFlight = refreshInFlight ?? refreshAccessToken();
    const refreshed = await refreshInFlight;
    refreshInFlight = null;

    if (!refreshed) {
      // 갱신까지 실패하면 로그인 화면으로 보내야 합니다. 호출부가 이 code로 판단합니다.
      throw new ApiError(401, {
        code: "TOKEN_EXPIRED",
        message: "세션이 만료되었습니다.",
      });
    }

    response = await send(path, options);
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response));
  }

  // 204 No Content (로그아웃, 삭제)
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),

  post: <T>(path: string, json?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", json, signal }),

  put: <T>(path: string, json?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "PUT", json, signal }),

  patch: <T>(path: string, json?: unknown) =>
    request<T>(path, { method: "PATCH", json }),

  upload: <T>(path: string, formData: FormData, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", formData, signal }),

  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
