import { apiError, requireAuth } from "@/lib/mock/http";
import { getConversationById } from "@/lib/mock/store";

// ConversationDetailAPIView (명세 19장)
export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const { id } = await context.params;
  const conversation = getConversationById(Number(id));

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

  return Response.json(conversation);
}
