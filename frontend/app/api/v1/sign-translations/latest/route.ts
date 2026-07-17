import { requireAuth } from "@/lib/mock/http";
import { store } from "@/lib/mock/store";

// 번역기 화면이 지켜보는 "가장 최근 촬영".
// 촬영은 아두이노 물리 버튼이 시작하므로 프론트는 업로드 응답으로 id를 받을 수
// 없고, 대신 최근 건을 폴링합니다. 번역기 모드(대면)라 대화방이 없는 건만 봅니다.
export async function GET(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const translation =
    [...store.translations]
      .reverse()
      .find(
        (item) => store.translationConversation.get(item.id) === undefined
      ) ?? null;

  return Response.json({ translation });
}
