import { apiError, requireAuth } from "@/lib/mock/http";
import { buildSignVideoSequence } from "@/lib/mock/store";

// SignVideoSequencePreviewAPIView (명세 19장)
// 명세 7.2의 요청 형식: { "keywords": ["토요일", "약속", "미안하다"] }
export async function POST(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const body = (await request.json()) as { keywords?: string[] };
  const keywords = body.keywords?.filter(Boolean) ?? [];

  if (keywords.length === 0) {
    return apiError(400, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      keywords: ["키워드를 하나 이상 보내주세요."],
    });
  }

  // 백엔드는 요청받은 키워드 순서를 유지해야 합니다 (명세 7.2).
  return Response.json(buildSignVideoSequence(keywords));
}
