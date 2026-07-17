"use client";

import { useEffect, useRef, useState } from "react";

import { getSignTranslation } from "@/lib/api/endpoints";
import type { SignTranslation } from "@/lib/types";

// 명세 5.2 / 12장: AI 처리 상태는 1초 간격으로 조회합니다.
const POLL_INTERVAL_MS = 1000;

// 명세 5.2: 최대 60초가 지나면 프론트에서 처리 지연 안내를 표시합니다.
const SLOW_NOTICE_MS = 60_000;

export function useSignTranslationPolling(
  translationId: number | null,
  onSettled?: (translation: SignTranslation) => void
) {
  const [translation, setTranslation] = useState<SignTranslation | null>(null);
  const [isSlow, setIsSlow] = useState(false);

  // translationId가 바뀌면 이전 결과가 잠깐 보이면 안 됩니다.
  // effect에서 setState로 되돌리면 렌더가 한 번 더 도므로,
  // React가 권장하는 "렌더 중 상태 조정" 방식으로 초기화합니다.
  const [trackedId, setTrackedId] = useState(translationId);

  if (trackedId !== translationId) {
    setTrackedId(translationId);
    setTranslation(null);
    setIsSlow(false);
  }

  // 콜백이 매 렌더마다 새로 만들어져도 폴링이 재시작되지 않도록 ref에 담아둡니다.
  // ref 쓰기는 렌더 중이 아니라 effect에서 해야 합니다.
  const onSettledRef = useRef(onSettled);

  useEffect(() => {
    onSettledRef.current = onSettled;
  });

  useEffect(() => {
    if (translationId === null) {
      return;
    }

    const controller = new AbortController();
    let timer: ReturnType<typeof setInterval> | null = null;

    const slowTimer = setTimeout(() => setIsSlow(true), SLOW_NOTICE_MS);

    const stop = () => {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };

    const poll = async () => {
      try {
        const result = await getSignTranslation(translationId, controller.signal);

        if (controller.signal.aborted) {
          return;
        }

        setTranslation(result);

        // 명세 5.2: 상태가 COMPLETED 또는 FAILED가 되면 조회를 중지합니다.
        if (result.status === "COMPLETED" || result.status === "FAILED") {
          stop();
          clearTimeout(slowTimer);
          setIsSlow(false);
          onSettledRef.current?.(result);
        }
      } catch {
        // 일시적 실패는 다음 주기에 다시 시도합니다.
      }
    };

    poll();
    timer = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      controller.abort();
      stop();
      clearTimeout(slowTimer);
    };
  }, [translationId]);

  return { translation, isSlow };
}
