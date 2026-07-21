"use client";

import { useState } from "react";

import {
  EmojiIdDisplay,
  EmojiPalette,
  MAX_ID_EMOJIS,
  countGraphemes,
  removeLastGrapheme,
} from "@/components/EmojiKeypad";
import { ActionButton, Avatar, Panel } from "@/components/ui";
import { useFriends } from "@/hooks/useFriends";
import {
  acceptFriendRequest,
  createConversation,
  rejectFriendRequest,
  sendFriendRequest,
} from "@/lib/api/endpoints";
import { toUserMessage } from "@/lib/api/errors";
import { roleLabel, withDisplayName } from "@/lib/types";
import type { User } from "@/lib/types";

export function FriendsView({
  currentUser,
  onConversationCreated,
}: {
  currentUser: User;
  onConversationCreated: (conversationId: number) => void;
}) {
  const { friends, incoming_requests, outgoing_requests, loading, refresh } =
    useFriends(true);

  const [nickname, setNickname] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // 어떤 버튼이 도는 중인지. 여러 개를 동시에 누르는 걸 막습니다.
  const [busy, setBusy] = useState<string | null>(null);

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    setNotice(null);

    try {
      await action();
      // 5초 주기를 기다리지 않고 즉시 다시 받아옵니다.
      refresh();
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setBusy(null);
    }
  };

  const handleSend = () => {
    const target = nickname.trim();

    if (!target) {
      return;
    }

    run("send", async () => {
      await sendFriendRequest(target);
      setNickname("");
      setNotice(`${target}님에게 친구 신청을 보냈어요.`);
    });
  };

  // 친구와 1:1 대화를 엽니다. 만든 뒤 바로 채팅 화면으로 넘어갑니다.
  const handleStartConversation = (friend: User) => {
    run(`chat-${friend.id}`, async () => {
      const conversation = await createConversation({
        title: `${friend.nickname}님과의 대화`,
        icon: friend.role === "SIGN_USER" ? "🤟" : "💬",
        category: "1:1 대화",
        participant_nicknames: [friend.nickname],
      });

      onConversationCreated(conversation.id);
    });
  };

  return (
    <div className="grid h-full grid-cols-1 gap-5 overflow-y-auto xl:grid-cols-[1fr_1fr]">
      {/* 왼쪽: 친구 찾기 + 받은 신청 */}
      <Panel className="animate-fade-up overflow-y-auto p-6">
        <div className="mb-5">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-600">
            친구 추가
          </p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">
            아이디로 찾기
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            친구의 이모지 아이디를 순서대로 골라주세요.
          </p>
        </div>

        {/* 아이디는 농인·청인 모두 이모지라 입력 방식이 하나뿐입니다. */}
        <div className="space-y-3">
          <EmojiIdDisplay
            value={nickname}
            placeholder="친구의 이모지 아이디를 골라주세요"
          />
          <EmojiPalette
            onPick={(emoji) =>
              setNickname((current) =>
                countGraphemes(current) >= MAX_ID_EMOJIS ? current : current + emoji
              )
            }
            onBackspace={() => setNickname((current) => removeLastGrapheme(current))}
            disabled={countGraphemes(nickname) >= MAX_ID_EMOJIS}
          />
          <ActionButton
            onClick={handleSend}
            disabled={!nickname.trim() || busy === "send"}
          >
            {busy === "send" ? "보내는 중…" : "🔍 친구 신청"}
          </ActionButton>
        </div>

        {error && (
          <p className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-600">
            {error}
          </p>
        )}

        {notice && (
          <p className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-700">
            {notice}
          </p>
        )}

        <div className="mt-8">
          <h4 className="text-lg font-black text-slate-900">
            받은 신청
            {incoming_requests.length > 0 && (
              <span className="ml-2 inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-pink-500 px-2 text-xs font-black text-white animate-soft-pulse">
                {incoming_requests.length}
              </span>
            )}
          </h4>

          {incoming_requests.length === 0 ? (
            <p className="mt-3 rounded-[24px] border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-400">
              받은 신청이 없어요
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {incoming_requests.map((request) => (
                <div
                  key={request.id}
                  className="animate-fade-up rounded-[24px] border border-sky-100 bg-sky-50 p-4"
                >
                  <div className="flex items-center gap-3">
                    <Avatar label={request.requester.nickname} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-base font-black text-slate-900">
                        {withDisplayName(
                          request.requester.nickname,
                          request.requester.display_name
                        )}
                      </p>
                      <p className="truncate text-xs font-semibold text-slate-500">
                        {roleLabel[request.requester.role]}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <ActionButton
                      onClick={() =>
                        run(`accept-${request.id}`, async () => {
                          await acceptFriendRequest(request.id);
                        })
                      }
                      disabled={busy === `accept-${request.id}`}
                    >
                      수락
                    </ActionButton>
                    <ActionButton
                      light
                      onClick={() =>
                        run(`reject-${request.id}`, async () => {
                          await rejectFriendRequest(request.id);
                        })
                      }
                      disabled={busy === `reject-${request.id}`}
                    >
                      거절
                    </ActionButton>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {outgoing_requests.length > 0 && (
          <div className="mt-8">
            <h4 className="text-lg font-black text-slate-900">보낸 신청</h4>
            <div className="mt-3 space-y-2">
              {outgoing_requests.map((request) => (
                <div
                  key={request.id}
                  className="flex items-center gap-3 rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3"
                >
                  <Avatar label={request.addressee.nickname} />
                  <p className="min-w-0 flex-1 truncate text-sm font-bold text-slate-700">
                    {withDisplayName(
                      request.addressee.nickname,
                      request.addressee.display_name
                    )}
                  </p>
                  <span className="shrink-0 rounded-full bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-700">
                    수락 대기 중
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {/* 오른쪽: 친구 목록 → 대화 시작 */}
      <Panel className="animate-fade-up overflow-y-auto p-6">
        <div className="mb-5">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-500">
            내 친구
          </p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">
            친구 {friends.length}명
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            친구를 눌러 대화를 시작합니다.
          </p>
        </div>

        {loading && friends.length === 0 && (
          <p className="py-10 text-center text-sm font-bold text-slate-400">
            불러오는 중…
          </p>
        )}

        {!loading && friends.length === 0 && (
          <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
            <p className="text-4xl">👋</p>
            <p className="mt-4 text-base font-black text-slate-700">
              아직 친구가 없어요
            </p>
            <p className="mt-2 text-sm text-slate-400">
              왼쪽에서 이모지 아이디로 친구를 찾아보세요.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {friends.map((friend) => (
            <div
              key={friend.id}
              className="group flex items-center gap-3 rounded-[24px] border border-slate-200 bg-slate-50 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-sky-200 hover:bg-white hover:shadow-lg"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#22C1FF_0%,#1D4ED8_100%)] text-2xl text-white shadow-[0_14px_30px_rgba(29,78,216,0.24)]">
                {friend.role === "SIGN_USER" ? "🤟" : "✍️"}
              </div>

              <div className="min-w-0 flex-1">
                <p className="truncate text-base font-black text-slate-900">
                  {withDisplayName(friend.nickname, friend.display_name)}
                </p>
                <p className="truncate text-xs font-semibold text-slate-400">
                  {roleLabel[friend.role]}
                </p>
              </div>

              <ActionButton
                onClick={() => handleStartConversation(friend)}
                disabled={busy === `chat-${friend.id}`}
              >
                {busy === `chat-${friend.id}` ? "여는 중…" : "💬 대화"}
              </ActionButton>
            </div>
          ))}
        </div>

        <div className="mt-8 rounded-[24px] bg-sky-50 p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-700">
            내 아이디
          </p>
          <p className="mt-2 text-lg font-black text-slate-900">
            {currentUser.nickname}
          </p>
          <p className="mt-1 text-xs leading-5 text-sky-700">
            친구가 이 아이디로 나를 찾을 수 있어요. 고른 순서 그대로 알려주세요.
          </p>
        </div>
      </Panel>
    </div>
  );
}
