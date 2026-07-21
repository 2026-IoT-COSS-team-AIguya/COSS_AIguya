import type { NextConfig } from "next";

// 브라우저가 Django의 8000번 포트로 직접 접근하면 다른 노트북의 방화벽,
// CORS, 로컬 네트워크 권한에 따라 초기 로그인이 멈출 수 있습니다.
// 브라우저는 같은 출처(/api/v1)만 호출하고 Next 서버가 Django로 프록시합니다.
const djangoOrigin = process.env.DJANGO_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // API 명세가 Django 관례대로 끝에 슬래시를 붙입니다 (예: /api/v1/sign-translations/27/).
  // Next는 기본적으로 슬래시를 떼며 308 리다이렉트를 걸기 때문에, 목 백엔드가
  // Django 프-백과 동일한 URL로 응답하도록 맞춥니다.
  trailingSlash: true,

  async rewrites() {
    return [
      {
        source: "/api/v1/:path*/",
        destination: `${djangoOrigin}/api/v1/:path*/`,
      },
    ];
  },
};

export default nextConfig;
