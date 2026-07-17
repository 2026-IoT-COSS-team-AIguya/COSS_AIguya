import type { ApiErrorBody } from "@/lib/types";

// 백엔드는 안정적인 영문 code와 기본 message를 제공하고,
// 프론트는 code에 맞는 사용자 문구를 표시합니다 (명세 8장).
//
// 이름은 팀이 확정한 8장 기준입니다. 설계 초안 26장이 같은 뜻에 다른 이름
// (UNSUPPORTED_VIDEO_FORMAT / NO_SIGN_DETECTED)을 쓰지만, 8장이 우선입니다.
// 26장에만 있던 코드는 아래 "추가분"으로 병합했습니다.
export const errorMessages: Record<string, string> = {
  // --- 명세 8장 ---
  VALIDATION_ERROR: "입력값을 확인해주세요.",
  INVALID_CREDENTIALS: "아이디 또는 비밀번호를 확인해주세요.",
  AUTHENTICATION_REQUIRED: "로그인이 필요해요.",
  TOKEN_EXPIRED: "로그인이 만료되었어요. 다시 로그인해주세요.",
  CONVERSATION_NOT_FOUND: "대화를 찾을 수 없어요.",
  CONVERSATION_ACCESS_DENIED: "이 대화에 접근할 권한이 없어요.",
  ALREADY_JOINED: "이미 참여한 대화예요.",
  VIDEO_TOO_LARGE: "영상 크기가 너무 큽니다.",
  UNSUPPORTED_VIDEO_TYPE: "지원하지 않는 영상 형식이에요.",
  SIGN_NOT_DETECTED: "수어를 인식하지 못했어요. 다시 촬영해주세요.",
  SIGN_VIDEO_NOT_FOUND: "해당 키워드의 수어 영상이 없어요.",
  AI_SERVER_UNAVAILABLE: "잠시 후 다시 시도해주세요.",
  INTERNAL_SERVER_ERROR: "서버에 문제가 발생했어요. 잠시 후 다시 시도해주세요.",

  // --- 26.1 영상 업로드 (추가분) ---
  VIDEO_REQUIRED: "영상 파일을 첨부해주세요.",
  DUPLICATE_CAPTURE_ID: "이미 처리된 촬영이에요.",
  VIDEO_SAVE_FAILED: "영상을 저장하지 못했어요. 다시 시도해주세요.",

  // --- 26.2 AI 처리 (추가분) ---
  // 인식 실패(SIGN_NOT_DETECTED)와 서버 장애를 구분합니다 (27장 원칙).
  AI_TIMEOUT: "분석이 너무 오래 걸려요. 다시 시도해주세요.",
  AI_INFERENCE_FAILED: "분석에 실패했어요. 다시 촬영해주세요.",
  LOW_CONFIDENCE: "수어를 또렷하게 인식하지 못했어요. 다시 촬영해주세요.",
  INVALID_AI_RESPONSE: "분석 결과를 읽지 못했어요. 다시 시도해주세요.",

  // --- 26.3 oneM2M (추가분) ---
  // 27장 원칙: oneM2M 등록 실패가 영상과 AI 결과를 삭제하게 두지 않습니다.
  // 사용자에게는 대화가 정상 동작하므로 굳이 노출하지 않고, 로그로 추적합니다.
  ONEM2M_AUTH_FAILED: "플랫폼 연동에 문제가 있어요. 대화는 계속 사용할 수 있어요.",
  ONEM2M_CONNECTION_FAILED:
    "플랫폼 연동에 문제가 있어요. 대화는 계속 사용할 수 있어요.",
  ONEM2M_RESOURCE_NOT_FOUND:
    "플랫폼 연동에 문제가 있어요. 대화는 계속 사용할 수 있어요.",
  ONEM2M_DUPLICATE_RESOURCE:
    "플랫폼 연동에 문제가 있어요. 대화는 계속 사용할 수 있어요.",
  ONEM2M_CREATE_FAILED:
    "플랫폼 연동에 문제가 있어요. 대화는 계속 사용할 수 있어요.",
  ONEM2M_INVALID_RESPONSE:
    "플랫폼 연동에 문제가 있어요. 대화는 계속 사용할 수 있어요.",
};

const fallbackMessage = "알 수 없는 오류가 발생했어요.";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fields?: Record<string, string[]>;

  constructor(status: number, body: ApiErrorBody) {
    // 사용자에게 노출할 문구와 서버 로그용 원문을 구분합니다 (명세 20장 체크리스트).
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.status = status;
    this.fields = body.fields;
  }

  // 화면에 띄울 문구. 모르는 code면 백엔드 기본 message로 물러섭니다.
  get userMessage(): string {
    return errorMessages[this.code] ?? this.message ?? fallbackMessage;
  }
}

/**
 * 로그인 화면으로 돌려보내야 하는 오류인가?
 *
 * 아무 실패나 로그아웃시키면 안 됩니다 — 서버가 잠깐 500을 내거나 네트워크가
 * 깜빡였을 뿐인데 하던 대화가 날아갑니다. 폴링은 다음 주기에 다시 시도하므로
 * 조용히 넘기고, 정말 인증이 죽었을 때만 내보냅니다.
 */
export function isAuthError(error: unknown): boolean {
  if (!(error instanceof ApiError)) {
    // fetch 자체가 실패한 경우(TypeError 등)는 인증 문제가 아닙니다.
    return false;
  }

  // 401이 여기까지 왔다는 건 client.ts가 토큰 갱신을 시도했다가 그것마저
  // 실패했다는 뜻입니다 — 진짜로 세션이 끝난 겁니다.
  return (
    error.status === 401 ||
    error.code === "TOKEN_EXPIRED" ||
    error.code === "AUTHENTICATION_REQUIRED"
  );
}

export function toUserMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.userMessage;
  }

  if (error instanceof TypeError) {
    // fetch 자체가 실패한 경우 (네트워크 단절, CORS 등)
    return "서버에 연결하지 못했어요. 네트워크를 확인해주세요.";
  }

  return fallbackMessage;
}
