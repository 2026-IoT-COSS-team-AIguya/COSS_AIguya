"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { SignVideoSequenceItem } from "@/lib/types";

export type SequenceModalState = {
  open: boolean;
  title: string;
  description?: string;
  sequence: SignVideoSequenceItem[];
};

export function SequenceModal({
  modal,
  onClose,
}: {
  modal: SequenceModalState;
  onClose: () => void;
}) {
  // 명세 7.2: 영상 재생 순서는 position으로 전달되며, 오름차순으로 재생합니다.
  const ordered = useMemo(
    () => [...modal.sequence].sort((a, b) => a.position - b.position),
    [modal.sequence]
  );

  const [activeIndex, setActiveIndex] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // 다른 시퀀스를 열면 첫 항목부터 다시 재생합니다.
  const [trackedSequence, setTrackedSequence] = useState(modal.sequence);

  if (trackedSequence !== modal.sequence) {
    setTrackedSequence(modal.sequence);
    setActiveIndex(0);
  }

  const active = ordered[activeIndex];

  // 현재 항목이 바뀌면 자동으로 재생합니다. 영상이 없는 항목(이모지 카드)은
  // 잠깐 보여준 뒤 다음으로 넘어갑니다.
  useEffect(() => {
    if (!active) {
      return;
    }

    if (active.sign_video.video_url) {
      videoRef.current?.play().catch(() => {
        // 자동재생이 막히면 사용자가 controls로 직접 재생하면 됩니다.
      });
      return;
    }

    const timer = setTimeout(() => {
      setActiveIndex((index) => (index + 1 < ordered.length ? index + 1 : index));
    }, 1400);

    return () => clearTimeout(timer);
  }, [active, ordered.length]);

  // 명세 7.2: 프론트는 영상의 ended 이벤트가 발생하면 다음 영상을 재생합니다.
  const handleEnded = () => {
    setActiveIndex((index) => (index + 1 < ordered.length ? index + 1 : index));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 px-4 py-8 backdrop-blur-md">
      <div className="animate-soft-scale flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-[32px] border border-white/10 bg-white shadow-[0_40px_120px_rgba(15,23,42,0.38)]">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-600">
              ▶ 전체 재생 모드
            </p>
            <h3 className="mt-1 text-2xl font-black text-slate-900">{modal.title}</h3>
            {modal.description && (
              <p className="mt-2 text-sm leading-6 text-slate-500">
                {modal.description}
              </p>
            )}
          </div>

          <button
            onClick={onClose}
            className="shrink-0 rounded-2xl bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-200 active:translate-y-0"
          >
            닫기
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-6">
          {!active ? (
            <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-slate-500">
              표시할 수어 영상이 없습니다.
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-center gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#0F172A_0%,#1D4ED8_100%)] text-2xl shadow-[0_12px_30px_rgba(29,78,216,0.28)]">
                  {active.sign_video.emoji}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-slate-900 px-2 text-xs font-black text-white">
                      {activeIndex + 1} / {ordered.length}
                    </span>
                    <h4 className="text-lg font-black text-slate-900">
                      {active.sign_video.title}
                    </h4>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    키워드: {active.sign_video.keyword}
                  </p>
                </div>
              </div>

              {active.sign_video.video_url ? (
                <video
                  ref={videoRef}
                  key={active.sign_video.video_url}
                  src={active.sign_video.video_url}
                  controls
                  autoPlay
                  onEnded={handleEnded}
                  className="w-full rounded-2xl bg-slate-950 shadow-inner"
                />
              ) : (
                <div className="flex h-64 items-center justify-center rounded-2xl bg-slate-950 text-white">
                  <div className="text-center">
                    <p className="text-7xl">{active.sign_video.emoji}</p>
                    <p className="mt-4 text-sm text-slate-300">
                      아직 연결된 영상이 없어요. AI 개발 완료 후 연결될 예정입니다.
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-5 flex flex-wrap gap-2">
                {ordered.map((item, index) => (
                  <button
                    key={`${item.sign_video.keyword}-${item.position}`}
                    onClick={() => setActiveIndex(index)}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-2 text-xs font-bold transition-all duration-200 ${
                      index === activeIndex
                        ? "border-sky-300 bg-sky-50 text-sky-700"
                        : "border-slate-200 bg-slate-50 text-slate-500 hover:bg-white"
                    }`}
                  >
                    <span className="text-base leading-none">
                      {item.sign_video.emoji}
                    </span>
                    {item.sign_video.title}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="border-t border-slate-200 bg-slate-50 px-6 py-4 text-sm text-slate-500">
          영상이 끝나면 다음 순서로 자동 재생됩니다.
        </div>
      </div>
    </div>
  );
}
