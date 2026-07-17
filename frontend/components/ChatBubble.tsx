"use client";

import type { Message, SignVideo, SignVideoSequenceItem, User } from "@/lib/types";
import { translationStatusLabel } from "@/lib/types";
import { Avatar, KeywordTag } from "@/components/ui";

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ChatBubble({
  message,
  index,
  currentUser,
  lookup,
  onOpenSequence,
}: {
  message: Message;
  index: number;
  currentUser: User;
  lookup: (keyword: string) => SignVideo;
  onOpenSequence: (
    title: string,
    sequence: SignVideoSequenceItem[],
    description?: string
  ) => void;
}) {
  const isMine = message.sender.id === currentUser.id;
  const displayName = isMine
    ? `${currentUser.nickname} · 나`
    : message.sender.nickname;

  return (
    <div
      className={`flex ${
        isMine ? "justify-end animate-slide-right" : "justify-start animate-slide-left"
      }`}
      style={{ animationDelay: `${Math.min(index, 6) * 90}ms` }}
    >
      <div className={`w-full max-w-[620px] ${isMine ? "ml-10" : "mr-10"}`}>
        <div
          className={`mb-2 flex items-center gap-2 px-2 ${
            isMine ? "justify-end" : "justify-start"
          }`}
        >
          {!isMine && <Avatar label={displayName} />}
          <span className="text-sm font-bold text-slate-500">{displayName}</span>
          <span className="text-xs font-semibold text-slate-400">
            {formatTime(message.created_at)}
          </span>
          {isMine && <Avatar label={currentUser.nickname} mine />}
        </div>

        {message.type === "SIGN_TRANSLATION" && message.sign_translation && (
          <div className="rounded-[30px] border border-sky-100 bg-white p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(15,23,42,0.12)]">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-sky-600">
                  🤟 수어 영상 → 텍스트
                </p>
                <h4 className="mt-2 text-base font-black text-slate-900">
                  AI 인식 결과
                </h4>
              </div>

              <span
                className={`rounded-full px-3 py-1.5 text-xs font-bold ${
                  message.sign_translation.status === "COMPLETED"
                    ? "bg-emerald-50 text-emerald-600"
                    : message.sign_translation.status === "FAILED"
                      ? "bg-rose-50 text-rose-600"
                      : "bg-sky-50 text-sky-600"
                }`}
              >
                {translationStatusLabel[message.sign_translation.status]}
              </span>
            </div>

            {message.sign_translation.recognized_keywords.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {[...message.sign_translation.recognized_keywords]
                  .sort((a, b) => a.position - b.position)
                  .map((item) => (
                    <KeywordTag
                      key={`${item.keyword}-${item.position}`}
                      keyword={item.keyword}
                      emoji={lookup(item.keyword).emoji}
                      title={lookup(item.keyword).title}
                      big
                    />
                  ))}
              </div>
            )}

            {message.sign_translation.sentence_candidates.length > 0 && (
              <div className="mt-4 rounded-[24px] bg-sky-50 p-4">
                <p className="text-xs font-bold text-sky-700">문장 후보</p>
                <p className="mt-2 text-xl font-black text-slate-900">
                  {message.sign_translation.sentence_candidates[0]}
                </p>
              </div>
            )}

            {message.sign_translation.recognized_keywords.length > 0 && (
              <p className="mt-3 text-xs font-bold text-emerald-600">
                📊 평균 신뢰도{" "}
                {Math.round(
                  (message.sign_translation.recognized_keywords.reduce(
                    (sum, item) => sum + item.confidence,
                    0
                  ) /
                    message.sign_translation.recognized_keywords.length) *
                    100
                )}
                %
              </p>
            )}

            {message.sign_translation.status === "FAILED" && (
              <p className="mt-3 text-sm font-bold text-rose-600">
                {message.sign_translation.error?.message ??
                  "수어를 인식하지 못했어요."}
              </p>
            )}
          </div>
        )}

        {message.type === "SIGN_VIDEO_SEQUENCE" && (
          <div className="rounded-[30px] border border-sky-100 bg-white p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(15,23,42,0.12)]">
            <div className="rounded-[24px] bg-[radial-gradient(circle_at_20%_0%,rgba(56,189,248,0.22),transparent_32%),linear-gradient(135deg,#071430,#0B1F4E)] p-5 text-white">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-sky-200">
                ⌨️ 텍스트 → 수어 영상
              </p>
              <h4 className="mt-2 flex flex-wrap gap-2 text-3xl">
                {message.sign_video_sequence.map((item) => (
                  <span key={item.position}>{item.sign_video.emoji}</span>
                ))}
              </h4>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {message.sign_video_sequence.map((item) => (
                <KeywordTag
                  key={item.position}
                  keyword={item.sign_video.keyword}
                  emoji={item.sign_video.emoji}
                  title={item.sign_video.title}
                  big
                />
              ))}
            </div>

            <button
              onClick={() =>
                onOpenSequence(
                  "수어 영상 시퀀스",
                  message.sign_video_sequence,
                  "순서대로 자동 재생됩니다."
                )
              }
              className="mt-4 w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-bold text-white shadow-[0_12px_30px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 active:translate-y-0"
            >
              ▶ 전체 재생
            </button>
          </div>
        )}

        {message.type === "TEXT" && (
          <div className="rounded-[30px] border border-slate-200 bg-white p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(15,23,42,0.12)]">
            <p className="text-2xl font-black leading-relaxed text-slate-900">
              {message.text}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
