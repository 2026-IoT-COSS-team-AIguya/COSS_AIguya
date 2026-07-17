import { apiError, requireAuth } from "@/lib/mock/http";
import { createSignTranslation, getConversationById } from "@/lib/mock/store";

// 명세 7.1
const ALLOWED_TYPES = ["video/mp4", "video/webm"];
const MAX_BYTES = 50 * 1024 * 1024; // 50MB

// SignTranslationCreateAPIView (명세 19장)
// 파일 크기와 MIME 타입 검증은 명세 20장 체크리스트에서 Serializer 책임으로 못박혀 있습니다.
export async function POST(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const formData = await request.formData();
  const video = formData.get("input_video");
  const conversationId = Number(formData.get("conversation_id"));

  if (!(video instanceof File)) {
    return apiError(400, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      input_video: ["영상 파일을 첨부해주세요."],
    });
  }

  // MIME 타입은 "video/webm;codecs=vp9"처럼 파라미터가 붙어 오므로 앞부분만 봅니다.
  const mimeType = video.type.split(";")[0].trim();

  if (!ALLOWED_TYPES.includes(mimeType)) {
    // 명세 9장: 지원하지 않는 영상 형식은 415
    return apiError(
      415,
      "UNSUPPORTED_VIDEO_TYPE",
      "지원하지 않는 영상 형식입니다."
    );
  }

  if (video.size > MAX_BYTES) {
    // 명세 9장: 영상 용량 초과는 413
    return apiError(413, "VIDEO_TOO_LARGE", "영상 크기가 너무 큽니다.");
  }

  if (!getConversationById(conversationId)) {
    return apiError(404, "CONVERSATION_NOT_FOUND", "대화를 찾을 수 없습니다.");
  }

  // 목 단계에서는 영상 바이트를 보관하지 않고 접수만 합니다.
  // 실제 프-백은 여기서 파일을 저장하고 submit_translation_to_ai로 인-백에 넘깁니다.
  const translation = createSignTranslation(conversationId);

  // 명세 9장: AI 분석 요청 접수는 202 Accepted
  // 명세 5.2: 업로드 직후 응답은 id/status/created_at
  return Response.json(
    {
      id: translation.id,
      status: translation.status,
      created_at: translation.created_at,
    },
    { status: 202 }
  );
}
