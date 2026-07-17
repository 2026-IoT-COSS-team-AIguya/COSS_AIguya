import { apiError, requireAuth } from "@/lib/mock/http";
import { getConversationById } from "@/lib/mock/store";

// ConversationReadAPIView (명세 19장)
export async function POST(
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

  conversation.unread_count = 0;

  return new Response(null, { status: 204 });
}
