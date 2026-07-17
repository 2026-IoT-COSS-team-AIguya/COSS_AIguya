import { apiError, requireAuth } from "@/lib/mock/http";
import {
  getTranslationById,
  saveTranslationResult,
  setTranslationProcessing,
} from "@/lib/mock/store";

// SignTranslationRetryAPIView (명세 19장)
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const { id } = await context.params;
  const translationId = Number(id);
  const translation = getTranslationById(translationId);

  if (!translation) {
    return apiError(404, "CONVERSATION_NOT_FOUND", "번역 결과를 찾을 수 없습니다.");
  }

  translation.status = "PENDING";
  translation.error = null;
  translation.recognized_keywords = [];
  translation.sentence_candidates = [];

  setTimeout(() => setTranslationProcessing(translationId), 1200);
  setTimeout(() => saveTranslationResult(translationId), 3600);

  return Response.json(
    {
      id: translation.id,
      status: translation.status,
      created_at: translation.created_at,
    },
    { status: 202 }
  );
}
