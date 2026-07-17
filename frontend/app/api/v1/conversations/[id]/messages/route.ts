import { apiError, requireAuth } from "@/lib/mock/http";
import { fetchMessagesAfter, getConversationById } from "@/lib/mock/store";

// ConversationMessageListAPIView (명세 19장)
// 명세 5.1: 프론트는 화면 활성화 중 2초 간격으로 폴링하고, 신규 메시지는 after_id로 받아갑니다.
export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  // Next 16에서 동적 세그먼트 params는 Promise입니다.
  const { id } = await context.params;
  const conversationId = Number(id);
  const conversation = getConversationById(conversationId);

  if (!conversation) {
    return apiError(404, "CONVERSATION_NOT_FOUND", "대화를 찾을 수 없습니다.");
  }

  if (!conversation.participants.some((participant) => participant.id === user.id)) {
    return apiError(
      403,
      "CONVERSATION_ACCESS_DENIED",
      "이 대화에 접근할 권한이 없습니다."
    );
  }

  const afterIdParam = new URL(request.url).searchParams.get("after_id");
  const afterId = afterIdParam === null ? undefined : Number(afterIdParam);

  const messages = fetchMessagesAfter(conversationId, afterId);

  // last_message_id는 신규분이 없어도 클라이언트가 커서를 유지할 수 있어야 하므로
  // afterId로 물러섭니다 (명세 5.1의 has_new_messages: false 예시).
  const lastMessageId =
    messages.length > 0 ? messages[messages.length - 1].id : afterId ?? 0;

  return Response.json({
    has_new_messages: messages.length > 0,
    last_message_id: lastMessageId,
    messages,
  });
}
