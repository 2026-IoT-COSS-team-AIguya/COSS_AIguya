"use client";

import { useCallback, useEffect, useState } from "react";

import { listConversations } from "@/lib/api/endpoints";
import { isAuthError } from "@/lib/api/errors";
import type { Conversation } from "@/lib/types";

// 백엔드가 최근 메시지순(-updated_at)으로 돌려주므로, 주기적으로 다시 받아오면
// 방금 메시지가 온 대화가 알아서 위로 올라옵니다. 안 읽은 개수도 같이 갱신됩니다.
// 목록은 방 안 메시지(2초)만큼 급하지 않아 조금 느슨하게 둡니다.
const POLL_INTERVAL_MS = 4000;

export function useConversations(
  enabled: boolean,
  onAuthExpired: () => void
) {
  // null = 아직 첫 응답 전.
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  // 대화를 새로 만든 직후엔 다음 주기를 기다리지 않고 바로 받아옵니다.
  const refresh = useCallback(() => {
    setReloadToken((token) => token + 1);
  }, []);

  useEffect(() => {
    if (!enabled) {
      const resetTimer = window.setTimeout(() => {
        setConversations(null);
      }, 0);

      return () => {
        window.clearTimeout(resetTimer);
      };
    }

    const controller = new AbortController();

    const load = async () => {
      try {
        const result = await listConversations(controller.signal);

        if (controller.signal.aborted) {
          return;
        }

        setConversations(result);
      } catch (cause) {
        // 인증이 죽었을 때만 로그인 화면으로 보냅니다. 서버가 잠깐 500을 내거나
        // 네트워크가 깜빡인 것까지 로그아웃시키면 하던 대화가 날아갑니다 —
        // 폴링은 다음 주기에 알아서 다시 시도합니다.
        if (!controller.signal.aborted && isAuthError(cause)) {
          onAuthExpired();
        }
      }
    };

    load();

    const timer = setInterval(() => {
      if (document.visibilityState === "visible") {
        load();
      }
    }, POLL_INTERVAL_MS);

    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [enabled, reloadToken, onAuthExpired]);

  return {
    conversations: enabled ? conversations ?? [] : [],
    loading: enabled && conversations === null,
    refresh,
  };
}
