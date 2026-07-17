import { apiError, requireAuth } from "@/lib/mock/http";
import {
  appendMessage,
  getConversationById,
  getTranslationById,
  store,
} from "@/lib/mock/store";

// TranslationMessageCreateAPIView (명세 19장)
// 분석이 끝난 번역 결과를 대화에 메시지로 올립니다.
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const { id } = await context.params;
  const conversationId = Number(id);

  if (!getConversationById(conversationId)) {
    return apiError(404, "CONVERSATION_NOT_FOUND", "대화를 찾을 수 없습니다.");
  }

  const body = (await request.json()) as { translation_id?: number };
  const translation =
    body.translation_id === undefined
      ? undefined
      : getTranslationById(body.translation_id);

  if (!translation) {
    return apiError(404, "CONVERSATION_NOT_FOUND", "번역 결과를 찾을 수 없습니다.");
  }

  // 콜백이 이미 메시지를 올렸다면 중복으로 만들지 않고 기존 것을 돌려줍니다
  // (명세 20장: 콜백 중복 수신에도 결과 저장이 중복되지 않게 처리).
  const existing = store.messages.find(
    (message) => message.sign_translation?.id === translation.id
  );

  if (existing) {
    return Response.json(existing, { status: 200 });
  }

  const message = appendMessage({
    conversationId,
    type: "SIGN_TRANSLATION",
    senderId: user.id,
    translation,
  });

  return Response.json(message, { status: 201 });
}
