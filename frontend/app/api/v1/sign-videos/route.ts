import { requireAuth } from "@/lib/mock/http";
import { signVideos } from "@/lib/mock/signWords";

// SignVideoSearchAPIView (명세 19장)
export async function GET(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const keyword = new URL(request.url).searchParams.get("keyword")?.trim();

  const matched = keyword
    ? signVideos.filter((video) => video.keyword.includes(keyword))
    : signVideos;

  return Response.json(
    matched.map((video, index) => ({ position: index + 1, sign_video: video }))
  );
}
