import { api, refreshAccessToken, setAccessToken } from "@/lib/api/client";
import { request } from "@/lib/api/client";
import type {
  Conversation,
  FriendListResponse,
  Friendship,
  LoginResponse,
  Message,
  MessageListResponse,
  QuickKeyword,
  SentenceToSequenceResponse,
  SignTranslation,
  SignTranslationCreated,
  SignVideoSequenceItem,
  User,
  UserRole,
} from "@/lib/types";

// --- accounts ---

export async function login(nickname: string, password: string) {
  // 로그인 실패(401)에 refresh 재시도를 걸면 안 되므로 skipAuthRetry를 씁니다.
  const result = await request<LoginResponse>("/auth/login/", {
    method: "POST",
    json: { nickname, password },
    skipAuthRetry: true,
  });

  setAccessToken(result.access);
  return result;
}

// 닉네임이 곧 아이디입니다 — 친구 추가도 이 닉네임으로 서로를 찾습니다.
// 가입에 성공하면 바로 로그인된 상태가 됩니다 (백엔드가 201과 함께 토큰을 줍니다).
export async function signup(
  nickname: string,
  password: string,
  role: UserRole
) {
  const result = await request<LoginResponse>("/auth/signup/", {
    method: "POST",
    json: { nickname, password, role },
    // 가입 실패(400)에 토큰 갱신 재시도를 걸 이유가 없습니다.
    skipAuthRetry: true,
  });

  setAccessToken(result.access);
  return result;
}

export async function logout() {
  await api.post<void>("/auth/logout/");
  setAccessToken(null);
}

export function getMyProfile() {
  return api.get<User>("/users/me/");
}

/**
 * 새로고침 후 로그인 상태를 되살립니다. 살릴 수 없으면 null.
 *
 * 명세 10장대로 Access Token은 메모리에만 두므로 새로고침하면 사라집니다.
 * 하지만 Refresh Token은 HttpOnly 쿠키(7일)라 살아 있습니다 — 그걸로 Access를
 * 다시 받아오면 로그인 화면을 다시 보여주지 않아도 됩니다.
 *
 * 이게 없으면 새로고침할 때마다, 개발 중에는 파일을 저장할 때마다 로그아웃됩니다.
 */
export async function restoreSession(): Promise<User | null> {
  const refreshed = await refreshAccessToken();

  if (!refreshed) {
    // 쿠키가 없거나 만료됨 = 그냥 로그인 안 된 상태입니다. 오류가 아닙니다.
    return null;
  }

  try {
    return await getMyProfile();
  } catch {
    setAccessToken(null);
    return null;
  }
}

export function updateNickname(nickname: string) {
  return api.patch<User>("/users/me/nickname/", { nickname });
}

export function completeOnboarding() {
  return api.post<User>("/users/me/onboarding-complete/");
}

// --- friends ---

export function listFriends(signal?: AbortSignal) {
  return api.get<FriendListResponse>("/friends/", signal);
}

// 닉네임으로 친구를 찾아 신청합니다.
export function sendFriendRequest(nickname: string) {
  return api.post<Friendship>("/friends/requests/", { nickname });
}

export function acceptFriendRequest(friendshipId: number) {
  return api.post<Friendship>(`/friends/requests/${friendshipId}/accept/`);
}

export function rejectFriendRequest(friendshipId: number) {
  return api.post<Friendship>(`/friends/requests/${friendshipId}/reject/`);
}

// --- conversations ---

// 백엔드가 최근 메시지순(-updated_at)으로 정렬해서 돌려줍니다.
export function listConversations(signal?: AbortSignal) {
  return api.get<Conversation[]>("/conversations/", signal);
}

// 친구와 대화를 시작합니다.
export function createConversation(params: {
  title: string;
  icon?: string;
  category?: string;
  participant_nicknames: string[];
}) {
  return api.post<Conversation>("/conversations/", params);
}

export function getConversation(conversationId: number) {
  return api.get<Conversation>(`/conversations/${conversationId}/`);
}

export function joinConversation(code: string) {
  return api.post<Conversation>("/conversations/join/", { code });
}

export function markConversationRead(conversationId: number) {
  return api.post<void>(`/conversations/${conversationId}/read/`);
}

// 명세 5.1 / 12장: 신규 메시지는 after_id 방식으로 추가합니다.
export function fetchMessages(
  conversationId: number,
  afterId?: number,
  signal?: AbortSignal
) {
  const query = afterId ? `?after_id=${afterId}` : "";

  return api.get<MessageListResponse>(
    `/conversations/${conversationId}/messages/${query}`,
    signal
  );
}

export function createTextMessage(conversationId: number, text: string) {
  return api.post<Message>(`/conversations/${conversationId}/messages/text/`, {
    text,
  });
}

export function createTranslationMessage(
  conversationId: number,
  translationId: number
) {
  return api.post<Message>(
    `/conversations/${conversationId}/messages/translation/`,
    { translation_id: translationId }
  );
}

export function createSignVideoSequenceMessage(
  conversationId: number,
  keywords: string[]
) {
  // 명세 7.2: 백엔드는 요청받은 키워드 순서를 유지해야 합니다.
  return api.post<Message>(
    `/conversations/${conversationId}/messages/sign-video-sequence/`,
    { keywords }
  );
}

// --- capture target ---

// 촬영은 아두이노 물리 버튼이 시작하므로, 라즈베리파이는 내가 채팅방을 보고 있는지
// 번역기를 보고 있는지 모릅니다. 화면을 옮길 때마다 여기에 등록해두면, 업로드가
// 들어올 때 백엔드가 읽어서 알맞은 곳으로 보냅니다.
// conversationId가 null이면 번역기 모드(대면)입니다.
export function setCaptureTarget(conversationId: number | null) {
  return api.put<{ conversation_id: number | null; mode: "CHAT" | "TRANSLATOR" }>(
    "/capture-target/",
    { conversation_id: conversationId }
  );
}

// --- translations ---

// 명세 7.1: multipart/form-data, 필드명 input_video, video/mp4 또는 video/webm
//
// conversationId가 null이면 번역기 모드(대면)로 올라갑니다 — 대화방 없이 그 자리에서
// 번역만 하고, 번역기 화면이 /sign-translations/latest/ 로 결과를 받아갑니다.
// 값을 주면 그 대화방으로 올라가고, 분석이 끝나면 백엔드가 메시지를 자동으로 만듭니다.
export function createSignTranslation(
  conversationId: number | null,
  video: Blob,
  filename: string
) {
  const formData = new FormData();
  formData.append("input_video", video, filename);

  if (conversationId !== null) {
    formData.append("conversation_id", String(conversationId));
  }

  return api.upload<SignTranslationCreated>("/sign-translations/", formData);
}

export function getSignTranslation(
  translationId: number,
  signal?: AbortSignal
) {
  return api.get<SignTranslation>(`/sign-translations/${translationId}/`, signal);
}

// 촬영은 웹이 아니라 아두이노 물리 버튼이 시작하므로, 프론트는 업로드 응답으로
// id를 받을 수 없습니다. 대신 번역기 화면이 "가장 최근 촬영"을 폴링합니다.
export function getLatestSignTranslation(signal?: AbortSignal) {
  return api.get<{ translation: SignTranslation | null }>(
    "/sign-translations/latest/",
    signal
  );
}

export function retrySignTranslation(translationId: number) {
  return api.post<SignTranslationCreated>(
    `/sign-translations/${translationId}/retry/`
  );
}

// --- sign_videos ---

export function listQuickKeywords() {
  return api.get<QuickKeyword[]>("/quick-keywords/");
}

export function previewSignVideoSequence(keywords: string[]) {
  return api.post<SignVideoSequenceItem[]>("/sign-videos/sequence-preview/", {
    keywords,
  });
}

// 쉼표로 끊지 않고 문장을 그대로 보냅니다. AI가 사전 안의 키워드로 분해합니다.
export function sentenceToSignSequence(sentence: string) {
  return api.post<SentenceToSequenceResponse>(
    "/sign-videos/sentence-to-sequence/",
    { sentence }
  );
}

export function searchSignVideos(keyword: string) {
  return api.get<SignVideoSequenceItem[]>(
    `/sign-videos/?keyword=${encodeURIComponent(keyword)}`
  );
}
