import { cookies } from "next/headers";

import { REFRESH_COOKIE, clearRefreshCookie } from "@/lib/mock/http";
import { store } from "@/lib/mock/store";

export async function POST() {
  const cookieStore = await cookies();
  const token = cookieStore.get(REFRESH_COOKIE)?.value;

  if (token) {
    store.sessions.delete(token);
  }

  // 명세 9장: 로그아웃 성공은 204 No Content
  return new Response(null, {
    status: 204,
    headers: { "Set-Cookie": clearRefreshCookie() },
  });
}
