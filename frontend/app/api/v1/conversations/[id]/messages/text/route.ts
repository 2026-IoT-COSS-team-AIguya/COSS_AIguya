import { apiError, requireAuth } from "@/lib/mock/http";
import { appendMessage, getConversationById } from "@/lib/mock/store";

// TextMessageCreateAPIView (명세 19장)
// 기존 목업의 필담(memo)도 명세에 대응 유형이 없어 TEXT로 들어옵니다.
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

  const body = (await request.json()) as { text?: string };
  const text = body.text?.trim();

  if (!text) {
    return apiError(400, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      text: ["내용을 입력해주세요."],
    });
  }

  const message = appendMessage({
    conversationId,
    type: "TEXT",
    senderId: user.id,
    text,
  });

  // 명세 9장: 메시지 생성 성공은 201 Created
  return Response.json(message, { status: 201 });
}
