"use client";

// 자소 단위 계산은 lib/graphemes에 있습니다 (아바타 등 여기 말고도 씁니다).
export { countGraphemes, removeLastGrapheme } from "@/lib/graphemes";

// 농인용 입력 도구. 아이디는 이모지 조합, 비밀번호는 숫자 PIN입니다.
//
// 로그인 화면(= 로그인 전)에서도 써야 해서 팔레트를 서버에서 받아오지 않습니다.
// /quick-keywords/ 는 IsAuthenticated라 로그인 전에는 못 부릅니다.

// 아이디용 이모지. 수어 사전 이모지(🤝=약속)를 쓰지 않는 이유는, 그건 **뜻**이 있는
// 기호라서 아이디로 쓰면 "약속이라는 뜻인가?" 하고 헷갈리기 때문입니다.
// 아이디에 필요한 건 뜻이 아니라 **서로 확실히 구별되는 것**이라, 모양과 색이
// 뚜렷하게 다른 것들로 고릅니다.
export const ID_EMOJIS = [
  "🐶", "🐱", "🐰", "🦊", "🐻", "🐼",
  "🍎", "🍌", "🍇", "🍓", "🍒", "🍑",
  "⚽", "🎈", "🎁", "🎸", "🚗", "✈️",
  "⭐", "🌙", "☀️", "🌈", "❤️", "💎",
];

// 아이디에 넣을 수 있는 이모지 개수. 너무 짧으면 겹치고, 너무 길면 못 외웁니다.
export const MAX_ID_EMOJIS = 6;
export const MIN_ID_EMOJIS = 3;

// PIN 자릿수.
export const PIN_LENGTH = 4;

/** 고른 이모지를 크게 보여주는 칸. 비어 있으면 안내를 띄웁니다. */
export function EmojiIdDisplay({
  value,
  placeholder = "아래에서 이모지를 골라주세요",
}: {
  value: string;
  placeholder?: string;
}) {
  return (
    <div className="flex min-h-[72px] items-center justify-center rounded-2xl border-2 border-dashed border-sky-200 bg-sky-50/60 px-4 py-3">
      {value ? (
        <p className="break-all text-center text-4xl leading-tight tracking-widest">
          {value}
        </p>
      ) : (
        <p className="text-center text-sm font-bold text-slate-400">{placeholder}</p>
      )}
    </div>
  );
}

export function EmojiPalette({
  onPick,
  onBackspace,
  disabled = false,
}: {
  onPick: (emoji: string) => void;
  onBackspace: () => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <div className="grid grid-cols-6 gap-2">
        {ID_EMOJIS.map((emoji) => (
          <button
            key={emoji}
            type="button"
            disabled={disabled}
            onClick={() => onPick(emoji)}
            className="flex aspect-square items-center justify-center rounded-2xl border border-slate-200 bg-white text-2xl transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-300 hover:bg-sky-50 hover:shadow-md active:translate-y-0 disabled:opacity-40 disabled:hover:translate-y-0"
          >
            {emoji}
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={onBackspace}
        className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-black text-slate-600 transition-all duration-200 hover:bg-slate-100 active:translate-y-0.5"
      >
        ⌫ 지우기
      </button>
    </div>
  );
}

export function NumberPad({
  onPick,
  onBackspace,
  disabled = false,
}: {
  onPick: (digit: string) => void;
  onBackspace: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((digit) => (
        <button
          key={digit}
          type="button"
          disabled={disabled}
          onClick={() => onPick(digit)}
          className="rounded-2xl border border-slate-200 bg-white py-3.5 text-xl font-black text-slate-900 transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-300 hover:bg-sky-50 hover:shadow-md active:translate-y-0 disabled:opacity-40"
        >
          {digit}
        </button>
      ))}

      <div />

      <button
        type="button"
        disabled={disabled}
        onClick={() => onPick("0")}
        className="rounded-2xl border border-slate-200 bg-white py-3.5 text-xl font-black text-slate-900 transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-300 hover:bg-sky-50 hover:shadow-md active:translate-y-0 disabled:opacity-40"
      >
        0
      </button>

      <button
        type="button"
        onClick={onBackspace}
        className="rounded-2xl border border-slate-200 bg-slate-50 py-3.5 text-lg font-black text-slate-600 transition-all duration-200 hover:bg-slate-100 active:translate-y-0.5"
      >
        ⌫
      </button>
    </div>
  );
}

/** PIN을 ●●●○ 로 보여줍니다. 숫자를 그대로 노출하지 않습니다. */
export function PinDisplay({ length }: { length: number }) {
  return (
    <div className="flex justify-center gap-3 rounded-2xl border-2 border-dashed border-sky-200 bg-sky-50/60 py-4">
      {Array.from({ length: PIN_LENGTH }).map((_, index) => (
        <span
          key={index}
          className={`h-4 w-4 rounded-full transition-all duration-200 ${
            index < length ? "scale-110 bg-sky-500" : "bg-slate-300"
          }`}
        />
      ))}
    </div>
  );
}
