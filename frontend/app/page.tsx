"use client";

import { useCallback, useEffect, useState } from "react";

import { ChatView } from "@/components/ChatView";
import { FriendsView } from "@/components/FriendsView";
import { LoginScreen } from "@/components/LoginScreen";
import {
  SequenceModal,
  type SequenceModalState,
  type SequenceRequest,
} from "@/components/SequenceModal";
import { SettingsView } from "@/components/SettingsView";
import { TranslatorView } from "@/components/TranslatorView";
import { MotionStyles, SidebarButton, StatusPill } from "@/components/ui";
import { useConversations } from "@/hooks/useConversations";
import { useSignVideoDictionary } from "@/hooks/useSignVideoDictionary";
import { setAccessToken } from "@/lib/api/client";
import {
  listQuickKeywords,
  logout,
  restoreSession,
  setCaptureTarget,
} from "@/lib/api/endpoints";
import { firstGrapheme } from "@/lib/graphemes";
import { roleLabel, withDisplayName } from "@/lib/types";
import type { QuickKeyword, User } from "@/lib/types";

type MenuType = "chat" | "friends" | "translator" | "settings";

export default function Page() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  // 첫 화면을 그리기 전에 Refresh 쿠키로 세션을 되살려봅니다. 이게 끝나기 전에
  // 로그인 화면을 그리면, 이미 로그인된 사람에게 로그인 화면이 번쩍 스칩니다.
  const [booting, setBooting] = useState(true);
  const [activeMenu, setActiveMenu] = useState<MenuType>("chat");

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [quickKeywords, setQuickKeywords] = useState<QuickKeyword[]>([]);

  const [sequenceModal, setSequenceModal] = useState<SequenceModalState>({
    open: false,
    title: "",
    sequence: [],
  });

  const { lookup, matchInText } = useSignVideoDictionary(currentUser !== null);

  // 명세 10장: 토큰 갱신까지 실패하면 로그인 화면으로 이동합니다.
  const handleAuthExpired = useCallback(() => {
    setAccessToken(null);
    setCurrentUser(null);
    setSelectedId(null);
  }, []);

  // 명세 10장대로 Access Token은 메모리에만 둡니다 — 새로고침하면 사라집니다.
  // 대신 Refresh 쿠키(HttpOnly, 7일)로 되살립니다. 이게 없으면 새로고침할 때마다,
  // 개발 중에는 파일을 저장할 때마다 로그인 화면으로 튕깁니다.
  useEffect(() => {
    let cancelled = false;

    restoreSession()
      .then((user) => {
        if (!cancelled && user) {
          setCurrentUser(user);
        }
      })
      .catch(() => {
        // 되살리기 실패는 그냥 "로그인 안 된 상태"입니다. 오류를 띄우지 않습니다.
      })
      .finally(() => {
        if (!cancelled) {
          setBooting(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // 목록을 주기적으로 다시 받아옵니다 — 최근 메시지가 온 대화가 위로 올라오고,
  // 상대가 만든 새 대화도 알아서 나타납니다.
  const { conversations, refresh: refreshConversations } = useConversations(
    currentUser !== null,
    handleAuthExpired
  );

  // 아직 아무 방도 안 골랐으면 맨 위(= 가장 최근) 대화를 띄웁니다.
  // 이미 고른 방이 있으면 폴링으로 순서가 바뀌어도 건드리지 않습니다.
  const selectedConversationId =
    selectedId !== null &&
    conversations.some((conversation) => conversation.id === selectedId)
      ? selectedId
      : conversations[0]?.id ?? null;

  // 촬영 버튼(아두이노)을 눌렀을 때 결과가 어디로 갈지 서버에 등록해둡니다.
  // 채팅 화면에서 방을 열어두고 있으면 그 방으로, 번역기 화면을 보고 있으면
  // 대화방 없이 번역기로. 기기는 목적지를 모른 채 촬영만 하면 됩니다.
  //
  // 채팅 화면인데 아직 방을 못 고른 경우(대화 0개)는 등록할 대화가 없으므로
  // 번역기 모드로 둡니다 — 그래야 촬영분이 사라지지 않고 번역기 화면에 남습니다.
  const captureConversationId =
    activeMenu === "chat" && selectedConversationId !== null
      ? selectedConversationId
      : null;

  useEffect(() => {
    if (!currentUser) {
      return;
    }

    setCaptureTarget(captureConversationId).catch(() => {
      // 등록 실패는 조용히 넘깁니다. 화면을 다시 옮기면 또 시도하고,
      // 실패해도 촬영분은 번역기 모드로 안전하게 떨어집니다.
    });
  }, [currentUser, captureConversationId]);

  useEffect(() => {
    if (!currentUser) {
      return;
    }

    let cancelled = false;

    listQuickKeywords()
      .then((result) => {
        if (!cancelled) {
          setQuickKeywords(result);
        }
      })
      .catch(() => {
        // 빠른 키워드는 보조 기능이라 실패해도 화면은 계속 동작합니다.
      });

    return () => {
      cancelled = true;
    };
  }, [currentUser]);

  const openSequence = (request: SequenceRequest) => {
    setSequenceModal({ open: true, ...request });
  };

  // 친구 화면에서 대화를 만들면 폴링 주기를 기다리지 않고 바로 그 방으로 데려갑니다.
  const handleConversationCreated = (conversationId: number) => {
    refreshConversations();
    setSelectedId(conversationId);
    setActiveMenu("chat");
  };

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      handleAuthExpired();
    }
  };

  // 세션 복구 중. 잠깐이지만 여기서 로그인 화면을 그리면 이미 로그인된 사람에게도
  // 화면이 번쩍 스쳤다가 넘어갑니다.
  if (booting) {
    return (
      <>
        <MotionStyles />
        <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_15%_18%,rgba(56,189,248,0.24),transparent_30%),linear-gradient(135deg,#07111f_0%,#0b1f4e_48%,#0f2a5f_100%)]">
          <div className="animate-fade-up text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-white text-2xl font-black text-slate-950 shadow-[0_24px_70px_rgba(0,0,0,0.32)]">
              잇
            </div>
            <p className="mt-5 text-sm font-bold text-sky-100/70">불러오는 중…</p>
          </div>
        </main>
      </>
    );
  }

  if (!currentUser) {
    return (
      <>
        <MotionStyles />
        <LoginScreen onLogin={setCurrentUser} />
      </>
    );
  }

  const isSignUser = currentUser.role === "SIGN_USER";

  return (
    <div className="h-screen overflow-hidden bg-[#edf5fc] text-slate-900">
      <MotionStyles />

      <div className="grid h-screen grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="relative hidden h-screen overflow-hidden bg-[radial-gradient(circle_at_12%_8%,rgba(56,189,248,0.34),transparent_32%),linear-gradient(180deg,#071430_0%,#0B1F4E_58%,#0E2A64_100%)] p-5 text-white lg:block">
          <div className="pointer-events-none absolute -right-24 top-12 h-56 w-56 rounded-full bg-sky-400/20 blur-3xl animate-float-glow" />
          <div className="pointer-events-none absolute -left-24 bottom-20 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl animate-float-glow" />

          <div className="relative z-10 flex h-full flex-col">
            <div className="animate-fade-up">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/95 text-2xl font-black text-slate-900 shadow-[0_16px_40px_rgba(0,0,0,0.25)] transition-all duration-300 hover:-translate-y-1">
                잇
              </div>

              <h1 className="text-[1.9rem] font-black tracking-tight">잇손</h1>
              <p className="mt-1 text-sm font-semibold text-sky-100/90">
                Itson
              </p>
            </div>

            <nav className="relative z-10 mt-10 space-y-3">
              <SidebarButton
                active={activeMenu === "chat"}
                icon="💬"
                label="채팅"
                onClick={() => setActiveMenu("chat")}
              />
              <SidebarButton
                active={activeMenu === "friends"}
                icon="👫"
                label="친구"
                onClick={() => setActiveMenu("friends")}
              />
              <SidebarButton
                active={activeMenu === "translator"}
                icon="🔄"
                label="번역기"
                onClick={() => setActiveMenu("translator")}
              />
              <SidebarButton
                active={activeMenu === "settings"}
                icon="⚙️"
                label="설정"
                onClick={() => setActiveMenu("settings")}
              />
            </nav>

            <div className="relative z-10 mt-auto rounded-[26px] border border-white/10 bg-white/10 p-4 backdrop-blur-xl">
              <p className="text-sm font-bold text-white/95">
                {isSignUser ? "🤟 수어로 말하기" : "🧠 AI 통역"}
              </p>
              <p className="mt-2 whitespace-pre-line text-xs leading-6 text-sky-50/70">
                {isSignUser
                  ? "🔘 버튼 → 💡 LED → 📷 촬영\n결과는 지금 보고 있는 화면으로 갑니다."
                  : "문장을 그냥 쓰면\nAI가 수어 단어로 바꿔줍니다."}
              </p>
            </div>
          </div>
        </aside>

        <main className="flex h-screen min-w-0 flex-col">
          <header className="relative flex h-20 shrink-0 items-center justify-between overflow-hidden border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(56,189,248,0.22),transparent_28%),linear-gradient(90deg,#071430_0%,#0A2252_55%,#0C2E70_100%)] px-6 text-white">
            <div className="relative z-10">
              <h2 className="text-2xl font-black tracking-tight">
                {activeMenu === "chat" && "💬 채팅"}
                {activeMenu === "friends" && "👫 친구"}
                {activeMenu === "translator" && "🔄 번역기 모드"}
                {activeMenu === "settings" && "⚙️ 설정"}
              </h2>
              <p className="mt-1 text-xs font-medium text-sky-100/70">
                {activeMenu === "chat" &&
                  (isSignUser
                    ? "🤟 촬영하면 AI가 분석해서 대화에 올려줍니다."
                    : "⌨️ 농인의 수어 메시지는 왼쪽, 내 답변은 오른쪽에 보입니다.")}
                {activeMenu === "friends" &&
                  "이모지 아이디로 친구를 찾아 대화를 시작합니다."}
                {activeMenu === "translator" &&
                  "🎥 촬영하면 결과가 여기에 나타납니다. 대화방 없이 그 자리에서 번역합니다."}
                {activeMenu === "settings" && "계정 정보와 연결 상태를 확인합니다."}
              </p>
            </div>

            <div className="relative z-10 flex items-center gap-2">
              <StatusPill
                label={`${isSignUser ? "🤟" : "⌨️"} ${roleLabel[currentUser.role]}`}
                tone="sky"
              />

              <div className="ml-2 flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-3 py-2 backdrop-blur-xl">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-sm font-black text-slate-950">
                  {firstGrapheme(currentUser.nickname)}
                </div>
                <div className="hidden leading-tight xl:block">
                  <p className="text-xs font-black text-white">
                    {withDisplayName(currentUser.nickname, currentUser.display_name)}
                  </p>
                  <p className="mt-0.5 text-[11px] font-medium text-sky-100/70">
                    user #{currentUser.id}
                  </p>
                </div>
              </div>
            </div>
          </header>

          <section className="min-h-0 flex-1 overflow-hidden p-5">
            {activeMenu === "chat" && (
              <ChatView
                conversations={conversations}
                selectedId={selectedConversationId}
                onSelectConversation={setSelectedId}
                currentUser={currentUser}
                quickKeywords={quickKeywords}
                lookup={lookup}
                matchInText={matchInText}
                onOpenSequence={openSequence}
                onAuthExpired={handleAuthExpired}
              />
            )}

            {activeMenu === "friends" && (
              <FriendsView
                currentUser={currentUser}
                onConversationCreated={handleConversationCreated}
              />
            )}

            {activeMenu === "translator" && (
              <TranslatorView
                currentUser={currentUser}
                quickKeywords={quickKeywords}
                lookup={lookup}
                onOpenSequence={openSequence}
              />
            )}

            {activeMenu === "settings" && (
              <SettingsView
                currentUser={currentUser}
                onUpdateUser={setCurrentUser}
                onLogout={handleLogout}
              />
            )}
          </section>
        </main>
      </div>

      {sequenceModal.open && (
        <SequenceModal
          modal={sequenceModal}
          onClose={() =>
            setSequenceModal({ open: false, title: "", sequence: [] })
          }
        />
      )}
    </div>
  );
}
