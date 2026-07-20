"use client";

import { useEffect, useRef, useState } from "react";

import { CaptureButton } from "@/components/CaptureButton";
import { ChatBubble } from "@/components/ChatBubble";
import { ActionButton, Panel } from "@/components/ui";
import { useMessagePolling } from "@/hooks/useMessagePolling";
import {
  createSignVideoSequenceMessage,
  createTextMessage,
  sentenceToSignSequence,
} from "@/lib/api/endpoints";
import { toUserMessage } from "@/lib/api/errors";
import { withDisplayName } from "@/lib/types";
import type {
  Conversation,
  QuickKeyword,
  SignVideo,
  SignVideoSequenceItem,
  User,
} from "@/lib/types";

export function ChatView({
  conversations,
  selectedId,
  onSelectConversation,
  currentUser,
  quickKeywords,
  lookup,
  matchInText,
  onOpenSequence,
  onAuthExpired,
}: {
  conversations: Conversation[];
  selectedId: number | null;
  onSelectConversation: (id: number) => void;
  currentUser: User;
  quickKeywords: QuickKeyword[];
  lookup: (keyword: string) => SignVideo;
  matchInText: (text: string) => SignVideo[];
  onOpenSequence: (
    title: string,
    sequence: SignVideoSequenceItem[],
    description?: string
  ) => void;
  onAuthExpired: () => void;
}) {
  const isSignUser = currentUser.role === "SIGN_USER";
  const selected = conversations.find((item) => item.id === selectedId) ?? null;

  const { messages, loading, appendLocal } = useMessagePolling(
    selectedId,
    onAuthExpired
  );

  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pickedKeywords, setPickedKeywords] = useState<string[]>([]);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  // 새 메시지가 오면 아래로 따라갑니다.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleSendText = async () => {
    if (selectedId === null || !draft.trim() || sending) {
      return;
    }

    setSending(true);
    setError(null);

    try {
      const message = await createTextMessage(selectedId, draft.trim());
      appendLocal(message);
      setDraft("");
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setSending(false);
    }
  };

  const handleSendSequence = async () => {
    if (selectedId === null || pickedKeywords.length === 0 || sending) {
      return;
    }

    setSending(true);
    setError(null);

    try {
      const message = await createSignVideoSequenceMessage(
        selectedId,
        pickedKeywords
      );
      appendLocal(message);
      setPickedKeywords([]);
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setSending(false);
    }
  };

  // 입력창의 문장을 AI가 수어 키워드로 바꿔서 영상 시퀀스로 보냅니다.
  // 키워드를 직접 고르는 아래 버튼과 달리, 그냥 평소처럼 말하면 됩니다.
  const handleSendSentenceAsSign = async () => {
    if (selectedId === null || !draft.trim() || sending) {
      return;
    }

    setSending(true);
    setError(null);

    try {
      const { keywords } = await sentenceToSignSequence(draft.trim());

      if (keywords.length === 0) {
        setError(
          "이 문장에서 수어로 바꿀 수 있는 단어를 못 찾았어요. 다르게 말해보시거나 아래 키워드를 골라주세요."
        );
        return;
      }

      const message = await createSignVideoSequenceMessage(selectedId, keywords);
      appendLocal(message);
      setDraft("");
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setSending(false);
    }
  };

  const togglePick = (keyword: string) => {
    setPickedKeywords((current) =>
      current.includes(keyword)
        ? current.filter((item) => item !== keyword)
        : [...current, keyword]
    );
  };

  return (
    <div className="grid h-full grid-cols-1 gap-5 xl:grid-cols-[310px_minmax(0,1fr)]">
      <Panel className="animate-fade-up flex min-h-0 flex-col p-5">
        <div className="mb-4">
          <h3 className="text-xl font-black tracking-tight text-slate-900">
            대화 목록
          </h3>
          <p className="mt-1 text-xs font-medium text-slate-400">
            최근 메시지가 온 대화가 위로 올라옵니다.
          </p>
        </div>

        <div className="space-y-3 overflow-y-auto pr-1">
          {conversations.length === 0 && (
            <div className="rounded-[24px] border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
              <p className="text-3xl">👋</p>
              <p className="mt-3 text-sm font-black text-slate-700">
                아직 대화가 없어요
              </p>
              <p className="mt-2 text-xs leading-5 text-slate-400">
                👥 친구 화면에서 이모지 아이디로 친구를 추가한 뒤 대화를 시작하세요.
              </p>
            </div>
          )}

          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => onSelectConversation(conversation.id)}
              className={`group w-full rounded-[24px] border p-3 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl ${
                conversation.id === selectedId
                  ? "border-sky-300 bg-sky-50 shadow-[0_12px_30px_rgba(56,189,248,0.16)]"
                  : "border-slate-200 bg-slate-50 hover:border-sky-200 hover:bg-white"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#22C1FF_0%,#1D4ED8_100%)] text-2xl shadow-[0_14px_30px_rgba(29,78,216,0.24)] transition-transform duration-300 group-hover:scale-105">
                  {conversation.icon}
                </div>

                <div className="min-w-0 flex-1">
                  <h4 className="truncate text-base font-black text-slate-900">
                    {conversation.title}
                  </h4>

                  <p className="mt-0.5 truncate text-xs font-bold text-slate-500">
                    {conversation.participants
                      .filter((participant) => participant.id !== currentUser.id)
                      .map((participant) =>
                        withDisplayName(
                          participant.nickname,
                          participant.display_name
                        )
                      )
                      .join(", ")}
                  </p>

                  <p className="mt-1 truncate text-xs font-medium text-slate-400">
                    {conversation.last_message_preview ?? "아직 대화가 없어요"}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </Panel>

      <Panel className="animate-fade-up flex min-h-0 flex-col overflow-hidden">
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white/90 px-6 py-4 backdrop-blur">
          <div>
            <h3 className="flex items-center gap-2 text-xl font-black text-slate-900">
              <span className="text-2xl">{selected?.icon ?? "💬"}</span>
              {selected?.title ?? "대화를 선택하세요"}
            </h3>
            <p className="mt-1 text-xs font-medium text-slate-400">
              {selected?.category ?? "—"}
            </p>
          </div>

          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-bold text-slate-500">
            {isSignUser ? "🤟 농인 화면" : "⌨️ 비장애인 화면"}
          </span>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto bg-[radial-gradient(circle_at_20%_10%,rgba(56,189,248,0.12),transparent_26%),linear-gradient(180deg,#F8FBFF_0%,#EEF6FF_100%)] px-6 py-5">
          <div className="mx-auto max-w-5xl space-y-5">
            {loading && messages.length === 0 && (
              <p className="py-10 text-center text-sm font-bold text-slate-400">
                대화를 불러오는 중…
              </p>
            )}

            {!loading && messages.length === 0 && (
              <div className="rounded-[28px] border border-dashed border-slate-300 bg-white/60 p-10 text-center">
                <p className="text-4xl">{isSignUser ? "🤟" : "⌨️"}</p>
                <p className="mt-4 text-base font-black text-slate-700">
                  아직 대화가 없어요
                </p>
                <p className="mt-2 text-sm text-slate-400">
                  아래 입력창에 메시지를 적어 보내보세요.
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <ChatBubble
                key={message.id}
                message={message}
                index={index}
                currentUser={currentUser}
                lookup={lookup}
                matchInText={matchInText}
                onOpenSequence={onOpenSequence}
              />
            ))}

            <div ref={bottomRef} />
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-200 bg-white/95 px-6 py-4 backdrop-blur">
          {error && (
            <p className="mb-3 rounded-2xl bg-rose-50 px-4 py-2.5 text-sm font-bold text-rose-600">
              {error}
            </p>
          )}

          {isSignUser ? (
            <div className="space-y-3">
              {/* 수어가 주 입력입니다. 촬영을 맨 앞에 크게 둡니다 —
                  필담만 있으면 농인에게 "글로 쓰세요"라고 하는 화면이 됩니다. */}
              <div className="flex items-center gap-3">
                <CaptureButton
                  conversationId={selectedId}
                  label="🎥 수어로 말하기"
                />
                <p className="text-xs leading-5 text-slate-400">
                  찍으면 AI가 분석해서 이 대화에 올려줍니다.
                  <br />
                  🔘 아두이노 버튼을 눌러도 됩니다.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <div className="h-px flex-1 bg-slate-200" />
                <span className="text-xs font-bold text-slate-400">
                  또는 ✍️ 필담으로
                </span>
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              <div className="flex gap-2">
                <input
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      handleSendText();
                    }
                  }}
                  placeholder="✍️ 글이나 이모지로 적기"
                  className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900 outline-none focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                />
                <ActionButton
                  onClick={handleSendText}
                  disabled={!draft.trim() || sending}
                >
                  전송
                </ActionButton>
              </div>

              {/* 농인 화면은 이모지를 크게 깔아둡니다 — 글자보다 빠르게 고를 수 있습니다. */}
              <div className="flex flex-wrap items-center gap-2">
                {quickKeywords.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setDraft((current) => current + item.emoji)}
                    title={item.keyword}
                    className="flex h-11 w-11 items-center justify-center rounded-2xl border border-sky-100 bg-sky-50 text-2xl transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-100 hover:shadow-md active:translate-y-0"
                  >
                    {item.emoji}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      handleSendText();
                    }
                  }}
                  placeholder="⌨️ 메시지를 입력하세요"
                  className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900 outline-none focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                />
                <ActionButton
                  onClick={handleSendText}
                  disabled={!draft.trim() || sending}
                >
                  전송
                </ActionButton>
                <ActionButton
                  dark
                  onClick={handleSendSentenceAsSign}
                  disabled={!draft.trim() || sending}
                >
                  {sending ? "🧠 분석 중…" : "🤟 수어로 보내기"}
                </ActionButton>
              </div>

              {/* 위 문장 입력이 기본이고, 아래는 AI 없이 키워드를 직접 고르는 길입니다. */}
              <div className="flex flex-wrap items-center gap-2">
                {quickKeywords.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => togglePick(item.keyword)}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold transition-all duration-200 hover:-translate-y-0.5 ${
                      pickedKeywords.includes(item.keyword)
                        ? "border-sky-400 bg-sky-100 text-sky-800"
                        : "border-sky-100 bg-sky-50 text-sky-700 hover:bg-sky-100"
                    }`}
                  >
                    <span className="text-base leading-none">{item.emoji}</span>
                    {item.keyword}
                  </button>
                ))}

                {pickedKeywords.length > 0 && (
                  <ActionButton
                    light
                    onClick={handleSendSequence}
                    disabled={sending}
                  >
                    고른 {pickedKeywords.length}개 보내기
                  </ActionButton>
                )}
              </div>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
