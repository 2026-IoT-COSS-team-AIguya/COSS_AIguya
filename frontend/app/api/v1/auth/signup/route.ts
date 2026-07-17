import {
  apiError,
  issueAccessToken,
  issueRefreshToken,
  refreshCookie,
} from "@/lib/mock/http";
import { createUser, findUserByNickname } from "@/lib/mock/store";
import type { UserRole } from "@/lib/types";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    nickname?: string;
    password?: string;
    role?: UserRole;
  };

  if (!body.nickname || !body.password || !body.role) {
    return apiError(400, "VALIDATION_ERROR", "입력값을 확인해주세요.");
  }

  if (findUserByNickname(body.nickname)) {
    // 명세 9장: 닉네임 중복은 409 Conflict
    return apiError(409, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      nickname: ["이미 사용 중인 닉네임입니다."],
    });
  }

  const user = createUser(body.nickname, body.password, body.role);

  return Response.json(
    {
      access: issueAccessToken(user.id),
      user: {
        id: user.id,
        nickname: user.nickname,
        role: user.role,
        onboarding_completed: user.onboarding_completed,
      },
    },
    {
      status: 201,
      headers: { "Set-Cookie": refreshCookie(issueRefreshToken(user.id)) },
    }
  );
}
