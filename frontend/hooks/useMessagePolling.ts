"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchMessages } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/errors";
import type { Message } from "@/lib/types";

// 명세 12장: 채팅 메시지는 화면 활성화 중 2초 간격으로 폴링합니다.
const POLL_INTERVAL_MS = 2000;

export function useMessagePolling(
  conversationId: number | null,
  onAuthExpired: () => void
) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(conversationId !== null);

  // 방을 바꾸면 이전 방의 메시지가 잠깐 보이면 안 됩니다.
  // effect에서 비우면 한 프레임 동안 남으므로 렌더 중에 조정합니다.
  const [trackedId, setTrackedId] = useState(conversationId);

  if (trackedId !== conversationId) {
    setTrackedId(conversationId);
    setMessages([]);
    setLoading(conversationId !== null);
  }

  // 명세 12장: 신규 메시지는 after_id 방식으로 추가합니다.
  const lastMessageIdRef = useRef(0);

  const poll = useCallback(
    async (signal?: AbortSignal) => {
      if (conversationId === null) {
        return;
      }

      try {
        const result = await fetchMessages(
          conversationId,
          lastMessageIdRef.current || undefined,
          signal
        );

        if (signal?.aborted) {
          return;
        }

        if (result.has_new_messages && result.messages.length > 0) {
          lastMessageIdRef.current = result.last_message_id;
          setMessages((previous) => {
            // 내가 보내 이미 붙인 메시지가 폴링으로 또 올 수 있습니다.
            const known = new Set(previous.map((item) => item.id));
            const fresh = result.messages.filter((item) => !known.has(item.id));

            return fresh.length > 0 ? [...previous, ...fresh] : previous;
          });
        }
      } catch (cause) {
        if (signal?.aborted) {
          return;
        }

        if (cause instanceof ApiError && cause.status === 401) {
          onAuthExpired();
        }

        // 그 외 폴링 실패는 다음 주기에 다시 시도하므로 화면에 띄우지 않습니다.
      }
    },
    [conversationId, onAuthExpired]
  );

  useEffect(() => {
    if (conversationId === null) {
      return;
    }

    const controller = new AbortController();

    lastMessageIdRef.current = 0;

    poll(controller.signal).finally(() => {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    });

    // 명세 12장: 화면 활성화 중에만 폴링합니다.
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") {
        poll(controller.signal);
      }
    }, POLL_INTERVAL_MS);

    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [conversationId, poll]);

  // 내가 보낸 메시지는 폴링을 기다리지 않고 즉시 붙입니다.
  const appendLocal = useCallback((message: Message) => {
    setMessages((previous) => {
      if (previous.some((item) => item.id === message.id)) {
        return previous;
      }

      return [...previous, message];
    });

    lastMessageIdRef.current = Math.max(lastMessageIdRef.current, message.id);
  }, []);

  return { messages, loading, appendLocal, refresh: poll };
}
