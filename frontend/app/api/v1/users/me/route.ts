import { requireAuth } from "@/lib/mock/http";

export async function GET(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  return Response.json({
    id: user.id,
    nickname: user.nickname,
    role: user.role,
    onboarding_completed: user.onboarding_completed,
  });
}
