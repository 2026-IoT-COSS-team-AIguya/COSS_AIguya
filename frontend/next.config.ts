import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API 명세가 Django 관례대로 끝에 슬래시를 붙입니다 (예: /api/v1/sign-translations/27/).
  // Next는 기본적으로 슬래시를 떼며 308 리다이렉트를 걸기 때문에, 목 백엔드가
  // Django 프-백과 동일한 URL로 응답하도록 맞춥니다.
  trailingSlash: true,
};

export default nextConfig;
