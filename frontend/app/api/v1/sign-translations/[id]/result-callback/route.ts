import { apiError } from "@/lib/mock/http";
import {
  appendMessage,
  getConversationById,
  getTranslationById,
  setTranslationFailed,
  store,
} from "@/lib/mock/store";
import type { RecognizedKeyword } from "@/lib/types";

// SignTranslationResultCallbackAPIView (명세 18.1 / 19장)
//
// 인-백이 send_translation_result로 호출하는 엔드포인트입니다.
// 모델이 준비되면 인-백이 여기로 결과를 쏘면 되고, 그때 store.ts의
// fakePredictSignKeywords 기반 타이머는 제거합니다.

// 명세 20장: AI 콜백에는 내부 API Key 인증을 적용합니다.
// 사용자 JWT가 아니라 서버 간 인증이라 requireAuth를 쓰지 않습니다.
const INTERNAL_API_KEY = process.env.AI_CALLBACK_API_KEY ?? "dev-internal-key";

export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  if (request.headers.get("x-internal-api-key") !== INTERNAL_API_KEY) {
    return apiError(401, "AUTHENTICATION_REQUIRED", "내부 인증에 실패했습니다.");
  }

  const { id } = await context.params;
  // 명세 20장: 인-백 연동 식별자는 translation_id로 통일합니다.
  const translationId = Number(id);
  const translation = getTranslationById(translationId);

  if (!translation) {
    return apiError(404, "CONVERSATION_NOT_FOUND", "번역 작업을 찾을 수 없습니다.");
  }

  const body = (await request.json()) as {
    status?: "COMPLETED" | "FAILED";
    recognized_keywords?: RecognizedKeyword[];
    sentence_candidates?: string[];
    error?: { code: string; message: string };
  };

  // 명세 20장: 콜백을 중복 수신해도 결과 저장이 중복되지 않아야 합니다.
  if (translation.status === "COMPLETED" || translation.status === "FAILED") {
    return Response.json(translation);
  }

  if (body.status === "FAILED") {
    setTranslationFailed(
      translationId,
      body.error?.code ?? "SIGN_NOT_DETECTED",
      body.error?.message ?? "영상에서 수어 동작을 찾지 못했습니다."
    );

    return Response.json(getTranslationById(translationId));
  }

  translation.status = "COMPLETED";
  translation.recognized_keywords = body.recognized_keywords ?? [];
  translation.sentence_candidates = body.sentence_candidates ?? [];
  translation.error = null;

  const conversationId = store.translationConversation.get(translationId);

  if (conversationId !== undefined) {
    const alreadyPosted = store.messages.some(
      (message) => message.sign_translation?.id === translationId
    );

    if (!alreadyPosted) {
      const signUser = getConversationById(conversationId)?.participants.find(
        (participant) => participant.role === "SIGN_USER"
      );

      appendMessage({
        conversationId,
        type: "SIGN_TRANSLATION",
        senderId: signUser?.id ?? 1,
        translation,
      });
    }
  }

  return Response.json(translation);
}
