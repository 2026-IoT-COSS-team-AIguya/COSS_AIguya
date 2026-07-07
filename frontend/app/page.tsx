"use client";

import { useState } from "react";

type ViewMode = "chat" | "translator";
type TranslatorMode = "signToText" | "textToSignVideo";

type SignVideoClip = {
  order: number;
  keyword: string;
  videoTitle: string;
  videoUrl: string;
  description: string;
};

type ChatMessage =
  | {
      messageId: number;
      senderName: string;
      senderType: "deaf";
      messageType: "sign_to_text";
      originalVideoLabel: string;
      keywords: string[];
      translatedText: string;
      confidence: number;
      createdAt: string;
      isMe: boolean;
    }
  | {
      messageId: number;
      senderName: string;
      senderType: "hearing";
      messageType: "text_to_sign_video";
      inputText: string;
      keywords: string[];
      signVideoSequence: SignVideoClip[];
      notice: string;
      createdAt: string;
      isMe: boolean;
    }
  | {
      messageId: number;
      senderName: string;
      senderType: "system";
      messageType: "text";
      text: string;
      createdAt: string;
      isMe: boolean;
    };

const chatRooms = [
  {
    roomId: 1,
    name: "민지",
    description: "수어 영상 시퀀스로 대화 중",
    lastMessage: "내일 / 밥 / 먹다 / 가능?",
    unreadCount: 2,
  },
  {
    roomId: 2,
    name: "학교 행정실",
    description: "공공창구 확장 예시",
    lastMessage: "서류 접수 안내",
    unreadCount: 0,
  },
  {
    roomId: 3,
    name: "가족방",
    description: "가족과 쉬운 표현으로 대화",
    lastMessage: "오늘 약속 있어요.",
    unreadCount: 1,
  },
];

const mockMessages: ChatMessage[] = [
  {
    messageId: 1,
    senderName: "민지",
    senderType: "deaf",
    messageType: "sign_to_text",
    originalVideoLabel: "수어 영상 00:03",
    keywords: ["오늘", "약속"],
    translatedText: "오늘 약속 있어요.",
    confidence: 0.88,
    createdAt: "14:31",
    isMe: false,
  },
  {
    messageId: 2,
    senderName: "나",
    senderType: "hearing",
    messageType: "text_to_sign_video",
    inputText: "그럼 내일 밥 먹을래?",
    keywords: ["내일", "밥", "먹다", "가능?"],
    signVideoSequence: [
      {
        order: 1,
        keyword: "내일",
        videoTitle: "내일.mp4",
        videoUrl: "/videos/tomorrow.mp4",
        description: "내일을 의미하는 수어 영상 클립",
      },
      {
        order: 2,
        keyword: "밥",
        videoTitle: "meal.mp4",
        videoUrl: "/videos/meal.mp4",
        description: "밥 또는 식사를 의미하는 수어 영상 클립",
      },
      {
        order: 3,
        keyword: "먹다",
        videoTitle: "eat.mp4",
        videoUrl: "/videos/eat.mp4",
        description: "먹는 동작을 표현하는 수어 영상 클립",
      },
      {
        order: 4,
        keyword: "가능?",
        videoTitle: "possible-question.mp4",
        videoUrl: "/videos/possible-question.mp4",
        description: "가능 여부를 묻는 수어 영상 클립",
      },
    ],
    notice:
      "자연스러운 수어 문장 자동 생성이 아니라, 키워드에 대응되는 수어 영상 클립을 순서대로 보여주는 방식입니다.",
    createdAt: "14:33",
    isMe: true,
  },
  {
    messageId: 3,
    senderName: "민지",
    senderType: "system",
    messageType: "text",
    text: "좋아! 시간은 몇 시가 좋아?",
    createdAt: "14:35",
    isMe: false,
  },
];

const signToTextResult = {
  keywords: [
    { keyword: "화장실", confidence: 0.92 },
    { keyword: "어디", confidence: 0.84 },
    { keyword: "도움", confidence: 0.67 },
  ],
  sentenceCandidates: [
    "화장실 위치를 묻고 있는 상황일 수 있습니다.",
    "길 안내가 필요한 상황일 수 있습니다.",
    "도움이 필요한 상황일 수 있습니다.",
  ],
};

const textToSignVideoResult = {
  inputText: "저쪽 왼쪽에 있어.",
  keywords: ["저쪽", "왼쪽", "있다"],
  signVideoSequence: [
    {
      order: 1,
      keyword: "저쪽",
      videoTitle: "there.mp4",
      videoUrl: "/videos/there.mp4",
      description: "저쪽 방향을 가리키는 수어 영상 클립",
    },
    {
      order: 2,
      keyword: "왼쪽",
      videoTitle: "left.mp4",
      videoUrl: "/videos/left.mp4",
      description: "왼쪽 방향을 나타내는 수어 영상 클립",
    },
    {
      order: 3,
      keyword: "있다",
      videoTitle: "exist.mp4",
      videoUrl: "/videos/exist.mp4",
      description: "위치나 존재를 표현하는 수어 영상 클립",
    },
  ],
  notice:
    "입력 문장을 완전한 수어 문장으로 번역하지 않고, 핵심 키워드에 맞는 수어 영상 클립을 순서대로 제공합니다.",
};

const apiList = [
  {
    method: "GET",
    url: "/api/chat-rooms/",
    desc: "채팅방 목록 조회",
  },
  {
    method: "GET",
    url: "/api/chat-rooms/:roomId/messages/",
    desc: "채팅 메시지 목록 조회",
  },
  {
    method: "POST",
    url: "/api/messages/sign/",
    desc: "수어 영상 메시지 업로드 및 키워드 분석",
  },
  {
    method: "POST",
    url: "/api/messages/text-to-sign-sequence/",
    desc: "텍스트 입력을 키워드 기반 수어 영상 시퀀스로 변환",
  },
  {
    method: "POST",
    url: "/api/translator/sign-to-text/",
    desc: "대면 모드 수어 영상 → 키워드/문장 후보",
  },
  {
    method: "POST",
    url: "/api/translator/text-to-sign-sequence/",
    desc: "대면 모드 텍스트 → 수어 영상 시퀀스",
  },
];

export default function Home() {
  const [viewMode, setViewMode] = useState<ViewMode>("chat");
  const [translatorMode, setTranslatorMode] =
    useState<TranslatorMode>("signToText");
  const [selectedRoomId, setSelectedRoomId] = useState(1);

  const selectedRoom = chatRooms.find((room) => room.roomId === selectedRoomId);

  return (
    <main className="min-h-screen bg-[#f7f1e8] text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 flex-col justify-between bg-[#171717] p-5 text-white lg:flex">
          <div>
            <div className="mb-10">
              <p className="text-sm text-emerald-300">SignBridge</p>
              <h1 className="mt-1 text-2xl font-bold">손말이음</h1>
              <p className="mt-2 text-xs leading-5 text-zinc-400">
                수어 영상과 텍스트를 키워드 단위로 이어주는 양방향 소통
                보조 웹서비스
              </p>
            </div>

            <nav className="space-y-2">
              <button
                onClick={() => setViewMode("chat")}
                className={`w-full rounded-2xl px-4 py-3 text-left text-sm font-semibold transition ${
                  viewMode === "chat"
                    ? "bg-white text-slate-900"
                    : "text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                💬 채팅 모드
              </button>

              <button
                onClick={() => setViewMode("translator")}
                className={`w-full rounded-2xl px-4 py-3 text-left text-sm font-semibold transition ${
                  viewMode === "translator"
                    ? "bg-white text-slate-900"
                    : "text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                🖐️ 대면 번역기
              </button>

              <button className="w-full rounded-2xl px-4 py-3 text-left text-sm font-semibold text-zinc-300 hover:bg-zinc-800">
                🎞️ 수어 영상 보관함
              </button>

              <button className="w-full rounded-2xl px-4 py-3 text-left text-sm font-semibold text-zinc-300 hover:bg-zinc-800">
                ⚙️ 설정
              </button>
            </nav>
          </div>

          <div className="rounded-2xl bg-zinc-900 p-4">
            <p className="text-xs text-zinc-400">현재 단계</p>
            <p className="mt-1 text-sm font-semibold">1차 기능 프로토타입</p>
          </div>
        </aside>

        <section className="flex flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-stone-200 bg-white/80 px-6 py-4 backdrop-blur">
            <div>
              <p className="text-xs font-semibold text-emerald-600">
                수어 키워드 기반 양방향 소통 보조 AIoT
              </p>
              <h2 className="text-xl font-bold">
                {viewMode === "chat" ? "채팅 모드" : "대면 번역기 모드"}
              </h2>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setViewMode("chat")}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  viewMode === "chat"
                    ? "bg-slate-900 text-white"
                    : "bg-white text-slate-700"
                }`}
              >
                채팅
              </button>
              <button
                onClick={() => setViewMode("translator")}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  viewMode === "translator"
                    ? "bg-slate-900 text-white"
                    : "bg-white text-slate-700"
                }`}
              >
                번역기
              </button>
            </div>
          </header>

          {viewMode === "chat" ? (
            <section className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[320px_1fr_360px]">
              <div className="border-r border-stone-200 bg-white p-5">
                <div className="mb-5 flex items-center justify-between">
                  <h3 className="text-2xl font-bold">Chats</h3>
                  <button className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white">
                    새 대화
                  </button>
                </div>

                <input
                  placeholder="대화방 검색"
                  className="mb-4 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm outline-none focus:border-emerald-400"
                />

                <div className="space-y-3">
                  {chatRooms.map((room) => (
                    <button
                      key={room.roomId}
                      onClick={() => setSelectedRoomId(room.roomId)}
                      className={`w-full rounded-3xl p-4 text-left transition ${
                        selectedRoomId === room.roomId
                          ? "bg-emerald-50 ring-2 ring-emerald-300"
                          : "bg-stone-50 hover:bg-stone-100"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-bold">{room.name}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {room.description}
                          </p>
                          <p className="mt-3 truncate text-sm text-slate-700">
                            {room.lastMessage}
                          </p>
                        </div>

                        {room.unreadCount > 0 && (
                          <span className="rounded-full bg-rose-500 px-2 py-1 text-xs font-bold text-white">
                            {room.unreadCount}
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex flex-col bg-[#f5f5f3]">
                <div className="flex items-center justify-between border-b border-stone-200 bg-white px-6 py-4">
                  <div>
                    <h3 className="font-bold">{selectedRoom?.name}</h3>
                    <p className="text-xs text-slate-500">
                      폴라로이드형 수어-텍스트 채팅
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button className="rounded-full bg-stone-100 px-4 py-2 text-sm font-semibold">
                      원본 영상 보기
                    </button>
                    <button
                      onClick={() => setViewMode("translator")}
                      className="rounded-full bg-emerald-500 px-4 py-2 text-sm font-semibold text-white"
                    >
                      대면 번역기 열기
                    </button>
                  </div>
                </div>

                <div className="flex-1 space-y-5 overflow-y-auto p-6">
                  {mockMessages.map((message) => (
                    <div
                      key={message.messageId}
                      className={`flex ${
                        message.isMe ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-xl rounded-3xl p-5 shadow-sm ${
                          message.isMe
                            ? "bg-emerald-500 text-white"
                            : "bg-white text-slate-900"
                        }`}
                      >
                        <div className="mb-3 flex items-center justify-between gap-6">
                          <p className="text-sm font-bold">
                            {message.senderName}
                          </p>
                          <p
                            className={`text-xs ${
                              message.isMe
                                ? "text-emerald-50"
                                : "text-slate-400"
                            }`}
                          >
                            {message.createdAt}
                          </p>
                        </div>

                        {message.messageType === "sign_to_text" && (
                          <div>
                            <div className="mb-4 rounded-2xl bg-slate-900 p-5 text-white">
                              <p className="text-xs text-slate-300">
                                {message.originalVideoLabel}
                              </p>
                              <p className="mt-3 text-lg font-bold">
                                📹 수어 영상 메시지
                              </p>
                            </div>

                            <p className="text-xs font-semibold opacity-80">
                              AI 인식 키워드
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {message.keywords.map((keyword) => (
                                <span
                                  key={keyword}
                                  className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-bold text-emerald-700"
                                >
                                  {keyword}
                                </span>
                              ))}
                            </div>

                            <p className="mt-4 text-lg font-bold">
                              {message.translatedText}
                            </p>
                            <p className="mt-1 text-xs opacity-70">
                              신뢰도 {Math.round(message.confidence * 100)}%
                            </p>

                            <div className="mt-4 flex flex-wrap gap-2">
                              <button className="rounded-full bg-slate-900 px-3 py-2 text-xs font-semibold text-white">
                                맞아요
                              </button>
                              <button className="rounded-full bg-stone-100 px-3 py-2 text-xs font-semibold text-slate-700">
                                다시 해석
                              </button>
                              <button className="rounded-full bg-stone-100 px-3 py-2 text-xs font-semibold text-slate-700">
                                필담으로 확인
                              </button>
                            </div>
                          </div>
                        )}

                        {message.messageType === "text_to_sign_video" && (
                          <div>
                            <p className="text-sm font-semibold opacity-80">
                              입력 문장
                            </p>
                            <p className="mt-1 text-lg font-bold">
                              {message.inputText}
                            </p>

                            <p className="mt-4 text-xs font-semibold opacity-80">
                              추출 키워드
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {message.keywords.map((keyword) => (
                                <span
                                  key={keyword}
                                  className="rounded-full bg-white/20 px-3 py-1 text-sm font-bold"
                                >
                                  {keyword}
                                </span>
                              ))}
                            </div>

                            <div className="mt-4 rounded-2xl bg-white/15 p-4">
                              <p className="text-sm font-bold">
                                키워드 기반 수어 영상 시퀀스
                              </p>
                              <p className="mt-1 text-xs opacity-80">
                                {message.notice}
                              </p>

                              <div className="mt-4 space-y-3">
                                {message.signVideoSequence.map((clip) => (
                                  <div
                                    key={clip.order}
                                    className="flex items-center gap-3 rounded-2xl bg-white/20 p-3"
                                  >
                                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white/30 text-sm font-bold">
                                      {clip.order}
                                    </div>
                                    <div className="flex-1">
                                      <p className="font-bold">
                                        {clip.keyword}
                                      </p>
                                      <p className="text-xs opacity-80">
                                        {clip.videoTitle}
                                      </p>
                                    </div>
                                    <button className="rounded-full bg-white/25 px-3 py-2 text-xs font-bold">
                                      보기
                                    </button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}

                        {message.messageType === "text" && (
                          <p className="text-lg">{message.text}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="border-t border-stone-200 bg-white p-4">
                  <div className="flex gap-2">
                    <button className="rounded-2xl bg-stone-100 px-4 py-3 text-sm font-semibold">
                      📹 수어로 보내기
                    </button>
                    <input
                      placeholder="메시지를 입력하세요"
                      className="flex-1 rounded-2xl border border-stone-200 px-4 py-3 text-sm outline-none focus:border-emerald-400"
                    />
                    <button className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white">
                      보내기
                    </button>
                  </div>
                </div>
              </div>

              <div className="hidden border-l border-stone-200 bg-white p-5 xl:block">
                <h3 className="text-lg font-bold">API / 데이터 확인</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  이 영역은 백엔드와 맞춰야 할 API를 1차로 확인하는 용도.
                </p>

                <div className="mt-5 space-y-3">
                  {apiList.map((api) => (
                    <div
                      key={api.url}
                      className="rounded-2xl border border-stone-200 p-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-slate-900 px-2 py-1 text-xs font-bold text-white">
                          {api.method}
                        </span>
                        <p className="text-xs font-semibold text-emerald-600">
                          {api.url}
                        </p>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{api.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          ) : (
            <section className="flex-1 p-6">
              <div className="mx-auto max-w-6xl">
                <div className="mb-6 rounded-3xl bg-white p-6 shadow-sm">
                  <p className="text-sm font-semibold text-emerald-600">
                    대면 번역기
                  </p>
                  <h3 className="mt-2 text-3xl font-bold">
                    한 화면에서 수어와 텍스트를 빠르게 이어줘요
                  </h3>
                  <p className="mt-3 max-w-2xl text-slate-500">
                    같이 있을 때 하나의 폰이나 웹 화면을 가운데 두고 쓰는
                    모드입니다. 완전 자동 번역이 아니라, 키워드 후보와 수어
                    영상 시퀀스를 통해 오해를 줄이는 구조입니다.
                  </p>
                </div>

                <div className="mb-6 flex gap-2">
                  <button
                    onClick={() => setTranslatorMode("signToText")}
                    className={`rounded-full px-5 py-3 text-sm font-bold ${
                      translatorMode === "signToText"
                        ? "bg-slate-900 text-white"
                        : "bg-white text-slate-700"
                    }`}
                  >
                    수어 → 텍스트
                  </button>
                  <button
                    onClick={() => setTranslatorMode("textToSignVideo")}
                    className={`rounded-full px-5 py-3 text-sm font-bold ${
                      translatorMode === "textToSignVideo"
                        ? "bg-slate-900 text-white"
                        : "bg-white text-slate-700"
                    }`}
                  >
                    텍스트 → 수어 영상
                  </button>
                </div>

                {translatorMode === "signToText" ? (
                  <div className="grid gap-6 lg:grid-cols-2">
                    <div className="rounded-3xl bg-white p-6 shadow-sm">
                      <h4 className="text-xl font-bold">수어 입력</h4>
                      <p className="mt-2 text-sm text-slate-500">
                        버튼을 누르면 카메라/영상 센서 입력이 시작되는 구조.
                      </p>

                      <div className="mt-5 flex h-80 items-center justify-center rounded-3xl bg-slate-900 text-white">
                        <div className="text-center">
                          <p className="text-5xl">📹</p>
                          <p className="mt-4 text-lg font-bold">
                            카메라 미리보기 영역
                          </p>
                          <p className="mt-2 text-sm text-slate-300">
                            실제 구현 시 웹캠 또는 업로드 영상 사용
                          </p>
                        </div>
                      </div>

                      <div className="mt-5 flex gap-2">
                        <button className="flex-1 rounded-2xl bg-emerald-500 px-4 py-3 font-bold text-white">
                          수어 촬영 시작
                        </button>
                        <button className="rounded-2xl bg-stone-100 px-4 py-3 font-bold">
                          다시 촬영
                        </button>
                      </div>
                    </div>

                    <div className="rounded-3xl bg-white p-6 shadow-sm">
                      <h4 className="text-xl font-bold">AI 분석 결과</h4>

                      <p className="mt-5 text-sm font-semibold text-slate-500">
                        인식 키워드 후보
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {signToTextResult.keywords.map((item) => (
                          <button
                            key={item.keyword}
                            className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-700"
                          >
                            {item.keyword} {Math.round(item.confidence * 100)}%
                          </button>
                        ))}
                      </div>

                      <p className="mt-6 text-sm font-semibold text-slate-500">
                        문장 후보
                      </p>
                      <div className="mt-3 space-y-3">
                        {signToTextResult.sentenceCandidates.map(
                          (sentence, index) => (
                            <button
                              key={sentence}
                              className="w-full rounded-2xl border border-stone-200 p-4 text-left font-semibold hover:border-emerald-400 hover:bg-emerald-50"
                            >
                              {index + 1}. {sentence}
                            </button>
                          )
                        )}
                      </div>

                      <div className="mt-6 grid grid-cols-2 gap-2">
                        <button className="rounded-2xl bg-slate-900 px-4 py-3 font-bold text-white">
                          상대에게 크게 보여주기
                        </button>
                        <button className="rounded-2xl bg-emerald-500 px-4 py-3 font-bold text-white">
                          채팅방에 보내기
                        </button>
                        <button className="rounded-2xl bg-stone-100 px-4 py-3 font-bold">
                          필담으로 전환
                        </button>
                        <button className="rounded-2xl bg-rose-100 px-4 py-3 font-bold text-rose-600">
                          긴급 도움
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="grid gap-6 lg:grid-cols-2">
                    <div className="rounded-3xl bg-white p-6 shadow-sm">
                      <h4 className="text-xl font-bold">텍스트 / 키워드 입력</h4>
                      <p className="mt-2 text-sm text-slate-500">
                        비장애인이 짧은 문장이나 키워드를 입력하면 핵심
                        키워드에 맞는 수어 영상 클립을 순서대로 조합합니다.
                      </p>

                      <textarea
                        defaultValue={textToSignVideoResult.inputText}
                        className="mt-5 h-52 w-full resize-none rounded-3xl border border-stone-200 p-5 text-xl font-semibold outline-none focus:border-emerald-400"
                      />

                      <button className="mt-4 w-full rounded-2xl bg-emerald-500 px-4 py-3 font-bold text-white">
                        수어 영상 시퀀스 만들기
                      </button>
                    </div>

                    <div className="rounded-3xl bg-white p-6 shadow-sm">
                      <h4 className="text-xl font-bold">수어 영상 시퀀스</h4>
                      <p className="mt-2 text-sm text-slate-500">
                        {textToSignVideoResult.notice}
                      </p>

                      <p className="mt-5 text-sm font-semibold text-slate-500">
                        추출 키워드
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {textToSignVideoResult.keywords.map((keyword) => (
                          <span
                            key={keyword}
                            className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-700"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>

                      <div className="mt-5 space-y-3">
                        {textToSignVideoResult.signVideoSequence.map((clip) => (
                          <div
                            key={clip.order}
                            className="flex items-center gap-4 rounded-3xl border border-stone-200 p-4"
                          >
                            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-lg font-bold text-white">
                              {clip.order}
                            </div>

                            <div className="flex-1">
                              <p className="text-lg font-bold">
                                {clip.keyword}
                              </p>
                              <p className="text-sm font-semibold text-emerald-600">
                                {clip.videoTitle}
                              </p>
                              <p className="mt-1 text-xs text-slate-500">
                                {clip.description}
                              </p>
                            </div>

                            <button className="rounded-full bg-stone-100 px-4 py-2 text-sm font-bold">
                              영상 보기
                            </button>
                          </div>
                        ))}
                      </div>

                      <div className="mt-6 grid grid-cols-2 gap-2">
                        <button className="rounded-2xl bg-slate-900 px-4 py-3 font-bold text-white">
                          이어보기 화면 열기
                        </button>
                        <button className="rounded-2xl bg-emerald-500 px-4 py-3 font-bold text-white">
                          채팅방에 보내기
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}
        </section>
      </div>
    </main>
  );
}