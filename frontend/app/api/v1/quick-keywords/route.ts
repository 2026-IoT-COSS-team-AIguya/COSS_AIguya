import { requireAuth } from "@/lib/mock/http";
import { getActiveQuickKeywords } from "@/lib/mock/store";

// QuickKeywordListAPIView (명세 19장)
export async function GET(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  return Response.json(getActiveQuickKeywords());
}
