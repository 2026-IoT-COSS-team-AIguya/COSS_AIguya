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

  // 문장 안에 들어 있는 사전 단어를 등장 순서대로 찾습니다.
  // 농인 화면에서 상대가 보낸 맨 텍스트에 이모지를 붙여주는 데 씁니다 —
  // 한국어 문장만 덩그러니 있는 것보다 그림이 붙으면 훨씬 빨리 읽힙니다.
  const matchInText = useCallback(
    (text: string): SignVideo[] => {
      if (!text) {
        return [];
      }

      const found: { at: number; video: SignVideo }[] = [];

      for (const [keyword, video] of dictionary) {
        const at = text.indexOf(keyword);

        if (at !== -1) {
          found.push({ at, video });
        }
      }

      return found.sort((a, b) => a.at - b.at).map((item) => item.video);
    },
    [dictionary]
  );

  return { lookup, matchInText, ready: dictionary.size > 0 };
}
