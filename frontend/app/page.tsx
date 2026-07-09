"use client";

import { useMemo, useState, type ReactNode } from "react";

type MenuType = "chat" | "translator" | "settings";
type UserRole = "signUser" | "hearingUser";

type CurrentUser = {
  id: string;
  nickname: string;
  email: string;
  role: UserRole;
};

type Participant = {
  id: string;
  name: string;
  role: UserRole;
};

type SignVideoItem = {
  keyword: string;
  title: string;
  url?: string;
  symbol: string;
};

type ChatMessage = {
  id: number;
  senderId: string;
  senderName: string;
  time: string;
  type: "sign-to-text" | "text-to-sign" | "memo";
  text: string;
  keywords?: string[];
  confidence?: number;
  signVideoSequence?: SignVideoItem[];
};

type ChatRoom = {
  id: string;
  name: string;
  icon: string;
  preview: string;
  category: string;
  unread?: number;
  participants: Participant[];
  messages: ChatMessage[];
};

type SequenceModalState = {
  open: boolean;
  title: string;
  description?: string;
  sequence: SignVideoItem[];
};

const roleLabelMap: Record<UserRole, string> = {
  signUser: "수어 사용자",
  hearingUser: "비장애인 / 직원",
};

const demoUsers: Record<"minji" | "staff", CurrentUser> = {
  minji: {
    id: "user-a",
    nickname: "민지",
    email: "minji@signbridge.kr",
    role: "signUser",
  },
  staff: {
    id: "user-b",
    nickname: "직원",
    email: "staff@signbridge.kr",
    role: "hearingUser",
  },
};

const signVideoLibrary: Record<string, SignVideoItem> = {
  토요일: {
    keyword: "토요일",
    title: "토요일",
    url: "/videos/saturday_sign.mp4",
    symbol: "토",
  },
  약속: {
    keyword: "약속",
    title: "약속",
    url: "/videos/promise_sign.mp4",
    symbol: "약",
  },
  미안하다: {
    keyword: "미안하다",
    title: "미안하다",
    url: "/videos/sorry_sign.mp4",
    symbol: "미",
  },
  화장실: {
    keyword: "화장실",
    title: "화장실",
    symbol: "화",
  },
  어디: {
    keyword: "어디",
    title: "어디",
    symbol: "?",
  },
  도움: {
    keyword: "도움",
    title: "도움",
    symbol: "!",
  },
  기다려: {
    keyword: "기다려",
    title: "기다려",
    symbol: "기",
  },
  천천히: {
    keyword: "천천히",
    title: "천천히",
    symbol: "천",
  },
};

function makeSignSequence(keywords: string[]): SignVideoItem[] {
  return keywords.map((keyword) => {
    return (
      signVideoLibrary[keyword] ?? {
        keyword,
        title: keyword,
        symbol: keyword.slice(0, 1),
      }
    );
  });
}

const quickKeywords = [
  "토요일",
  "약속",
  "미안하다",
  "화장실",
  "어디",
  "도움",
  "기다려",
  "천천히",
];

const chatRoomsMock: ChatRoom[] = [
  {
    id: "room-1",
    name: "민지와 직원",
    icon: "수어",
    category: "대면 상담",
    preview: "토요일 약속 미안하다",
    unread: 2,
    participants: [
      { id: "user-a", name: "민지", role: "signUser" },
      { id: "user-b", name: "직원", role: "hearingUser" },
    ],
    messages: [
      {
        id: 1,
        senderId: "user-a",
        senderName: "민지",
        time: "14:31",
        type: "sign-to-text",
        text: "화장실 어디예요?",
        keywords: ["화장실", "어디"],
        confidence: 0.88,
      },
      {
        id: 2,
        senderId: "user-b",
        senderName: "직원",
        time: "14:33",
        type: "text-to-sign",
        text: "토요일 약속 미안하다",
        keywords: ["토요일", "약속", "미안하다"],
        signVideoSequence: makeSignSequence(["토요일", "약속", "미안하다"]),
      },
      {
        id: 3,
        senderId: "user-a",
        senderName: "민지",
        time: "14:35",
        type: "memo",
        text: "잠시만 기다려 주세요",
      },
    ],
  },
  {
    id: "room-2",
    name: "접수 창구",
    icon: "필담",
    category: "공공창구",
    preview: "서류 확인 후 다시 안내드릴게요",
    participants: [
      { id: "user-c", name: "지훈", role: "signUser" },
      { id: "user-b", name: "직원", role: "hearingUser" },
    ],
    messages: [
      {
        id: 1,
        senderId: "user-b",
        senderName: "직원",
        time: "10:20",
        type: "memo",
        text: "서류 확인 후 다시 안내드릴게요.",
      },
    ],
  },
  {
    id: "room-3",
    name: "가족 대화",
    icon: "채팅",
    category: "가족",
    preview: "토요일 약속 미안하다",
    unread: 1,
    participants: [
      { id: "user-a", name: "민지", role: "signUser" },
      { id: "user-d", name: "가족", role: "hearingUser" },
    ],
    messages: [
      {
        id: 1,
        senderId: "user-d",
        senderName: "가족",
        time: "09:10",
        type: "text-to-sign",
        text: "토요일 약속 미안하다",
        keywords: ["토요일", "약속", "미안하다"],
        signVideoSequence: makeSignSequence(["토요일", "약속", "미안하다"]),
      },
    ],
  },
];

function getRoomDisplayName(room: ChatRoom, currentUser: CurrentUser) {
  const otherParticipant = room.participants.find(
    (participant) => participant.id !== currentUser.id
  );

  const isCurrentUserInRoom = room.participants.some(
    (participant) => participant.id === currentUser.id
  );

  if (isCurrentUserInRoom && otherParticipant) {
    return otherParticipant.name;
  }

  return room.name;
}

export default function Page() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);

  const [activeMenu, setActiveMenu] = useState<MenuType>("chat");
  const [selectedRoomId, setSelectedRoomId] = useState("room-1");
  const [keywordInput, setKeywordInput] = useState("토요일, 약속, 미안하다");
  const [sentenceInput, setSentenceInput] = useState("토요일 약속 미안하다");
  const [previewKeywords, setPreviewKeywords] = useState([
    "토요일",
    "약속",
    "미안하다",
  ]);

  const [sequenceModal, setSequenceModal] = useState<SequenceModalState>({
    open: false,
    title: "",
    description: "",
    sequence: [],
  });

  const selectedRoom =
    chatRoomsMock.find((room) => room.id === selectedRoomId) ?? chatRoomsMock[0];

  const previewSequence = useMemo(() => {
    return makeSignSequence(previewKeywords);
  }, [previewKeywords]);

  const openSequenceModal = (
    title: string,
    sequence: SignVideoItem[],
    description?: string
  ) => {
    setSequenceModal({
      open: true,
      title,
      description,
      sequence,
    });
  };

  const closeSequenceModal = () => {
    setSequenceModal({
      open: false,
      title: "",
      description: "",
      sequence: [],
    });
  };

  const handleAppendKeyword = (keyword: string) => {
    const current = keywordInput
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    if (!current.includes(keyword)) {
      const next = [...current, keyword];
      setKeywordInput(next.join(", "));
      setPreviewKeywords(next);
    }

    setActiveMenu("translator");
  };

  const handleGenerateFromKeywords = () => {
    const keywords = keywordInput
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    setPreviewKeywords(keywords);
  };

  const handleGenerateFromSentence = () => {
    const matched = Object.keys(signVideoLibrary).filter((keyword) =>
      sentenceInput.includes(keyword)
    );

    if (matched.length > 0) {
      setPreviewKeywords(matched);
      return;
    }

    const fallback = sentenceInput
      .split(/\s+/)
      .map((item) => item.trim())
      .filter(Boolean);

    setPreviewKeywords(fallback);
  };

  if (!currentUser) {
    return (
      <>
        <MotionStyles />
        <LoginScreen onLogin={setCurrentUser} />
      </>
    );
  }

  return (
    <div className="h-screen overflow-hidden bg-[#edf5fc] text-slate-900">
      <MotionStyles />

      <div className="grid h-screen grid-cols-[260px_minmax(0,1fr)]">
        <aside className="relative hidden h-screen overflow-hidden bg-[radial-gradient(circle_at_12%_8%,rgba(56,189,248,0.34),transparent_32%),linear-gradient(180deg,#071430_0%,#0B1F4E_58%,#0E2A64_100%)] p-5 text-white lg:block">
          <div className="pointer-events-none absolute -right-24 top-12 h-56 w-56 rounded-full bg-sky-400/20 blur-3xl animate-float-glow" />
          <div className="pointer-events-none absolute -left-24 bottom-20 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl animate-float-glow" />

          <div className="relative z-10 flex h-full flex-col">
            <div className="animate-fade-up">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/95 text-2xl font-black text-slate-900 shadow-[0_16px_40px_rgba(0,0,0,0.25)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_22px_50px_rgba(0,0,0,0.32)]">
                손
              </div>

              <h1 className="text-[1.9rem] font-black tracking-tight">
                손말이음
              </h1>
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
                active={activeMenu === "translator"}
                icon="↔"
                label="번역기"
                onClick={() => setActiveMenu("translator")}
              />
              <SidebarButton
                active={activeMenu === "settings"}
                icon="⚙"
                label="설정"
                onClick={() => setActiveMenu("settings")}
              />
            </nav>

            <div className="relative z-10 mt-auto rounded-[26px] border border-white/10 bg-white/10 p-4 backdrop-blur-xl transition-all duration-300 hover:bg-white/[0.13]">
              <p className="text-sm font-bold text-white/95">Prototype v1</p>
              <p className="mt-2 text-xs leading-6 text-sky-50/70">
                senderId 기반 mockData입니다.
                <br />
                로그인 계정에 따라 같은 메시지도 나/상대가 다르게 보입니다.
              </p>
            </div>
          </div>
        </aside>

        <main className="flex h-screen min-w-0 flex-col">
          <AppHeader activeMenu={activeMenu} currentUser={currentUser} />

          <section className="min-h-0 flex-1 overflow-hidden p-5">
            {activeMenu === "chat" && (
              <ChatView
                selectedRoom={selectedRoom}
                selectedRoomId={selectedRoomId}
                currentUser={currentUser}
                onSelectRoom={setSelectedRoomId}
                quickKeywords={quickKeywords}
                onAppendKeyword={handleAppendKeyword}
                onOpenSequenceModal={openSequenceModal}
              />
            )}

            {activeMenu === "translator" && (
              <TranslatorView
                currentUser={currentUser}
                keywordInput={keywordInput}
                setKeywordInput={setKeywordInput}
                sentenceInput={sentenceInput}
                setSentenceInput={setSentenceInput}
                previewKeywords={previewKeywords}
                previewSequence={previewSequence}
                quickKeywords={quickKeywords}
                onAppendKeyword={handleAppendKeyword}
                onGenerateFromKeywords={handleGenerateFromKeywords}
                onGenerateFromSentence={handleGenerateFromSentence}
                onOpenSequenceModal={openSequenceModal}
              />
            )}

            {activeMenu === "settings" && (
              <SettingsView
                currentUser={currentUser}
                onUpdateUser={setCurrentUser}
                onLogout={() => setCurrentUser(null)}
              />
            )}
          </section>
        </main>
      </div>

      {sequenceModal.open && (
        <SequenceModal modal={sequenceModal} onClose={closeSequenceModal} />
      )}
    </div>
  );
}

function MotionStyles() {
  return (
    <style jsx global>{`
      @keyframes fadeUp {
        from {
          opacity: 0;
          transform: translateY(16px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      @keyframes softScale {
        from {
          opacity: 0;
          transform: scale(0.96);
        }
        to {
          opacity: 1;
          transform: scale(1);
        }
      }

      @keyframes floatGlow {
        0% {
          transform: translate3d(0, 0, 0) scale(1);
        }
        50% {
          transform: translate3d(18px, -14px, 0) scale(1.08);
        }
        100% {
          transform: translate3d(0, 0, 0) scale(1);
        }
      }

      @keyframes softPulse {
        0%,
        100% {
          opacity: 0.8;
          transform: scale(1);
        }
        50% {
          opacity: 1;
          transform: scale(1.04);
        }
      }

      @keyframes slideInRight {
        from {
          opacity: 0;
          transform: translateX(22px);
        }
        to {
          opacity: 1;
          transform: translateX(0);
        }
      }

      @keyframes slideInLeft {
        from {
          opacity: 0;
          transform: translateX(-22px);
        }
        to {
          opacity: 1;
          transform: translateX(0);
        }
      }

      .animate-fade-up {
        animation: fadeUp 520ms ease both;
      }

      .animate-soft-scale {
        animation: softScale 220ms ease both;
      }

      .animate-float-glow {
        animation: floatGlow 10s ease-in-out infinite;
      }

      .animate-soft-pulse {
        animation: softPulse 2.4s ease-in-out infinite;
      }

      .animate-slide-right {
        animation: slideInRight 520ms ease both;
      }

      .animate-slide-left {
        animation: slideInLeft 520ms ease both;
      }
    `}</style>
  );
}

function LoginScreen({ onLogin }: { onLogin: (user: CurrentUser) => void }) {
  const [selectedRole, setSelectedRole] = useState<UserRole>("hearingUser");
  const [nickname, setNickname] = useState("채진");
  const [email, setEmail] = useState("demo@signbridge.kr");
  const [password, setPassword] = useState("password");

  const handleRoleChange = (role: UserRole) => {
    setSelectedRole(role);
  };

  const handleLogin = () => {
    const id = selectedRole === "signUser" ? "user-a" : "user-b";

    onLogin({
      id,
      nickname: nickname.trim() || "데모 사용자",
      email: email.trim() || "demo@signbridge.kr",
      role: selectedRole,
    });
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#07111f] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_18%,rgba(56,189,248,0.24),transparent_30%),radial-gradient(circle_at_82%_12%,rgba(37,99,235,0.22),transparent_28%),linear-gradient(135deg,#07111f_0%,#0b1f4e_48%,#0f2a5f_100%)]" />
      <div className="pointer-events-none absolute left-[12%] top-[18%] h-72 w-72 rounded-full bg-sky-400/20 blur-3xl animate-float-glow" />
      <div className="pointer-events-none absolute bottom-[12%] right-[12%] h-80 w-80 rounded-full bg-blue-500/20 blur-3xl animate-float-glow" />

      <div className="relative z-10 grid min-h-screen grid-cols-1 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="flex items-center px-8 py-10 lg:px-16">
          <div className="max-w-2xl animate-fade-up">
            <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-3xl bg-white text-2xl font-black text-slate-950 shadow-[0_24px_70px_rgba(0,0,0,0.32)]">
              손
            </div>

            <p className="text-sm font-bold uppercase tracking-[0.22em] text-sky-200">
              Visual Sign Bridge
            </p>

            <h1 className="mt-5 text-5xl font-black leading-tight tracking-[-0.05em] lg:text-6xl">
              같은 대화방,
              <br />
              다른 나의 화면
            </h1>

            <p className="mt-6 max-w-xl text-base leading-8 text-sky-50/70">
              민지와 직원은 같은 대화방을 봅니다.
              <br />
              하지만 로그인한 계정에 따라 내 메시지와 상대 메시지가 다르게 정렬됩니다.
            </p>

            <div className="mt-10 grid max-w-xl grid-cols-3 gap-3">
              {[
                ["senderId", "발신자 구분"],
                ["room", "공통 대화방"],
                ["role", "역할별 UI"],
              ].map(([title, desc], index) => (
                <div
                  key={title}
                  className="animate-fade-up rounded-3xl border border-white/10 bg-white/10 p-4 backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:bg-white/[0.14]"
                  style={{ animationDelay: `${index * 90}ms` }}
                >
                  <div className="text-lg font-black text-white">{title}</div>
                  <div className="mt-2 text-xs font-medium text-sky-100/70">
                    {desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-10">
          <div className="w-full max-w-md animate-soft-scale rounded-[34px] border border-white/15 bg-white/95 p-6 text-slate-950 shadow-[0_40px_120px_rgba(0,0,0,0.34)] backdrop-blur-xl">
            <div className="mb-6">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-600">
                Login
              </p>
              <h2 className="mt-2 text-3xl font-black tracking-tight">
                손말이음 시작하기
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                A/B 시연은 아래 데모 계정 버튼을 쓰면 가장 정확합니다.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => onLogin(demoUsers.minji)}
                className="rounded-[24px] border border-sky-300 bg-sky-50 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl"
              >
                <div className="text-sm font-black text-slate-950">
                  민지로 시작
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-400">
                  user-a · 수어 사용자
                </div>
              </button>

              <button
                type="button"
                onClick={() => onLogin(demoUsers.staff)}
                className="rounded-[24px] border border-indigo-200 bg-indigo-50 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl"
              >
                <div className="text-sm font-black text-slate-950">
                  직원으로 시작
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-400">
                  user-b · 비장애인/직원
                </div>
              </button>
            </div>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-slate-200" />
              <span className="text-xs font-bold text-slate-400">
                직접 입력
              </span>
              <div className="h-px flex-1 bg-slate-200" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <RoleButton
                active={selectedRole === "signUser"}
                title="수어 사용자"
                desc="수어 촬영 중심"
                onClick={() => handleRoleChange("signUser")}
              />
              <RoleButton
                active={selectedRole === "hearingUser"}
                title="비장애인 / 직원"
                desc="텍스트 입력 중심"
                onClick={() => handleRoleChange("hearingUser")}
              />
            </div>

            <form
              className="mt-6 space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                handleLogin();
              }}
            >
              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">
                  닉네임
                </span>
                <input
                  value={nickname}
                  onChange={(event) => setNickname(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-950 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                  placeholder="닉네임을 입력하세요"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">
                  이메일
                </span>
                <input
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-950 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                  placeholder="email@example.com"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-bold text-slate-700">
                  비밀번호
                </span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-950 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                  placeholder="password"
                />
              </label>

              <button className="w-full rounded-2xl bg-sky-500 px-5 py-3.5 text-sm font-black text-white shadow-[0_16px_38px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 hover:shadow-xl active:translate-y-0">
                로그인
              </button>
            </form>

            <div className="mt-6 rounded-[24px] bg-sky-50 p-4">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-700">
                시연 방법
              </p>
              <p className="mt-2 text-xs leading-5 text-sky-700">
                일반 창은 민지, 시크릿 창은 직원으로 로그인하면 같은 방에서
                나/상대가 다르게 보이는 구조를 확인할 수 있습니다.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function RoleButton({
  active,
  title,
  desc,
  onClick,
}: {
  active: boolean;
  title: string;
  desc: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-[24px] border p-4 text-left transition-all duration-300 hover:-translate-y-0.5 ${
        active
          ? "border-sky-300 bg-sky-50 shadow-[0_12px_30px_rgba(14,165,233,0.16)]"
          : "border-slate-200 bg-slate-50 hover:bg-white"
      }`}
    >
      <div className="text-sm font-black text-slate-950">{title}</div>
      <div className="mt-1 text-xs font-semibold text-slate-400">{desc}</div>
    </button>
  );
}

function AppHeader({
  activeMenu,
  currentUser,
}: {
  activeMenu: MenuType;
  currentUser: CurrentUser;
}) {
  return (
    <header className="relative flex h-20 shrink-0 items-center justify-between overflow-hidden border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(56,189,248,0.22),transparent_28%),linear-gradient(90deg,#071430_0%,#0A2252_55%,#0C2E70_100%)] px-6 text-white">
      <div className="pointer-events-none absolute right-20 top-[-90px] h-44 w-44 rounded-full bg-sky-400/20 blur-3xl animate-float-glow" />

      <div className="relative z-10 flex min-w-0 items-center gap-5">
        <div>
          <h2 className="text-2xl font-black tracking-tight">
            {activeMenu === "chat" && "Polaroid Chat"}
            {activeMenu === "translator" && "Translator Mode"}
            {activeMenu === "settings" && "System Settings"}
          </h2>
          <p className="mt-1 text-xs font-medium text-sky-100/70">
            {activeMenu === "chat" &&
              (currentUser.role === "signUser"
                ? "민지 기준: 내 수어 메시지는 오른쪽, 직원 답변은 왼쪽에 보입니다."
                : "직원 기준: 내 답변은 오른쪽, 민지의 수어 메시지는 왼쪽에 보입니다.")}
            {activeMenu === "translator" &&
              (currentUser.role === "signUser"
                ? "수어 영상 → 텍스트 흐름을 먼저 확인합니다."
                : "텍스트 → 수어 영상 흐름을 먼저 확인합니다.")}
            {activeMenu === "settings" &&
              "계정 정보, 역할, 장치 상태를 확인합니다."}
          </p>
        </div>
      </div>

      <div className="relative z-10 flex items-center gap-2">
        <StatusPill label={roleLabelMap[currentUser.role]} tone="sky" />
        <div className="hidden 2xl:flex items-center gap-2">
          <StatusPill label="카메라 연결" tone="sky" />
          <StatusPill label="LED 대기" tone="amber" />
          <StatusPill label="버튼 대기" tone="slate" />
        </div>
        <AccountCapsule currentUser={currentUser} />
        <button className="ml-2 rounded-2xl bg-pink-500 px-5 py-2.5 text-sm font-bold text-white shadow-[0_16px_40px_rgba(236,72,153,0.32)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-pink-400 active:translate-y-0">
          긴급 호출
        </button>
      </div>
    </header>
  );
}

function AccountCapsule({ currentUser }: { currentUser: CurrentUser }) {
  return (
    <div className="ml-2 flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-3 py-2 backdrop-blur-xl">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-sm font-black text-slate-950">
        {currentUser.nickname.slice(0, 1)}
      </div>
      <div className="hidden leading-tight xl:block">
        <p className="text-xs font-black text-white">{currentUser.nickname}</p>
        <p className="mt-0.5 max-w-[140px] truncate text-[11px] font-medium text-sky-100/70">
          {currentUser.email}
        </p>
      </div>
    </div>
  );
}

function ChatView({
  selectedRoom,
  selectedRoomId,
  currentUser,
  onSelectRoom,
  quickKeywords,
  onAppendKeyword,
  onOpenSequenceModal,
}: {
  selectedRoom: ChatRoom;
  selectedRoomId: string;
  currentUser: CurrentUser;
  onSelectRoom: (id: string) => void;
  quickKeywords: string[];
  onAppendKeyword: (keyword: string) => void;
  onOpenSequenceModal: (
    title: string,
    sequence: SignVideoItem[],
    description?: string
  ) => void;
}) {
  const isSignUser = currentUser.role === "signUser";
  const selectedRoomTitle = getRoomDisplayName(selectedRoom, currentUser);

  return (
    <div className="grid h-full grid-cols-1 gap-5 xl:grid-cols-[310px_minmax(0,1fr)]">
      <Panel className="animate-fade-up flex min-h-0 flex-col p-5">
        <div className="mb-4">
          <h3 className="text-xl font-black tracking-tight text-slate-900">
            대화 목록
          </h3>
          <p className="mt-1 text-xs font-medium text-slate-400">
            같은 방이라도 로그인 계정에 따라 상대 이름이 달라집니다.
          </p>
        </div>

        <div className="space-y-3 overflow-y-auto pr-1">
          {chatRoomsMock.map((room, index) => {
            const displayName = getRoomDisplayName(room, currentUser);

            return (
              <button
                key={room.id}
                onClick={() => onSelectRoom(room.id)}
                className={`group w-full rounded-[24px] border p-3 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl ${
                  room.id === selectedRoomId
                    ? "border-sky-300 bg-sky-50 shadow-[0_12px_30px_rgba(56,189,248,0.16)]"
                    : "border-slate-200 bg-slate-50 hover:border-sky-200 hover:bg-white"
                }`}
                style={{ animationDelay: `${index * 70}ms` }}
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#22C1FF_0%,#1D4ED8_100%)] text-xs font-black text-white shadow-[0_14px_30px_rgba(29,78,216,0.24)] transition-transform duration-300 group-hover:scale-105">
                    {room.icon}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="truncate text-base font-black text-slate-900">
                        {displayName}
                      </h4>
                      {room.unread ? (
                        <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-pink-500 px-2 text-xs font-black text-white animate-soft-pulse">
                          {room.unread}
                        </span>
                      ) : null}
                    </div>

                    <p className="mt-1 truncate text-xs font-medium text-slate-400">
                      {room.preview}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="mt-6 shrink-0">
          <h4 className="mb-3 text-base font-black text-slate-900">
            빠른 키워드
          </h4>
          <div className="flex flex-wrap gap-2">
            {quickKeywords.map((keyword) => (
              <button
                key={keyword}
                onClick={() => onAppendKeyword(keyword)}
                className="rounded-full border border-sky-100 bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-700 transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-100 hover:shadow-md active:translate-y-0"
              >
                {keyword}
              </button>
            ))}
          </div>
        </div>
      </Panel>

      <Panel className="animate-fade-up flex min-h-0 flex-col overflow-hidden">
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white/90 px-6 py-4 backdrop-blur">
          <div>
            <h3 className="text-xl font-black text-slate-900">
              {selectedRoomTitle}와 대화
            </h3>
            <p className="mt-1 text-xs font-medium text-slate-400">
              {isSignUser
                ? "현재 민지 계정입니다. 민지가 보낸 메시지가 오른쪽에 표시됩니다."
                : "현재 직원 계정입니다. 직원이 보낸 메시지가 오른쪽에 표시됩니다."}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-600">
              저장 중
            </span>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-bold text-slate-500">
              senderId mock
            </span>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto bg-[radial-gradient(circle_at_20%_10%,rgba(56,189,248,0.12),transparent_26%),linear-gradient(180deg,#F8FBFF_0%,#EEF6FF_100%)] px-6 py-5">
          <div className="mx-auto max-w-5xl space-y-5">
            {selectedRoom.messages.map((message, index) => (
              <ChatBubble
                key={message.id}
                message={message}
                index={index}
                currentUser={currentUser}
                onOpenSequenceModal={onOpenSequenceModal}
              />
            ))}
          </div>
        </div>

        <div className="shrink-0 border-t border-slate-200 bg-white/95 px-6 py-4 backdrop-blur">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {isSignUser ? (
              <>
                <ActionButton dark>📷 수어 촬영</ActionButton>
                <ActionButton>필담 크게 쓰기</ActionButton>
                <ActionButton light>상대방 답변 보기</ActionButton>
              </>
            ) : (
              <>
                <ActionButton>글 입력</ActionButton>
                <ActionButton dark>수어 영상 만들기</ActionButton>
                <ActionButton light>필담</ActionButton>
              </>
            )}
          </div>
        </div>
      </Panel>
    </div>
  );
}

function ChatBubble({
  message,
  index,
  currentUser,
  onOpenSequenceModal,
}: {
  message: ChatMessage;
  index: number;
  currentUser: CurrentUser;
  onOpenSequenceModal: (
    title: string,
    sequence: SignVideoItem[],
    description?: string
  ) => void;
}) {
  const isMine = message.senderId === currentUser.id;
  const displayName = isMine ? `${currentUser.nickname} · 나` : message.senderName;

  return (
    <div
      className={`flex ${
        isMine ? "justify-end animate-slide-right" : "justify-start animate-slide-left"
      }`}
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <div className={`w-full max-w-[620px] ${isMine ? "ml-10" : "mr-10"}`}>
        <div
          className={`mb-2 flex items-center gap-2 px-2 ${
            isMine ? "justify-end" : "justify-start"
          }`}
        >
          {!isMine && <Avatar label={displayName} />}
          <span className="text-sm font-bold text-slate-500">
            {displayName}
          </span>
          <span className="text-xs font-semibold text-slate-400">
            {message.time}
          </span>
          {isMine && <Avatar label={currentUser.nickname} mine />}
        </div>

        {message.type === "sign-to-text" && (
          <div className="rounded-[30px] border border-sky-100 bg-white p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(15,23,42,0.12)]">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-sky-600">
                  수어 영상 → 텍스트
                </p>
                <h4 className="mt-2 text-base font-black text-slate-900">
                  AI 인식 결과
                </h4>
              </div>

              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-600">
                분석 완료
              </span>
            </div>

            <VideoMockSurface />

            <div className="mt-4 flex flex-wrap gap-2">
              {message.keywords?.map((keyword) => (
                <KeywordTag key={keyword} label={keyword} />
              ))}
            </div>

            <div className="mt-4 rounded-[24px] bg-sky-50 p-4">
              <p className="text-xs font-bold text-sky-700">문장 후보</p>
              <p className="mt-2 text-xl font-black text-slate-900">
                {message.text}
              </p>
            </div>

            {message.confidence && (
              <p className="mt-3 text-xs font-bold text-emerald-600">
                평균 신뢰도 {Math.round(message.confidence * 100)}%
              </p>
            )}
          </div>
        )}

        {message.type === "text-to-sign" && (
          <div className="rounded-[30px] border border-sky-100 bg-white p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(15,23,42,0.12)]">
            <div className="rounded-[24px] bg-[radial-gradient(circle_at_20%_0%,rgba(56,189,248,0.22),transparent_32%),linear-gradient(135deg,#071430,#0B1F4E)] p-5 text-white">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-sky-200">
                텍스트 → 수어 영상
              </p>
              <h4 className="mt-2 text-xl font-black">{message.text}</h4>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {message.keywords?.map((keyword) => (
                <KeywordTag key={keyword} label={keyword} />
              ))}
            </div>

            {message.signVideoSequence && message.signVideoSequence.length > 0 && (
              <div className="mt-5 rounded-[26px] border border-slate-200 bg-slate-50 p-4">
                <div className="mb-4 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-bold text-slate-900">
                      키워드 기반 수어 영상 시퀀스
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      키워드 순서 기반 프로토타입입니다.
                    </p>
                  </div>

                  <button
                    onClick={() =>
                      onOpenSequenceModal(
                        `${message.text} - 전체 재생`,
                        message.signVideoSequence ?? [],
                        "배경이 어두워진 모달에서 순서대로 영상을 확인합니다."
                      )
                    }
                    className="rounded-2xl bg-sky-500 px-4 py-2 text-sm font-bold text-white shadow-[0_12px_30px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 hover:shadow-xl active:translate-y-0"
                  >
                    전체 재생
                  </button>
                </div>

                <div className="space-y-3">
                  {message.signVideoSequence.map((video, videoIndex) => (
                    <VideoRow
                      key={`${video.keyword}-${videoIndex}`}
                      video={video}
                      index={videoIndex}
                      onPlay={() =>
                        onOpenSequenceModal(
                          `${video.title} 재생`,
                          [video],
                          "단일 수어 영상을 모달에서 재생합니다."
                        )
                      }
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {message.type === "memo" && (
          <div className="rounded-[30px] border border-slate-200 bg-white p-5 shadow-[0_20px_50px_rgba(15,23,42,0.08)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(15,23,42,0.12)]">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">
              필담
            </p>
            <p className="mt-3 text-2xl font-black text-slate-900">
              {message.text}
            </p>
            <button className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-slate-700 transition-all duration-200 hover:-translate-y-0.5 hover:bg-white hover:shadow-md active:translate-y-0">
              크게 보기
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function TranslatorView({
  currentUser,
  keywordInput,
  setKeywordInput,
  sentenceInput,
  setSentenceInput,
  previewKeywords,
  previewSequence,
  quickKeywords,
  onAppendKeyword,
  onGenerateFromKeywords,
  onGenerateFromSentence,
  onOpenSequenceModal,
}: {
  currentUser: CurrentUser;
  keywordInput: string;
  setKeywordInput: (value: string) => void;
  sentenceInput: string;
  setSentenceInput: (value: string) => void;
  previewKeywords: string[];
  previewSequence: SignVideoItem[];
  quickKeywords: string[];
  onAppendKeyword: (keyword: string) => void;
  onGenerateFromKeywords: () => void;
  onGenerateFromSentence: () => void;
  onOpenSequenceModal: (
    title: string,
    sequence: SignVideoItem[],
    description?: string
  ) => void;
}) {
  const isSignUser = currentUser.role === "signUser";

  return (
    <div className="grid h-full grid-cols-1 gap-5 overflow-y-auto xl:grid-cols-[1fr_1fr]">
      <Panel
        className={`animate-fade-up p-6 ${
          isSignUser ? "ring-4 ring-sky-100" : ""
        }`}
      >
        <div className="mb-5">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-600">
            수어 사용자 중심
          </p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">
            수어 영상 → 텍스트
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            카메라 앞에서 수어를 표현하면 AI가 핵심 키워드와 문장 후보를 제공합니다.
          </p>
        </div>

        <div className="rounded-[30px] border border-sky-100 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
          <VideoMockSurface large />

          <div className="mt-4 flex flex-wrap gap-2">
            <KeywordTag label="화장실 92%" />
            <KeywordTag label="어디 84%" />
          </div>

          <div className="mt-4 rounded-[24px] bg-sky-50 p-4">
            <p className="text-xs font-bold text-sky-700">문장 후보</p>
            <p className="mt-2 text-xl font-black text-slate-900">
              화장실 어디예요?
            </p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <ActionButton dark>수어 다시 촬영</ActionButton>
            <ActionButton>대화 저장</ActionButton>
          </div>
        </div>
      </Panel>

      <Panel
        className={`animate-fade-up overflow-y-auto p-6 ${
          !isSignUser ? "ring-4 ring-sky-100" : ""
        }`}
      >
        <div className="mb-5">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-500">
            비장애인 / 직원 중심
          </p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">
            텍스트 → 수어 영상
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            문장을 입력하면 핵심 키워드를 뽑고 대응되는 수어 영상을 순서대로 보여줍니다.
          </p>
        </div>

        <div className="space-y-5">
          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-700">
              1차 키워드 입력
            </span>
            <input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
              placeholder="예: 토요일, 약속, 미안하다"
            />
          </label>

          <div className="flex flex-wrap gap-2">
            {quickKeywords.map((keyword) => (
              <button
                key={keyword}
                onClick={() => onAppendKeyword(keyword)}
                className="rounded-full border border-sky-100 bg-sky-50 px-4 py-2 text-sm font-bold text-sky-700 transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-100 hover:shadow-md active:translate-y-0"
              >
                + {keyword}
              </button>
            ))}
          </div>

          <ActionButton onClick={onGenerateFromKeywords}>
            키워드 시퀀스 생성
          </ActionButton>

          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-700">
              2차 목표 문장 입력
            </span>
            <textarea
              value={sentenceInput}
              onChange={(e) => setSentenceInput(e.target.value)}
              rows={3}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
              placeholder="예: 토요일 약속인데 못 가서 미안하다"
            />
          </label>

          <ActionButton dark onClick={onGenerateFromSentence}>
            문장에서 키워드 추출
          </ActionButton>

          <div className="rounded-[26px] border border-slate-200 bg-slate-50 p-4">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-bold text-slate-900">미리보기</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {previewKeywords.map((keyword) => (
                    <KeywordTag key={keyword} label={keyword} />
                  ))}
                </div>
              </div>

              <button
                onClick={() =>
                  onOpenSequenceModal(
                    "미리보기 전체 재생",
                    previewSequence,
                    "선택된 키워드에 대응하는 수어 영상들을 순서대로 봅니다."
                  )
                }
                className="rounded-2xl bg-sky-500 px-4 py-2 text-sm font-bold text-white shadow-[0_12px_30px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 hover:shadow-xl active:translate-y-0"
              >
                전체 재생
              </button>
            </div>

            <div className="space-y-3">
              {previewSequence.map((video, index) => (
                <VideoRow
                  key={`${video.keyword}-${index}`}
                  video={video}
                  index={index}
                  onPlay={() =>
                    onOpenSequenceModal(
                      `${video.title} 재생`,
                      [video],
                      "단일 영상 재생입니다."
                    )
                  }
                />
              ))}
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}

function SettingsView({
  currentUser,
  onUpdateUser,
  onLogout,
}: {
  currentUser: CurrentUser;
  onUpdateUser: (user: CurrentUser) => void;
  onLogout: () => void;
}) {
  const [nickname, setNickname] = useState(currentUser.nickname);
  const [email, setEmail] = useState(currentUser.email);
  const [role, setRole] = useState<UserRole>(currentUser.role);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    const id = role === "signUser" ? "user-a" : "user-b";

    onUpdateUser({
      id,
      nickname: nickname.trim() || "데모 사용자",
      email: email.trim() || "demo@signbridge.kr",
      role,
    });

    setSaved(true);

    window.setTimeout(() => {
      setSaved(false);
    }, 1600);
  };

  return (
    <div className="grid h-full grid-cols-1 gap-5 overflow-y-auto xl:grid-cols-2">
      <Panel className="animate-fade-up p-6">
        <h3 className="text-2xl font-black text-slate-900">계정 정보</h3>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          역할을 바꾸면 데모 userId도 함께 바뀌어서 나/상대 기준이 달라집니다.
        </p>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-700">
              닉네임
            </span>
            <input
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-950 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-700">
              이메일
            </span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-950 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
            />
          </label>

          <div>
            <span className="mb-2 block text-sm font-bold text-slate-700">
              역할
            </span>
            <div className="grid grid-cols-2 gap-3">
              <RoleButton
                active={role === "signUser"}
                title="수어 사용자"
                desc="user-a 기준"
                onClick={() => setRole("signUser")}
              />
              <RoleButton
                active={role === "hearingUser"}
                title="비장애인 / 직원"
                desc="user-b 기준"
                onClick={() => setRole("hearingUser")}
              />
            </div>
          </div>

          <div className="rounded-[24px] bg-sky-50 p-4">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-700">
              현재 계정
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-sky-700 shadow-sm">
                {nickname || "닉네임 미입력"}
              </span>
              <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-sky-700 shadow-sm">
                {roleLabelMap[role]}
              </span>
              <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-sky-700 shadow-sm">
                {role === "signUser" ? "user-a" : "user-b"}
              </span>
            </div>
          </div>

          <button
            onClick={handleSave}
            className="w-full rounded-2xl bg-sky-500 px-5 py-3.5 text-sm font-bold text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 hover:shadow-xl active:translate-y-0"
          >
            {saved ? "저장 완료" : "변경사항 저장"}
          </button>

          <button
            onClick={onLogout}
            className="w-full rounded-2xl bg-slate-950 px-5 py-3.5 text-sm font-bold text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-xl active:translate-y-0"
          >
            로그아웃
          </button>
        </div>
      </Panel>

      <Panel className="animate-fade-up p-6">
        <h3 className="text-2xl font-black text-slate-900">장치 상태</h3>
        <div className="mt-6 space-y-4">
          <SettingRow label="카메라 연결" value="연결됨" active />
          <SettingRow label="LED 상태" value="대기" active />
          <SettingRow label="버튼 상태" value="대기" active />
          <SettingRow label="진동 알림" value="비활성" />
          <SettingRow label="부저 알림" value="비활성" />
        </div>

        <div className="mt-8">
          <h3 className="text-2xl font-black text-slate-900">구현 메모</h3>
          <div className="mt-5 space-y-4">
            <MemoText
              title="현재 구조"
              desc="같은 room-1을 보되, currentUser.id와 senderId를 비교해서 나/상대를 판단합니다."
            />
            <MemoText
              title="백엔드 연결"
              desc="DB에는 senderId만 저장하고, 프론트에서 currentUser 기준으로 정렬하면 됩니다."
            />
            <MemoText
              title="자동 반영"
              desc="웹소켓 없이도 2~3초마다 메시지 API를 polling하면 새 메시지를 화면에 추가할 수 있습니다."
            />
          </div>
        </div>
      </Panel>
    </div>
  );
}

function SequenceModal({
  modal,
  onClose,
}: {
  modal: SequenceModalState;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 px-4 py-8 backdrop-blur-md">
      <div className="animate-soft-scale flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-[32px] border border-white/10 bg-white shadow-[0_40px_120px_rgba(15,23,42,0.38)]">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-sky-600">
              전체 재생 모드
            </p>
            <h3 className="mt-1 text-2xl font-black text-slate-900">
              {modal.title}
            </h3>
            {modal.description && (
              <p className="mt-2 text-sm leading-6 text-slate-500">
                {modal.description}
              </p>
            )}
          </div>

          <button
            onClick={onClose}
            className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-200 active:translate-y-0"
          >
            닫기
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-6">
          {modal.sequence.length === 0 ? (
            <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-slate-500">
              표시할 수어 영상이 없습니다.
            </div>
          ) : (
            <div className="space-y-5">
              {modal.sequence.map((video, index) => (
                <div
                  key={`${video.keyword}-${index}`}
                  className="animate-fade-up rounded-[30px] border border-slate-200 bg-slate-50 p-5 shadow-sm"
                  style={{ animationDelay: `${index * 90}ms` }}
                >
                  <div className="mb-4 flex items-center gap-4">
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#0F172A_0%,#1D4ED8_100%)] text-lg font-black text-white shadow-[0_12px_30px_rgba(29,78,216,0.28)]">
                      {video.symbol}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-slate-900 px-2 text-xs font-black text-white">
                          {index + 1}
                        </span>
                        <h4 className="text-lg font-black text-slate-900">
                          {video.title}
                        </h4>
                      </div>
                      <p className="mt-1 text-sm text-slate-500">
                        키워드: {video.keyword}
                      </p>
                    </div>
                  </div>

                  {video.url ? (
                    <video
                      src={video.url}
                      controls
                      className="w-full rounded-2xl bg-slate-950 shadow-inner"
                    />
                  ) : (
                    <div className="flex h-64 items-center justify-center rounded-2xl bg-slate-950 text-white">
                      <div className="text-center">
                        <p className="text-4xl font-black">{video.symbol}</p>
                        <p className="mt-3 text-sm text-slate-300">
                          연결된 영상 파일이 없습니다.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 bg-slate-50 px-6 py-4 text-sm text-slate-500">
          한 화면에서 순서대로 영상을 확인하는 프로토타입입니다.
        </div>
      </div>
    </div>
  );
}

function VideoMockSurface({ large = false }: { large?: boolean }) {
  return (
    <div className="overflow-hidden rounded-[26px] bg-slate-950">
      <div
        className={`flex ${
          large ? "h-56" : "h-44"
        } items-center justify-center bg-[radial-gradient(circle_at_30%_20%,rgba(56,189,248,0.22),transparent_34%),linear-gradient(135deg,#020617,#0f2a5f)] text-white`}
      >
        <div className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 text-xl font-black ring-1 ring-white/15">
            수
          </div>
          <p className="mt-3 text-sm font-black">수어 입력 영상</p>
          <p className="mt-1 text-xs text-sky-100/60">camera mock</p>
        </div>
      </div>
    </div>
  );
}

function VideoRow({
  video,
  index,
  onPlay,
}: {
  video: SignVideoItem;
  index: number;
  onPlay: () => void;
}) {
  return (
    <div className="group flex items-center gap-4 rounded-[24px] border border-slate-200 bg-white px-4 py-3 transition-all duration-300 hover:-translate-y-0.5 hover:border-sky-200 hover:shadow-lg">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[linear-gradient(180deg,#0F172A_0%,#1D4ED8_100%)] text-2xl font-black text-white shadow-[0_12px_26px_rgba(29,78,216,0.28)] transition-transform duration-300 group-hover:scale-105">
        {video.symbol}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-slate-900 px-2 text-[11px] font-black text-white">
            {index + 1}
          </span>
          <p className="truncate text-lg font-black text-slate-900">
            {video.title}
          </p>
        </div>
        <p className="truncate text-sm text-slate-400">
          {video.url ?? "영상 파일 연결 전"}
        </p>
      </div>

      <button
        onClick={onPlay}
        className="rounded-full border border-sky-100 bg-sky-50 px-4 py-2 text-sm font-bold text-sky-700 transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-100 hover:shadow-md active:translate-y-0"
      >
        재생
      </button>
    </div>
  );
}

function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[30px] border border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.08)] ${className}`}
    >
      {children}
    </div>
  );
}

function SidebarButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex w-full items-center gap-4 rounded-[22px] px-4 py-4 text-left transition-all duration-300 hover:-translate-y-0.5 ${
        active
          ? "bg-white text-slate-900 shadow-[0_16px_40px_rgba(255,255,255,0.18)]"
          : "bg-white/[0.08] text-white/80 hover:bg-white/[0.12]"
      }`}
    >
      <div
        className={`flex h-11 w-11 items-center justify-center rounded-2xl text-base transition-transform duration-300 group-hover:scale-105 ${
          active ? "bg-sky-50 text-sky-600" : "bg-white/10 text-white"
        }`}
      >
        {icon}
      </div>
      <span className="text-lg font-black tracking-tight">{label}</span>
    </button>
  );
}

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "sky" | "amber" | "slate";
}) {
  const styles =
    tone === "sky"
      ? "bg-sky-50 text-sky-700 border-sky-100"
      : tone === "amber"
      ? "bg-amber-50 text-amber-700 border-amber-100"
      : "bg-white/90 text-slate-700 border-white/50";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3.5 py-1.5 text-xs font-bold ${styles}`}
    >
      {label}
    </span>
  );
}

function KeywordTag({ label }: { label: string }) {
  return (
    <span className="rounded-full bg-sky-50 px-3 py-1.5 text-sm font-bold text-sky-700 ring-1 ring-sky-100">
      {label}
    </span>
  );
}

function Avatar({ label, mine = false }: { label: string; mine?: boolean }) {
  return (
    <div
      className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-black text-white ${
        mine
          ? "bg-sky-500"
          : "bg-[linear-gradient(180deg,#0F172A_0%,#1D4ED8_100%)]"
      }`}
    >
      {label.slice(0, 1)}
    </div>
  );
}

function ActionButton({
  children,
  onClick,
  dark = false,
  light = false,
}: {
  children: ReactNode;
  onClick?: () => void;
  dark?: boolean;
  light?: boolean;
}) {
  const style = dark
    ? "bg-[linear-gradient(180deg,#0B1224_0%,#06133B_100%)] text-white shadow-[0_16px_38px_rgba(2,6,23,0.24)]"
    : light
    ? "border border-slate-200 bg-slate-50 text-slate-600"
    : "bg-sky-500 text-white shadow-[0_16px_38px_rgba(14,165,233,0.26)]";

  return (
    <button
      onClick={onClick}
      className={`rounded-2xl px-5 py-3.5 text-sm font-bold transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0 ${style}`}
    >
      {children}
    </button>
  );
}

function SettingRow({
  label,
  value,
  active = false,
}: {
  label: string;
  value: string;
  active?: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-[24px] border border-slate-200 bg-slate-50 px-5 py-4 transition-all duration-300 hover:-translate-y-0.5 hover:bg-white hover:shadow-md">
      <span className="text-sm font-bold text-slate-700">{label}</span>
      <span
        className={`rounded-full px-4 py-2 text-xs font-bold ${
          active
            ? "bg-emerald-50 text-emerald-600"
            : "bg-slate-200 text-slate-600"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function MemoText({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-5 transition-all duration-300 hover:-translate-y-0.5 hover:bg-white hover:shadow-md">
      <p className="text-sm font-black text-slate-900">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-500">{desc}</p>
    </div>
  );
}