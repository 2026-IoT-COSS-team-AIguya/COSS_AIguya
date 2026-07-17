import { apiError, requireAuth } from "@/lib/mock/http";
import {
  appendMessage,
  buildSignVideoSequence,
  getConversationById,
} from "@/lib/mock/store";

// SignVideoSequenceMessageCreateAPIView (명세 19장)
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

  const body = (await request.json()) as { keywords?: string[] };
  const keywords = body.keywords?.filter(Boolean) ?? [];

  if (keywords.length === 0) {
    return apiError(400, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      keywords: ["키워드를 하나 이상 보내주세요."],
    });
  }

  const message = appendMessage({
    conversationId,
    type: "SIGN_VIDEO_SEQUENCE",
    senderId: user.id,
    // 명세 7.2: 요청받은 키워드 순서를 유지합니다.
    sequence: buildSignVideoSequence(keywords),
  });

  return Response.json(message, { status: 201 });
}
