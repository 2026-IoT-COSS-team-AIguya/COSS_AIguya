"use client";

import type { ReactNode } from "react";

export function Panel({
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

export function SidebarButton({
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
        className={`flex h-11 w-11 items-center justify-center rounded-2xl text-xl transition-transform duration-300 group-hover:scale-105 ${
          active ? "bg-sky-50" : "bg-white/10"
        }`}
      >
        {icon}
      </div>
      <span className="text-lg font-black tracking-tight">{label}</span>
    </button>
  );
}

export function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "sky" | "amber" | "slate" | "emerald";
}) {
  const styles =
    tone === "sky"
      ? "bg-sky-50 text-sky-700 border-sky-100"
      : tone === "amber"
        ? "bg-amber-50 text-amber-700 border-amber-100"
        : tone === "emerald"
          ? "bg-emerald-50 text-emerald-700 border-emerald-100"
          : "bg-white/90 text-slate-700 border-white/50";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3.5 py-1.5 text-xs font-bold ${styles}`}
    >
      {label}
    </span>
  );
}

export function KeywordTag({
  keyword,
  emoji,
  title,
  big = false,
}: {
  keyword: string;
  emoji: string;
  title?: string;
  big?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full bg-sky-50 font-bold text-sky-700 ring-1 ring-sky-100 ${
        big ? "px-3.5 py-2 text-base" : "px-3 py-1.5 text-sm"
      }`}
    >
      <span className={big ? "text-xl leading-none" : "text-base leading-none"}>
        {emoji}
      </span>
      {title ?? keyword}
    </span>
  );
}

export function Avatar({ label, mine = false }: { label: string; mine?: boolean }) {
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-black text-white ${
        mine ? "bg-sky-500" : "bg-[linear-gradient(180deg,#0F172A_0%,#1D4ED8_100%)]"
      }`}
    >
      {label.slice(0, 1)}
    </div>
  );
}

export function ActionButton({
  children,
  onClick,
  dark = false,
  light = false,
  disabled = false,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  dark?: boolean;
  light?: boolean;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const style = dark
    ? "bg-[linear-gradient(180deg,#0B1224_0%,#06133B_100%)] text-white shadow-[0_16px_38px_rgba(2,6,23,0.24)]"
    : light
      ? "border border-slate-200 bg-slate-50 text-slate-600"
      : "bg-sky-500 text-white shadow-[0_16px_38px_rgba(14,165,233,0.26)]";

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-2xl px-5 py-3.5 text-sm font-bold transition-all duration-200 enabled:hover:-translate-y-0.5 enabled:hover:shadow-xl enabled:active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-40 ${style}`}
    >
      {children}
    </button>
  );
}

export function RoleButton({
  active,
  emoji,
  title,
  desc,
  onClick,
}: {
  active: boolean;
  emoji: string;
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
      <div className="text-xl">{emoji}</div>
      <div className="mt-1.5 text-sm font-black text-slate-950">{title}</div>
      <div className="mt-1 text-xs font-semibold text-slate-400">{desc}</div>
    </button>
  );
}

export function SettingRow({
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
          active ? "bg-emerald-50 text-emerald-600" : "bg-slate-200 text-slate-600"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

export function MemoText({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-5 transition-all duration-300 hover:-translate-y-0.5 hover:bg-white hover:shadow-md">
      <p className="text-sm font-black text-slate-900">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-500">{desc}</p>
    </div>
  );
}

export function MotionStyles() {
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
