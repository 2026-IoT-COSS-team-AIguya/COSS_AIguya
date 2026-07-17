"use client";

import { useState } from "react";

import { CaptureButton } from "@/components/CaptureButton";
import { ActionButton, KeywordTag, Panel } from "@/components/ui";
import { useLatestTranslation } from "@/hooks/useLatestTranslation";
import { sentenceToSignSequence } from "@/lib/api/endpoints";
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

  // 촬영은 화면의 버튼과 아두이노 물리 버튼 둘 다에서 시작됩니다. 어느 쪽이든
  // 업로드 응답으로 id를 받을 수 없는 경우가 있어(기기는 화면과 별개로 움직입니다),
  // 화면은 "가장 최근 촬영"을 폴링해서 보여줍니다.
  const { translation, isSlow } = useLatestTranslation(true);

  const [sentence, setSentence] = useState("은행에서 번호표 받으세요");
  const [sequence, setSequence] = useState<SignVideoSequenceItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // 사전에 겹치는 단어가 하나도 없을 때. 오류가 아니라 빈 결과입니다.
  const [noMatch, setNoMatch] = useState(false);

  const handleGenerate = async () => {
    const text = sentence.trim();

    if (!text) {
      return;
    }

    setLoading(true);
    setError(null);
    setNoMatch(false);

    try {
      // 조사·어순은 AI가 걷어내고, 사전 안의 키워드만 순서대로 돌려줍니다.
      const result = await sentenceToSignSequence(text);
      setSequence(result.sequence);
      setNoMatch(result.keywords.length === 0);
    } catch (cause) {
      setError(toUserMessage(cause));
      setSequence([]);
    } finally {
      setLoading(false);
    }
  };

  // 빠른 키워드는 문장을 처음부터 쓰기 번거로울 때 쓰는 보조입니다.
  const appendKeyword = (keyword: string) => {
    setSentence((current) => (current.trim() ? `${current.trim()} ${keyword}` : keyword));
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
            화면의 촬영 버튼을 누르거나, 🔘 아두이노 버튼을 눌러도 됩니다.
          </p>
        </div>

        {/* 하드웨어가 없는 자리에서도 시연할 수 있어야 합니다. 같은 API를 쓰는
            대체 경로라, 기기가 붙으면 둘 다 동작합니다. */}
        <div className="mb-5 flex items-center gap-3">
          <CaptureButton conversationId={null} label="🎥 수어 촬영" />
          <p className="text-xs leading-5 text-slate-400">
            대화방 없이 이 자리에서 바로 번역합니다.
          </p>
        </div>

        {/* 대기 상태 — 아직 아무것도 안 찍음 */}
        {!translation && (
          <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
            <p className="text-5xl">🔘</p>
            <p className="mt-4 text-base font-black text-slate-700">
              촬영을 시작하세요
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
            하고 싶은 말을 문장으로 쓰면 🧠 AI가 수어 단어로 바꿔줍니다.
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
              문장 입력
            </span>
            <textarea
              value={sentence}
              onChange={(event) => setSentence(event.target.value)}
              onKeyDown={(event) => {
                // 줄바꿈은 Shift+Enter. 그냥 Enter는 바로 생성입니다.
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  handleGenerate();
                }
              }}
              rows={2}
              className="w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
              placeholder="예: 은행에서 번호표 받으세요"
            />
            <span className="mt-2 block text-xs text-slate-400">
              쉼표로 끊지 않아도 됩니다. 조사·어순은 AI가 알아서 정리합니다.
            </span>
          </label>

          <ActionButton onClick={handleGenerate} disabled={loading || !sentence.trim()}>
            {loading ? "🧠 AI가 분석 중…" : "🔄 수어로 바꾸기"}
          </ActionButton>

          {error && (
            <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-600">
              {error}
            </p>
          )}

          {/* 문장 분석은 됐는데 사전에 겹치는 단어가 없는 경우 */}
          {noMatch && (
            <div className="rounded-[24px] border border-dashed border-amber-300 bg-amber-50 p-5 text-center">
              <p className="text-3xl">🤔</p>
              <p className="mt-3 text-sm font-black text-amber-900">
                이 문장에서 수어로 바꿀 수 있는 단어를 못 찾았어요
              </p>
              <p className="mt-2 text-xs leading-5 text-amber-700">
                수어 사전에 있는 단어로 다시 말해보세요. 위의 빠른 키워드를
                참고하시면 좋습니다.
              </p>
            </div>
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
