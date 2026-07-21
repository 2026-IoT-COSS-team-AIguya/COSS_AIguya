"use client";

import { useCallback, useEffect, useState } from "react";

import { listFriends } from "@/lib/api/endpoints";
import type { FriendListResponse } from "@/lib/types";

// 상대가 보낸 친구 신청이 실시간처럼 보이도록 폴링합니다.
// 메시지(2초)만큼 급하지 않아 조금 느슨하게 둡니다.
const POLL_INTERVAL_MS = 5000;

const EMPTY: FriendListResponse = {
  friends: [],
  incoming_requests: [],
  outgoing_requests: [],
};

export function useFriends(enabled: boolean) {
  // null = 아직 첫 응답 전. loading을 따로 상태로 들지 않고 여기서 파생시킵니다.
  const [data, setData] = useState<FriendListResponse | null>(null);

  // 친구를 수락/거절한 직후엔 5초를 기다리지 않고 바로 다시 받아옵니다.
  // 토큰을 바꿔 effect를 다시 돌리는 방식이라, 조회 로직이 effect 안에 한 벌만 있습니다.
  const [reloadToken, setReloadToken] = useState(0);

  const refresh = useCallback(() => {
    setReloadToken((token) => token + 1);
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const controller = new AbortController();

    const load = async () => {
      try {
        const result = await listFriends(controller.signal);

        if (controller.signal.aborted) {
          return;
        }

        setData(result);
      } catch {
        // 실패는 조용히 넘깁니다. 다음 주기에 다시 시도하므로 오류를 띄우지 않습니다.
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
  }, [enabled, reloadToken]);

  return {
    ...(data ?? EMPTY),
    loading: data === null,
    refresh,
  };
}
