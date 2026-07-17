"use client";

import { useCallback, useEffect, useState } from "react";

import { ChatView } from "@/components/ChatView";
import { FriendsView } from "@/components/FriendsView";
import { LoginScreen } from "@/components/LoginScreen";
import { SequenceModal, type SequenceModalState } from "@/components/SequenceModal";
import { SettingsView } from "@/components/SettingsView";
import { TranslatorView } from "@/components/TranslatorView";
import { MotionStyles, SidebarButton, StatusPill } from "@/components/ui";
import { useSignVideoDictionary } from "@/hooks/useSignVideoDictionary";
import { setAccessToken } from "@/lib/api/client";
import { listConversations, listQuickKeywords, logout } from "@/lib/api/endpoints";
import { roleLabel } from "@/lib/types";
import type {
  Conversation,
  QuickKeyword,
  SignVideoSequenceItem,
  User,
} from "@/lib/types";

type MenuType = "chat" | "friends" | "translator" | "settings";

export default function Page() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeMenu, setActiveMenu] = useState<MenuType>("chat");

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [quickKeywords, setQuickKeywords] = useState<QuickKeyword[]>([]);

  const [sequenceModal, setSequenceModal] = useState<SequenceModalState>({
    open: false,
    title: "",
    sequence: [],
  });

  const { lookup } = useSignVideoDictionary(currentUser !== null);

  // 명세 10장: 토큰 갱신까지 실패하면 로그인 화면으로 이동합니다.
  const handleAuthExpired = useCallback(() => {
    setAccessToken(null);
    setCurrentUser(null);
    setConversations([]);
    setSelectedId(null);
  }, []);

  // 로그인하면 대화 목록과 빠른 키워드를 받아옵니다.
  useEffect(() => {
    if (!currentUser) {
      return;
    }

    let cancelled = false;

    listConversations()
      .then((result) => {
        if (cancelled) {
          return;
        }

        setConversations(result);
        setSelectedId((current) => current ?? result[0]?.id ?? null);
      })
      .catch(handleAuthExpired);

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
  }, [currentUser, handleAuthExpired]);

  const openSequence = (
    title: string,
    sequence: SignVideoSequenceItem[],
    description?: string
  ) => {
    setSequenceModal({ open: true, title, sequence, description });
  };

  // 친구 화면에서 대화를 만들면 목록에 넣고 바로 그 방으로 데려갑니다.
  const handleConversationCreated = async (conversationId: number) => {
    try {
      setConversations(await listConversations());
    } catch {
      // 목록 갱신에 실패해도 방으로는 들어갑니다.
    }

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
                손
              </div>

              <h1 className="text-[1.9rem] font-black tracking-tight">손말이음</h1>
              <p className="mt-1 text-sm font-semibold text-sky-100/90">
                Visual Sign Bridge
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
                icon="👥"
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
              <p className="text-sm font-bold text-white/95">시연 시나리오 4종</p>
              <p className="mt-2 text-xs leading-6 text-sky-50/70">
                👫 친구 · 🧭 길찾기
                <br />
                🏥 병원 · 🏦 은행
              </p>
            </div>
          </div>
        </aside>

        <main className="flex h-screen min-w-0 flex-col">
          <header className="relative flex h-20 shrink-0 items-center justify-between overflow-hidden border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(56,189,248,0.22),transparent_28%),linear-gradient(90deg,#071430_0%,#0A2252_55%,#0C2E70_100%)] px-6 text-white">
            <div className="relative z-10">
              <h2 className="text-2xl font-black tracking-tight">
                {activeMenu === "chat" && "💬 폴라로이드 채팅"}
                {activeMenu === "friends" && "👥 친구"}
                {activeMenu === "translator" && "🔄 번역기 모드"}
                {activeMenu === "settings" && "⚙️ 설정"}
              </h2>
              <p className="mt-1 text-xs font-medium text-sky-100/70">
                {activeMenu === "chat" &&
                  (isSignUser
                    ? "🤟 촬영하면 AI가 분석해서 대화에 올려줍니다."
                    : "⌨️ 농인의 수어 메시지는 왼쪽, 내 답변은 오른쪽에 보입니다.")}
                {activeMenu === "friends" &&
                  "닉네임으로 친구를 찾아 대화를 시작합니다."}
                {activeMenu === "translator" &&
                  "🔘 버튼을 누르면 촬영이 시작되고 결과가 여기에 나타납니다."}
                {activeMenu === "settings" && "계정 정보와 구현 현황을 확인합니다."}
              </p>
            </div>

            <div className="relative z-10 flex items-center gap-2">
              <StatusPill
                label={`${isSignUser ? "🤟" : "⌨️"} ${roleLabel[currentUser.role]}`}
                tone="sky"
              />

              <div className="ml-2 flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-3 py-2 backdrop-blur-xl">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-sm font-black text-slate-950">
                  {currentUser.nickname.slice(0, 1)}
                </div>
                <div className="hidden leading-tight xl:block">
                  <p className="text-xs font-black text-white">
                    {currentUser.nickname}
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
                selectedId={selectedId}
                onSelectConversation={setSelectedId}
                currentUser={currentUser}
                quickKeywords={quickKeywords}
                lookup={lookup}
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
