"use client";

import { useState } from "react";

import {
  EmojiIdDisplay,
  EmojiPalette,
  MAX_ID_EMOJIS,
  MIN_ID_EMOJIS,
  NumberPad,
  PIN_LENGTH,
  PinDisplay,
  countGraphemes,
  removeLastGrapheme,
} from "@/components/EmojiKeypad";
import { login, signup } from "@/lib/api/endpoints";
import { toUserMessage } from "@/lib/api/errors";
import type { User, UserRole } from "@/lib/types";

type Mode = "login" | "signup";

export function LoginScreen({ onLogin }: { onLogin: (user: User) => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("SIGN_USER");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // 아이디는 농인·청인 모두 이모지입니다. 아이디는 "남이 입력하는 것"이라
  // 한쪽만 쉬워서는 소용이 없습니다 — 농인이 청인 친구를 추가하려면 결국
  // 청인의 글자 아이디를 쳐야 하니까요.
  //
  // 비밀번호는 남이 입력하지 않으므로 형식이 갈려도 됩니다: 농인은 숫자 PIN,
  // 청인은 글자. 다만 로그인 시점엔 어느 쪽인지 알 수 없어서(아이디를 받기 전),
  // 입력창과 숫자판을 둘 다 띄우고 사용자가 편한 쪽을 쓰게 합니다.
  const pinOnly = mode === "signup" && role === "SIGN_USER";

  const idCount = countGraphemes(nickname);

  const handleLogin = async (id: string, pw: string) => {
    setLoading(true);
    setError(null);

    try {
      const result = await login(id, pw);
      onLogin(result.user);
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async () => {
    const id = nickname.trim();

    if (!id || !password) {
      return;
    }

    if (idCount < MIN_ID_EMOJIS) {
      setError(`이모지를 ${MIN_ID_EMOJIS}개 이상 골라주세요.`);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await signup(id, password, role);
      onLogin(result.user);
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setLoading(false);
    }
  };

  const submit = () => {
    if (mode === "login") {
      handleLogin(nickname, password);
    } else {
      handleSignup();
    }
  };

  // 입력 방식을 바꾸면 이전 방식으로 넣던 값은 지웁니다 — 이모지와 글자가 섞이면
  // 사용자가 자기 아이디를 못 알아봅니다.
  const reset = () => {
    setNickname("");
    setPassword("");
    setError(null);
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    reset();
  };

  const switchRole = (next: UserRole) => {
    setRole(next);
    reset();
  };

  const pickEmoji = (emoji: string) => {
    if (idCount >= MAX_ID_EMOJIS) {
      return;
    }
    setNickname((current) => current + emoji);
  };

  const pickDigit = (digit: string) => {
    if (password.length >= PIN_LENGTH) {
      return;
    }
    setPassword((current) => current + digit);
  };

  const canSubmit =
    nickname.trim().length > 0 &&
    password.length > 0 &&
    !loading &&
    (!pinOnly || password.length === PIN_LENGTH);

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#07111f] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_18%,rgba(56,189,248,0.24),transparent_30%),radial-gradient(circle_at_82%_12%,rgba(37,99,235,0.22),transparent_28%),linear-gradient(135deg,#07111f_0%,#0b1f4e_48%,#0f2a5f_100%)]" />
      <div className="pointer-events-none absolute left-[12%] top-[18%] h-72 w-72 rounded-full bg-sky-400/20 blur-3xl animate-float-glow" />
      <div className="pointer-events-none absolute bottom-[12%] right-[12%] h-80 w-80 rounded-full bg-blue-500/20 blur-3xl animate-float-glow" />

      <div className="relative z-10 grid min-h-screen grid-cols-1 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="flex items-center px-8 py-10 lg:px-16">
          <div className="max-w-2xl animate-fade-up">
            <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-3xl bg-white text-2xl font-black text-slate-950 shadow-[0_24px_70px_rgba(0,0,0,0.32)]">
              잇
            </div>

            <p className="text-sm font-bold uppercase tracking-[0.22em] text-sky-200">
              Itson
            </p>

            <h1 className="mt-5 text-5xl font-black leading-tight tracking-[-0.05em] lg:text-6xl">
              손으로 말하고,
              <br />
              마음을 잇다
            </h1>

            <p className="mt-6 max-w-xl text-base leading-8 text-sky-50/70">
              농인은 🤟 수어로, 상대는 ⌨️ 텍스트로 입력합니다.
              <br />
              같은 대화방이지만 로그인 계정에 따라 내 화면이 달라집니다.
            </p>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-10">
          <div className="max-h-[92vh] w-full max-w-md animate-soft-scale overflow-y-auto rounded-[34px] border border-white/15 bg-white/95 p-6 text-slate-950 shadow-[0_40px_120px_rgba(0,0,0,0.34)] backdrop-blur-xl">
            {/* 로그인 / 회원가입 전환 */}
            <div className="mb-6 grid grid-cols-2 gap-1 rounded-2xl bg-slate-100 p-1">
              {(["login", "signup"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => switchMode(item)}
                  className={`rounded-xl px-4 py-2.5 text-sm font-black transition-all duration-200 ${
                    mode === item
                      ? "bg-white text-slate-950 shadow-sm"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {item === "login" ? "로그인" : "회원가입"}
                </button>
              ))}
            </div>

            <div className="mb-5">
              <h2 className="text-3xl font-black tracking-tight">
                {mode === "login" ? "잇손 시작하기" : "계정 만들기"}
              </h2>
            </div>

            {/* 회원가입: 역할을 먼저 고릅니다 — 이걸로 입력 방식이 갈립니다. */}
            {mode === "signup" && (
              <div className="mb-5">
                <span className="mb-2 block text-sm font-bold text-slate-700">
                  나는 어느 쪽인가요?
                </span>
                <div className="grid grid-cols-2 gap-3">
                  {(
                    [
                      ["SIGN_USER", "🤟", "농인", "이모지 아이디"],
                      ["HEARING_USER", "⌨️", "비장애인", "글자 비밀번호"],
                    ] as const
                  ).map(([value, emoji, title, hint]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => switchRole(value)}
                      className={`rounded-[24px] border p-4 text-left transition-all duration-300 hover:-translate-y-0.5 ${
                        role === value
                          ? "border-sky-400 bg-sky-50 shadow-[0_12px_30px_rgba(56,189,248,0.2)]"
                          : "border-slate-200 bg-slate-50 hover:border-sky-200"
                      }`}
                    >
                      <div className="text-2xl">{emoji}</div>
                      <div className="mt-2 text-sm font-black text-slate-950">
                        {title}
                      </div>
                      <div className="mt-1 text-xs font-semibold text-slate-400">
                        {hint}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <form
              className="space-y-5"
              onSubmit={(event) => {
                event.preventDefault();
                submit();
              }}
            >
              {/* 아이디 — 농인·청인 모두 이모지 */}
              <div>
                <span className="mb-2 flex items-center justify-between text-sm font-bold text-slate-700">
                  <span>내 아이디</span>
                  <span className="text-xs font-semibold text-slate-400">
                    {idCount} / {MAX_ID_EMOJIS}
                  </span>
                </span>
                <EmojiIdDisplay
                  value={nickname}
                  placeholder={
                    mode === "signup"
                      ? "아래에서 이모지를 골라주세요"
                      : "내 이모지 아이디를 골라주세요"
                  }
                />
                <div className="mt-3">
                  <EmojiPalette
                    onPick={pickEmoji}
                    onBackspace={() =>
                      setNickname((current) => removeLastGrapheme(current))
                    }
                    disabled={idCount >= MAX_ID_EMOJIS}
                  />
                </div>
              </div>

              {/* 비밀번호 — 농인은 숫자 PIN, 청인은 글자 */}
              {pinOnly ? (
                <div>
                  <span className="mb-2 block text-sm font-bold text-slate-700">
                    비밀번호 (숫자 {PIN_LENGTH}자리)
                  </span>
                  <PinDisplay length={password.length} />
                  <div className="mt-3">
                    <NumberPad
                      onPick={pickDigit}
                      onBackspace={() => setPassword((c) => c.slice(0, -1))}
                      disabled={password.length >= PIN_LENGTH}
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block">
                    <span className="mb-2 block text-sm font-bold text-slate-700">
                      {mode === "signup" ? "글자 비밀번호" : "비밀번호"}
                    </span>
                    <input
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-center text-lg font-black tracking-[0.3em] text-slate-950 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                      placeholder={mode === "signup" ? "4자 이상" : "••••"}
                    />
                  </label>

                  {/* 로그인에서는 상대가 농인인지 알 수 없어 숫자판도 같이 둡니다.
                      청인은 위에 타자로, 농인은 아래 숫자판으로 — 고를 게 없습니다. */}
                  {mode === "login" && (
                    <div className="mt-3">
                      <p className="mb-2 text-xs font-semibold text-slate-400">
                        🔢 숫자 비밀번호는 여기서 누르세요
                      </p>
                      <NumberPad
                        onPick={(digit) => setPassword((current) => current + digit)}
                        onBackspace={() => setPassword((c) => c.slice(0, -1))}
                      />
                    </div>
                  )}
                </div>
              )}

              {error && (
                <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-600">
                  {error}
                </p>
              )}

              <button
                disabled={!canSubmit}
                className="w-full rounded-2xl bg-sky-500 px-5 py-3.5 text-sm font-black text-white shadow-[0_16px_38px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 hover:shadow-xl active:translate-y-0 disabled:opacity-50"
              >
                {loading
                  ? mode === "login"
                    ? "로그인 중…"
                    : "계정 만드는 중…"
                  : mode === "login"
                    ? "로그인"
                    : "가입하고 시작하기"}
              </button>
            </form>

            {mode === "login" && (
              <>
                <div className="my-6 flex items-center gap-3">
                  <div className="h-px flex-1 bg-slate-200" />
                  <span className="text-xs font-bold text-slate-400">빠른 시작</span>
                  <div className="h-px flex-1 bg-slate-200" />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => handleLogin("🐶🍎⭐", "1234")}
                    className="rounded-[24px] border border-sky-300 bg-sky-50 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-50"
                  >
                    <div className="text-2xl">🐶🍎⭐</div>
                    <div className="mt-2 text-sm font-black text-slate-950">
                      🤟 농인으로 시작
                    </div>
                    <div className="mt-1 text-xs font-semibold text-slate-400">
                      수어 · PIN 1234
                    </div>
                  </button>

                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => handleLogin("🦊🎈🌈", "password")}
                    className="rounded-[24px] border border-indigo-200 bg-indigo-50 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-50"
                  >
                    <div className="text-2xl">🦊🎈🌈</div>
                    <div className="mt-2 text-sm font-black text-slate-950">
                      ⌨️ 비장애인으로 시작
                    </div>
                    <div className="mt-1 text-xs font-semibold text-slate-400">
                      텍스트 · password
                    </div>
                  </button>
                </div>
              </>
            )}

            {mode === "signup" && (
              <div className="mt-6 rounded-[24px] bg-sky-50 p-4">
                <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-700">
                  아이디 만들기
                </p>
                <p className="mt-2 text-xs leading-5 text-sky-700">
                  {`이모지를 ${MIN_ID_EMOJIS}~${MAX_ID_EMOJIS}개 골라 아이디를 만듭니다. 고른 순서가 아이디가 되니, 친구에게 알려줄 때도 이 순서 그대로 알려주세요.`}
                </p>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
