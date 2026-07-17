import { apiError, requireAuth } from "@/lib/mock/http";
import { findUserByNickname } from "@/lib/mock/store";

export async function PATCH(request: Request) {
  const { user, response } = requireAuth(request);

  if (!user) {
    return response;
  }

  const body = (await request.json()) as { nickname?: string };
  const nickname = body.nickname?.trim();

  if (!nickname) {
    return apiError(400, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      nickname: ["닉네임을 입력해주세요."],
    });
  }

  const duplicate = findUserByNickname(nickname);

  if (duplicate && duplicate.id !== user.id) {
    return apiError(409, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      nickname: ["이미 사용 중인 닉네임입니다."],
    });
  }

  user.nickname = nickname;

  return Response.json({
    id: user.id,
    nickname: user.nickname,
    role: user.role,
    onboarding_completed: user.onboarding_completed,
  });
}
