import {
  apiError,
  issueAccessToken,
  issueRefreshToken,
  refreshCookie,
} from "@/lib/mock/http";
import { findUserByNickname } from "@/lib/mock/store";

export async function POST(request: Request) {
  const body = (await request.json()) as {
    nickname?: string;
    password?: string;
  };

  if (!body.nickname || !body.password) {
    return apiError(400, "VALIDATION_ERROR", "입력값을 확인해주세요.", {
      nickname: body.nickname ? [] : ["닉네임을 입력해주세요."],
      password: body.password ? [] : ["비밀번호를 입력해주세요."],
    });
  }

  const user = findUserByNickname(body.nickname);

  if (!user || user.password !== body.password) {
    return apiError(
      401,
      "INVALID_CREDENTIALS",
      "아이디 또는 비밀번호가 올바르지 않습니다."
    );
  }

  // 명세 10장: Refresh Token은 JSON 응답에 노출하지 않고 쿠키로 전달합니다.
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
      status: 200,
      headers: { "Set-Cookie": refreshCookie(issueRefreshToken(user.id)) },
    }
  );
}
