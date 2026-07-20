"""generate_sentence.py / extract_keywords.py가 같이 쓰는 Gemini 호출 공통 로직."""
from __future__ import annotations

import json
import os
import time

# conda 환경의 SSL_CERT_FILE이 존재하지 않는 경로를 가리키면(예: 이 환경에서
# envs/coss/ssl/cacert.pem이 없는 경우) genai.Client() 생성 시
# ssl.create_default_context()가 FileNotFoundError를 던진다. certifi가 제공하는
# 정상 인증서로 대체해서 이 문제를 우회한다.
if not os.path.exists(os.environ.get("SSL_CERT_FILE", "")):
    import certifi

    os.environ["SSL_CERT_FILE"] = certifi.where()

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

RETRYABLE_CODES = {429, 500, 503}  # 쿼터 초과/서버 과부하 -- 잠깐 쉬었다 재시도하면 되는 것들


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY가 설정되어 있지 않습니다.\n"
            "프로젝트 루트에 .env 파일을 만들고 GEMINI_API_KEY=... 를 채워주세요 "
            "(.env.example 참고, https://aistudio.google.com/apikey 에서 무료 발급)."
        )
    return genai.Client(api_key=api_key)


def generate_json(
    client: genai.Client,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float,
    max_retries: int = 2,
) -> dict:
    """JSON 모드로 호출해서 dict로 파싱.

    데모 도중 Gemini가 잠깐 과부하(503)나 순간 쿼터 초과(429)로 삐끗하는 경우가
    실제로 있어서, 그런 일시적 에러는 짧게 쉬었다가 재시도한다.
    """
    for attempt in range(max_retries + 1):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=temperature,
                ),
            )
            # response_mime_type="application/json"을 줘도 가끔 JSON 뒤에 여분
            # 텍스트가 붙어 나올 때가 있어서(json.loads가 "Extra data" 에러를
            # 냄), raw_decode로 맨 앞의 JSON 값 하나만 파싱하고 뒤는 무시한다.
            data, _ = json.JSONDecoder().raw_decode(resp.text.strip())
            return data
        except genai_errors.APIError as e:
            if e.code not in RETRYABLE_CODES or attempt == max_retries:
                raise
            time.sleep(1.5 * (attempt + 1))
