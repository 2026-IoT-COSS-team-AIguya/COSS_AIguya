"use client";

import { useState } from "react";

import { ActionButton, KeywordTag, Panel } from "@/components/ui";
import { useLatestTranslation } from "@/hooks/useLatestTranslation";
import { previewSignVideoSequence } from "@/lib/api/endpoints";
import { toUserMessage } from "@/lib/api/errors";
import { translationStatusLabel } from "@/lib/types";
import type {
  QuickKeyword,
  SignVideo,
  SignVideoSequenceItem,
  User,
} from "@/lib/types";

export function TranslatorView({
  currentUser,
  quickKeywords,
  lookup,
  onOpenSequence,
}: {
  currentUser: User;
  quickKeywords: QuickKeyword[];
  lookup: (keyword: string) => SignVideo;
  onOpenSequence: (
    title: string,
    sequence: SignVideoSequenceItem[],
    description?: string
  ) => void;
}) {
  const isSignUser = currentUser.role === "SIGN_USER";

  // 촬영은 아두이노 물리 버튼이 시작합니다. 화면은 결과를 지켜보기만 합니다.
  const { translation, isSlow } = useLatestTranslation(true);

  const [keywordInput, setKeywordInput] = useState("은행, 번호, 받다");
  const [sequence, setSequence] = useState<SignVideoSequenceItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    const keywords = keywordInput
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    if (keywords.length === 0) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 명세 7.2: 백엔드가 요청받은 키워드 순서를 유지해 돌려줍니다.
      setSequence(await previewSignVideoSequence(keywords));
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setLoading(false);
    }
  };

  const appendKeyword = (keyword: string) => {
    const current = keywordInput
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    if (!current.includes(keyword)) {
      setKeywordInput([...current, keyword].join(", "));
    }
  };

  const analyzing =
    translation?.status === "PENDING" || translation?.status === "PROCESSING";

  return (
    <div className="grid h-full grid-cols-1 gap-5 overflow-y-auto xl:grid-cols-[1fr_1fr]">
      {/* 왼쪽: 농인 — 아두이노 버튼으로 촬영, 결과가 여기 뜹니다. */}
      <Panel
        className={`animate-fade-up overflow-y-auto p-6 ${
          isSignUser ? "ring-4 ring-sky-100" : ""
        }`}
      >
        <div className="mb-5">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-600">
            🤟 농인 중심
          </p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">
            수어 영상 → 텍스트
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            버튼을 누르면 💡 LED가 켜지고 📷 카메라가 촬영을 시작합니다.
          </p>
        </div>

        {/* 대기 상태 — 아직 아무것도 안 찍음 */}
        {!translation && (
          <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <p className="text-5xl">🔘</p>
            <p className="mt-4 text-base font-black text-slate-700">
              버튼을 눌러 촬영을 시작하세요
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              촬영이 끝나면 이 자리에 인식 결과가 나타납니다.
            </p>
          </div>
        )}

        {/* 분석 중 — 명세 6장의 상태 문구를 그대로 씁니다. */}
        {translation && analyzing && (
          <div className="rounded-[28px] border border-sky-200 bg-sky-50 p-8 text-center">
            <p className="text-5xl animate-soft-pulse">
              {translation.status === "PENDING" ? "💡" : "🧠"}
            </p>
            <p className="mt-4 text-xl font-black text-slate-900">
              {translationStatusLabel[translation.status]}
            </p>

            {/* 명세 5.2: 60초가 지나면 처리 지연 안내 */}
            {isSlow && (
              <p className="mt-4 rounded-2xl bg-amber-100 px-4 py-3 text-sm font-bold text-amber-800">
                분석이 예상보다 오래 걸리고 있어요. 조금만 더 기다려주세요.
              </p>
            )}
          </div>
        )}

        {/* 완료 */}
        {translation?.status === "COMPLETED" && (
          <div className="animate-soft-scale rounded-[28px] border border-sky-100 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-4">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-sky-600">
                🤟 인식 결과
              </p>
              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-600">
                ✅ {translationStatusLabel.COMPLETED}
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {[...translation.recognized_keywords]
                .sort((a, b) => a.position - b.position)
                .map((item) => (
                  <KeywordTag
                    key={`${item.keyword}-${item.position}`}
                    keyword={item.keyword}
                    emoji={lookup(item.keyword).emoji}
                    title={`${lookup(item.keyword).title} ${Math.round(
                      item.confidence * 100
                    )}%`}
                    big
                  />
                ))}
            </div>

            <div className="mt-5 rounded-[24px] bg-sky-50 p-5">
              <p className="text-xs font-bold text-sky-700">문장 후보</p>
              <p className="mt-2 text-3xl font-black leading-snug text-slate-900">
                {translation.sentence_candidates[0] ?? "—"}
              </p>
            </div>

            {translation.recognized_keywords.length > 0 && (
              <p className="mt-4 text-xs font-bold text-emerald-600">
                📊 평균 신뢰도{" "}
                {Math.round(
                  (translation.recognized_keywords.reduce(
                    (sum, item) => sum + item.confidence,
                    0
                  ) /
                    translation.recognized_keywords.length) *
                    100
                )}
                %
              </p>
            )}
          </div>
        )}

        {/* 실패 — 명세 9장: 인식 실패는 200 OK + status FAILED로 옵니다. */}
        {translation?.status === "FAILED" && (
          <div className="rounded-[28px] border border-rose-100 bg-white p-6 text-center shadow-sm">
            <p className="text-5xl">🙁</p>
            <p className="mt-4 text-lg font-black text-slate-900">
              {translationStatusLabel.FAILED}
            </p>
            <p className="mt-2 text-sm text-slate-500">
              {translation.error?.message ?? "다시 촬영해주세요."}
            </p>
            <p className="mt-4 text-sm font-bold text-slate-400">
              🔘 버튼을 다시 눌러 촬영하세요
            </p>
          </div>
        )}

        <div className="mt-5 rounded-[24px] bg-amber-50 p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-amber-700">
            개발 현황
          </p>
          <p className="mt-2 text-xs leading-5 text-amber-800">
            수어 인식 모델(키포인트 기반)은 학습 중이라, 현재 인식 결과는 고정된
            예시가 순서대로 나옵니다. 업로드 · 상태 전이 · 폴링은 실제로 동작합니다.
          </p>
        </div>
      </Panel>

      {/* 오른쪽: 청인 — 텍스트를 수어 영상으로 */}
      <Panel
        className={`animate-fade-up overflow-y-auto p-6 ${
          !isSignUser ? "ring-4 ring-sky-100" : ""
        }`}
      >
        <div className="mb-5">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-500">
            ⌨️ 비장애인 / 직원 중심
          </p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">
            텍스트 → 수어 영상
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            키워드를 입력하면 대응되는 수어 영상을 순서대로 보여줍니다.
          </p>
        </div>

        <div className="space-y-5">
          <div>
            <span className="mb-2 block text-sm font-bold text-slate-700">
              빠른 키워드
            </span>
            <div className="flex flex-wrap gap-2">
              {quickKeywords.map((item) => (
                <button
                  key={item.id}
                  onClick={() => appendKeyword(item.keyword)}
                  className="flex items-center gap-1.5 rounded-full border border-sky-100 bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-700 transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-100 hover:shadow-md active:translate-y-0"
                >
                  <span className="text-base leading-none">{item.emoji}</span>
                  {item.keyword}
                </button>
              ))}
            </div>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-700">
              키워드 입력 (쉼표로 구분)
            </span>
            <input
              value={keywordInput}
              onChange={(event) => setKeywordInput(event.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
              placeholder="예: 은행, 번호, 받다"
            />
          </label>

          <ActionButton onClick={handleGenerate} disabled={loading}>
            {loading ? "⏳ 생성 중…" : "🔄 키워드 시퀀스 생성"}
          </ActionButton>

          {error && (
            <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-600">
              {error}
            </p>
          )}

          {sequence.length > 0 && (
            <div className="rounded-[26px] border border-slate-200 bg-slate-50 p-4">
              <div className="mb-4 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-bold text-slate-900">미리보기</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {sequence.map((item) => (
                      <KeywordTag
                        key={item.position}
                        keyword={item.sign_video.keyword}
                        emoji={item.sign_video.emoji}
                        title={item.sign_video.title}
                      />
                    ))}
                  </div>
                </div>

                <button
                  onClick={() =>
                    onOpenSequence(
                      "미리보기 전체 재생",
                      sequence,
                      "position 순서대로 자동 재생됩니다."
                    )
                  }
                  className="shrink-0 rounded-2xl bg-sky-500 px-4 py-2 text-sm font-bold text-white shadow-[0_12px_30px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 active:translate-y-0"
                >
                  ▶ 전체 재생
                </button>
              </div>

              <div className="space-y-3">
                {sequence.map((item) => (
                  <div
                    key={item.position}
                    className="flex items-center gap-4 rounded-[24px] border border-slate-200 bg-white px-4 py-3"
                  >
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#0F172A_0%,#1D4ED8_100%)] text-2xl">
                      {item.sign_video.emoji}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-slate-900 px-2 text-[11px] font-black text-white">
                          {item.position}
                        </span>
                        <p className="truncate text-base font-black text-slate-900">
                          {item.sign_video.title}
                        </p>
                      </div>
                      <p className="truncate text-xs text-slate-400">
                        {item.sign_video.video_url ?? "영상 연결 전 (AI DB 예정)"}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
