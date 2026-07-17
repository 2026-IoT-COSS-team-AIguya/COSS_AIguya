"use client";

import { useState } from "react";

import { login } from "@/lib/api/endpoints";
import { toUserMessage } from "@/lib/api/errors";
import type { User } from "@/lib/types";

export function LoginScreen({ onLogin }: { onLogin: (user: User) => void }) {
  const [nickname, setNickname] = useState("민지");
  const [password, setPassword] = useState("password");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
              손으로 말하고,
              <br />
              마음을 잇다
            </h1>

            <p className="mt-6 max-w-xl text-base leading-8 text-sky-50/70">
              농인은 🤟 수어로, 상대는 ⌨️ 텍스트로 입력합니다.
              <br />
              같은 대화방이지만 로그인 계정에 따라 내 화면이 달라집니다.
            </p>

            <div className="mt-10 grid max-w-xl grid-cols-4 gap-3">
              {[
                ["👫", "친구"],
                ["🧭", "길찾기"],
                ["🏥", "병원"],
                ["🏦", "은행"],
              ].map(([emoji, title], index) => (
                <div
                  key={title}
                  className="animate-fade-up rounded-3xl border border-white/10 bg-white/10 p-4 backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:bg-white/[0.14]"
                  style={{ animationDelay: `${index * 90}ms` }}
                >
                  <div className="text-3xl">{emoji}</div>
                  <div className="mt-2 text-base font-black text-white">{title}</div>
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
                disabled={loading}
                onClick={() => handleLogin("민지", "password")}
                className="rounded-[24px] border border-sky-300 bg-sky-50 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-50"
              >
                <div className="text-2xl">🤟</div>
                <div className="mt-2 text-sm font-black text-slate-950">
                  민지로 시작
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-400">
                  농인 · 수어
                </div>
              </button>

              <button
                type="button"
                disabled={loading}
                onClick={() => handleLogin("채진", "password")}
                className="rounded-[24px] border border-indigo-200 bg-indigo-50 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-50"
              >
                <div className="text-2xl">⌨️</div>
                <div className="mt-2 text-sm font-black text-slate-950">
                  채진으로 시작
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-400">
                  비장애인 · 텍스트
                </div>
              </button>
            </div>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-slate-200" />
              <span className="text-xs font-bold text-slate-400">직접 입력</span>
              <div className="h-px flex-1 bg-slate-200" />
            </div>

            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                handleLogin(nickname, password);
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

              {error && (
                <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-600">
                  {error}
                </p>
              )}

              <button
                disabled={loading}
                className="w-full rounded-2xl bg-sky-500 px-5 py-3.5 text-sm font-black text-white shadow-[0_16px_38px_rgba(14,165,233,0.28)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-sky-600 hover:shadow-xl active:translate-y-0 disabled:opacity-50"
              >
                {loading ? "로그인 중…" : "로그인"}
              </button>
            </form>

            <div className="mt-6 rounded-[24px] bg-sky-50 p-4">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-700">
                시연 방법
              </p>
              <p className="mt-2 text-xs leading-5 text-sky-700">
                일반 창은 민지(농인), 시크릿 창은 채진(비장애인)으로 로그인하면 같은
                방에서 메시지가 오가는 걸 확인할 수 있습니다. 비밀번호는 둘 다
                password 입니다.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
