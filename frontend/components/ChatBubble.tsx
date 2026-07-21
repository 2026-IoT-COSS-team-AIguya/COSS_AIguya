"use client";

import type { Message, SignVideo, User } from "@/lib/types";
import { translationStatusLabel, withDisplayName } from "@/lib/types";
import type { SequenceRequest } from "@/components/SequenceModal";
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
  matchInText,
  onOpenSequence,
}: {
  message: Message;
  index: number;
  currentUser: User;
  lookup: (keyword: string) => SignVideo;
  matchInText: (text: string) => SignVideo[];
  onOpenSequence: (request: SequenceRequest) => void;
}) {
  const isMine = message.sender.id === currentUser.id;
  const isSignUser = currentUser.role === "SIGN_USER";
  const displayName = isMine
    ? `${withDisplayName(currentUser.nickname, currentUser.display_name)} · 나`
    : withDisplayName(message.sender.nickname, message.sender.display_name);

  // 농인 화면에서 상대가 보낸 맨 텍스트는 가장 읽기 어려운 형태입니다.
  // 문장 안의 사전 단어를 이모지로 뽑아 붙여줍니다.
  const textEmojis =
    isSignUser && !isMine && message.type === "TEXT"
      ? matchInText(message.text ?? "")
      : [];

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
                  <span key={item.position} title={item.sign_video.title}>
                    {item.sign_video.emoji}
                  </span>
                ))}
              </h4>

              {/* 보낸 사람이 실제로 친 문장. 키워드로 쪼개면 조사·어순이 날아가서
                  옆에서 같이 보는 청인이 자기가 보낸 말을 못 알아봅니다. */}
              {message.text && (
                <p className="mt-3 border-t border-white/15 pt-3 text-lg font-black leading-relaxed text-white">
                  “{message.text}”
                </p>
              )}
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
                onOpenSequence({
                  title: "수어 영상 시퀀스",
                  sequence: message.sign_video_sequence,
                  description: "순서대로 자동 재생됩니다.",
                  sourceText: message.text ?? undefined,
                })
              }
              className="mt-4 w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-bold text-white shadow-[0_12px_30px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 active:translate-y-0"
            >
              ▶ 전체 재생
            </button>
          </div>
        )}

        {message.type === "TEXT" && (
          <div className="rounded-[30px] border border-slate-200 bg-white p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(15,23,42,0.12)]">
            {/* 농인 화면: 문장에서 찾은 단어를 큰 이모지로 먼저 보여줍니다. */}
            {textEmojis.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-2 rounded-[24px] bg-[radial-gradient(circle_at_20%_0%,rgba(56,189,248,0.22),transparent_32%),linear-gradient(135deg,#071430,#0B1F4E)] p-4 text-4xl">
                {textEmojis.map((video) => (
                  <span key={video.keyword} title={video.title}>
                    {video.emoji}
                  </span>
                ))}
              </div>
            )}

            <p className="text-2xl font-black leading-relaxed text-slate-900">
              {message.text}
            </p>

            {textEmojis.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {textEmojis.map((video) => (
                  <KeywordTag
                    key={video.keyword}
                    keyword={video.keyword}
                    emoji={video.emoji}
                    title={video.title}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
