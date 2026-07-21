// 프-백 API 계약 타입. 명세 11장 "DB 구조" / 19장 "최종 이름 목록"의 이름을 그대로 씁니다.
// 프론트는 DB 내부 구조가 아니라 이 JSON 형식에만 의존합니다 (명세 11장).

// 명세 12장: 메시지는 세 유형으로 구분해 표시합니다.
// 필담(기존 목업의 "memo")은 대응 유형이 없어 TEXT로 보냅니다.
export type MessageType = "TEXT" | "SIGN_TRANSLATION" | "SIGN_VIDEO_SEQUENCE";

// 명세 6장: 양쪽 백엔드가 동일하게 사용하는 AI 처리 상태.
export type TranslationStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

// 명세 6장의 상태별 프론트 표시 문구.
export const translationStatusLabel: Record<TranslationStatus, string> = {
  PENDING: "분석을 준비하고 있어요",
  PROCESSING: "수어를 분석하고 있어요",
  COMPLETED: "분석이 완료되었어요",
  FAILED: "수어를 인식하지 못했어요",
};

export type UserRole = "SIGN_USER" | "HEARING_USER";

export type User = {
  id: number;
  nickname: string;
  // 이모지 아이디와 함께 보여줄 한글 이름(선택). 비워두면 빈 문자열.
  display_name: string;
  role: UserRole;
  onboarding_completed: boolean;
};

export type ConversationParticipant = {
  id: number;
  nickname: string;
  display_name: string;
  role: UserRole;
};

export type FriendRequestStatus = "PENDING" | "ACCEPTED" | "REJECTED";

export type Friendship = {
  id: number;
  requester: User;
  addressee: User;
  status: FriendRequestStatus;
  created_at: string;
};

export type FriendListResponse = {
  friends: User[];
  // 내가 답해야 할 신청
  incoming_requests: Friendship[];
  // 내가 보내고 기다리는 신청
  outgoing_requests: Friendship[];
};

export type Conversation = {
  id: number;
  title: string;
  icon: string;
  category: string;
  code: string;
  participants: ConversationParticipant[];
  last_message_preview: string | null;
  unread_count: number;
};

export type MessageSender = {
  id: number;
  nickname: string;
  display_name: string;
  role: UserRole;
};

export type RecognizedKeyword = {
  keyword: string;
  confidence: number;
  position: number;
};

export type SignVideo = {
  id: number;
  keyword: string;
  title: string;
  emoji: string;
  // 명세 7.2: 백엔드는 절대 URL을 반환합니다.
  // AI 개발 완료 후 AI DB에서 공급될 예정이라, 그때까지 대부분 null입니다.
  video_url: string | null;
};

export type SignVideoSequenceItem = {
  position: number;
  sign_video: SignVideo;
};

// 자유 문장을 AI가 사전 안의 키워드로 분해한 결과.
// 사전에 겹치는 단어가 없으면 오류가 아니라 빈 배열입니다.
export type SentenceToSequenceResponse = {
  keywords: string[];
  sequence: SignVideoSequenceItem[];
};

export type SignTranslation = {
  id: number;
  status: TranslationStatus;
  created_at: string;
  recognized_keywords: RecognizedKeyword[];
  sentence_candidates: string[];
  error: ApiErrorBody | null;
};

// 업로드 직후 202 응답 (명세 5.2)
export type SignTranslationCreated = {
  id: number;
  status: TranslationStatus;
  created_at: string;
};

export type Message = {
  id: number;
  conversation: number;
  type: MessageType;
  sender: MessageSender;
  created_at: string;
  // TEXT
  text: string | null;
  // SIGN_TRANSLATION
  sign_translation: SignTranslation | null;
  // SIGN_VIDEO_SEQUENCE
  sign_video_sequence: SignVideoSequenceItem[];
};

// 명세 5.1: 메시지 폴링 응답
export type MessageListResponse = {
  has_new_messages: boolean;
  last_message_id: number;
  messages: Message[];
};

export type QuickKeyword = {
  id: number;
  keyword: string;
  emoji: string;
  position: number;
};

// 명세 8장: 모든 API 오류의 공통 형식
export type ApiErrorBody = {
  code: string;
  message: string;
  fields?: Record<string, string[]>;
};

export type LoginResponse = {
  access: string;
  user: User;
};

export const roleLabel: Record<UserRole, string> = {
  SIGN_USER: "농인 (수어 사용자)",
  HEARING_USER: "비장애인 / 직원",
};

// 이모지 아이디에 한글 이름이 있으면 "🐶🍎⭐ (민지)" 형태로, 없으면 아이디만.
export function withDisplayName(
  nickname: string,
  displayName?: string | null
): string {
  const name = displayName?.trim();
  return name ? `${nickname} (${name})` : nickname;
}
