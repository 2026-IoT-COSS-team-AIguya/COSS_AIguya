import { apiError, requireAuth } from "@/lib/mock/http";
import { getTranslationById } from "@/lib/mock/store";

// SignTranslationDetailAPIView (명세 19장)
// 명세 5.2: 프론트가 1초마다 이걸 조회하고, COMPLETED/FAILED가 되면 중지합니다.
export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const { id } = await context.params;
  const translation = getTranslationById(Number(id));

  if (!translation) {
    return apiError(404, "CONVERSATION_NOT_FOUND", "번역 결과를 찾을 수 없습니다.");
  }

  // 명세 9장: 수어 인식 실패는 HTTP 오류가 아니라 200 OK + status: FAILED로 전달합니다.
  // 요청 자체는 정상 처리된 것이기 때문입니다.
  return Response.json(translation);
}
