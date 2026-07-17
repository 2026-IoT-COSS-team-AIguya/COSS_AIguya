import { cookies } from "next/headers";

import { REFRESH_COOKIE, apiError, issueAccessToken } from "@/lib/mock/http";
import { getUserById, store } from "@/lib/mock/store";

export async function POST() {
  const cookieStore = await cookies();
  const token = cookieStore.get(REFRESH_COOKIE)?.value;

  if (!token) {
    return apiError(401, "AUTHENTICATION_REQUIRED", "로그인이 필요합니다.");
  }

  const userId = store.sessions.get(token);

  if (userId === undefined || !getUserById(userId)) {
    return apiError(401, "TOKEN_EXPIRED", "세션이 만료되었습니다.");
  }

  return Response.json({ access: issueAccessToken(userId) });
}
