"use client";

import { useCallback, useEffect, useState } from "react";

import { searchSignVideos } from "@/lib/api/endpoints";
import type { SignVideo } from "@/lib/types";

// 명세의 RecognizedKeyword는 {keyword, confidence, position}이라 이모지가 없습니다.
// 프론트에 사전을 중복으로 두지 않도록, 앱 시작 시 수어 영상 목록을 한 번 받아
// keyword → SignVideo 조회용 Map을 만들어 씁니다 (서버가 단일 출처).
export function useSignVideoDictionary(enabled: boolean) {
  const [dictionary, setDictionary] = useState<Map<string, SignVideo>>(new Map());

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let cancelled = false;

    searchSignVideos("")
      .then((items) => {
        if (cancelled) {
          return;
        }

        setDictionary(
          new Map(items.map((item) => [item.sign_video.keyword, item.sign_video]))
        );
      })
      .catch(() => {
        // 사전을 못 받아도 기본 카드(🖐️)로 표시되므로 화면은 계속 동작합니다.
      });

    return () => {
      cancelled = true;
    };
  }, [enabled]);

  // 사전에 없는 키워드도 자리를 차지해야 하므로 기본값으로 물러섭니다.
  const lookup = useCallback(
    (keyword: string): SignVideo =>
      dictionary.get(keyword) ?? {
        id: -1,
        keyword,
        title: keyword,
        emoji: "🖐️",
        video_url: null,
      },
    [dictionary]
  );

  return { lookup, ready: dictionary.size > 0 };
}
