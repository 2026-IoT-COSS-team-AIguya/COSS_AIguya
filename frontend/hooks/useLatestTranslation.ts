"use client";

import { useEffect, useRef, useState } from "react";

import { getLatestSignTranslation } from "@/lib/api/endpoints";
import type { SignTranslation } from "@/lib/types";

// 촬영을 기다리는 동안은 느슨하게, 분석이 시작되면 명세 5.2의 1초 간격으로 좁힙니다.
const IDLE_INTERVAL_MS = 2000;
const ACTIVE_INTERVAL_MS = 1000;

// 명세 5.2: 최대 60초가 지나면 처리 지연 안내를 표시합니다.
const SLOW_NOTICE_MS = 60_000;

/**
 * 번역기 화면이 "가장 최근 촬영"을 지켜봅니다.
 *
 * 촬영은 웹 버튼이 아니라 아두이노 물리 버튼이 시작하므로, 프론트는 시작 시점을
 * 알 수 없습니다. 그래서 최근 건을 계속 폴링하다가 새 id가 나타나면 그때부터
 * 분석 과정을 따라갑니다.
 */
export function useLatestTranslation(enabled: boolean) {
  const [translation, setTranslation] = useState<SignTranslation | null>(null);
  const [isSlow, setIsSlow] = useState(false);

  // 분석 중인 건이 언제 시작됐는지. 지연 안내 판단에 씁니다.
  const activeSinceRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const poll = async () => {
      try {
        const result = await getLatestSignTranslation(controller.signal);

        if (cancelled) {
          return;
        }

        const latest = result.translation;
        setTranslation(latest);

        const analyzing =
          latest !== null &&
          (latest.status === "PENDING" || latest.status === "PROCESSING");

        if (analyzing) {
          activeSinceRef.current ??= Date.now();
          setIsSlow(Date.now() - activeSinceRef.current > SLOW_NOTICE_MS);
        } else {
          activeSinceRef.current = null;
          setIsSlow(false);
        }

        // 분석 중이면 1초, 촬영을 기다리는 중이면 2초.
        schedule(analyzing ? ACTIVE_INTERVAL_MS : IDLE_INTERVAL_MS);
      } catch {
        // 일시적 실패는 다음 주기에 다시 시도합니다.
        schedule(IDLE_INTERVAL_MS);
      }
    };

    const schedule = (delay: number) => {
      if (cancelled) {
        return;
      }

      timer = setTimeout(() => {
        // 화면이 안 보일 때는 굳이 부르지 않습니다.
        if (document.visibilityState === "visible") {
          poll();
        } else {
          schedule(delay);
        }
      }, delay);
    };

    poll();

    return () => {
      cancelled = true;
      controller.abort();

      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [enabled]);

  return { translation, isSlow };
}
