"use client";

import { useState } from "react";

import {
  EmojiIdDisplay,
  EmojiPalette,
  MAX_ID_EMOJIS,
  MIN_ID_EMOJIS,
} from "@/components/EmojiKeypad";
import { ActionButton, Panel, SettingRow } from "@/components/ui";
import { updateDisplayName, updateNickname } from "@/lib/api/endpoints";
import { toUserMessage } from "@/lib/api/errors";
import { countGraphemes, removeLastGrapheme } from "@/lib/graphemes";
import { roleLabel } from "@/lib/types";
import type { User } from "@/lib/types";

export function SettingsView({
  currentUser,
  onUpdateUser,
  onLogout,
}: {
  currentUser: User;
  onUpdateUser: (user: User) => void;
  onLogout: () => void;
}) {
  const [nickname, setNickname] = useState(currentUser.nickname);
  const [displayName, setDisplayName] = useState(currentUser.display_name ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 아이디는 농인·청인 모두 이모지라 키보드로 고칠 수 없습니다 — 여기도 팔레트를 씁니다.
  const idCount = countGraphemes(nickname);

  const handleSave = async () => {
    if (idCount < MIN_ID_EMOJIS) {
      setError(`이모지를 ${MIN_ID_EMOJIS}개 이상 골라주세요.`);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // 바뀐 것만 저장합니다. 아이디(이모지)는 로그인 식별자라 굳이 매번 건드리지 않습니다.
      let updated = currentUser;

      if (nickname.trim() !== currentUser.nickname) {
        updated = await updateNickname(nickname.trim());
      }

      if (displayName.trim() !== (currentUser.display_name ?? "")) {
        updated = await updateDisplayName(displayName.trim());
      }

      onUpdateUser(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 1600);
    } catch (cause) {
      setError(toUserMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid h-full grid-cols-1 gap-5 overflow-y-auto xl:grid-cols-2">
      <Panel className="animate-fade-up p-6">
        <h3 className="text-2xl font-black text-slate-900">계정 정보</h3>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          역할은 서버 계정에 속해 있어 화면에서 바꾸지 않습니다. 다른 역할로 보려면
          로그아웃 후 해당 계정으로 로그인하세요.
        </p>

        <div className="mt-6 space-y-4">
          <div>
            <span className="mb-2 flex items-center justify-between text-sm font-bold text-slate-700">
              <span>내 아이디</span>
              <span className="text-xs font-semibold text-slate-400">
                {idCount} / {MAX_ID_EMOJIS}
              </span>
            </span>
            <EmojiIdDisplay value={nickname} />
            <div className="mt-3">
              <EmojiPalette
                onPick={(emoji) =>
                  setNickname((current) =>
                    countGraphemes(current) >= MAX_ID_EMOJIS ? current : current + emoji
                  )
                }
                onBackspace={() => setNickname((current) => removeLastGrapheme(current))}
                disabled={idCount >= MAX_ID_EMOJIS}
              />
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-400">
              아이디를 바꾸면 친구가 예전 아이디로는 나를 못 찾습니다.
            </p>
          </div>

          <div>
            <span className="mb-2 block text-sm font-bold text-slate-700">
              한글 이름{" "}
              <span className="font-semibold text-slate-400">(선택)</span>
            </span>
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              maxLength={20}
              placeholder="예: 김민지"
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-900 outline-none transition-all duration-200 focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
            />
            <p className="mt-2 text-xs leading-5 text-slate-400">
              이모지 아이디는 글로 읽기 어려우니, 한글 이름을 적어두면 채팅에 「🐶🍎⭐
              (민지)」처럼 함께 보입니다. 농인은 가족이 대신 적어줄 수도 있어요. 비워두면
              아이디만 보입니다.
            </p>
          </div>

          <div className="rounded-[24px] bg-sky-50 p-4">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-sky-700">
              현재 계정
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-sky-700 shadow-sm">
                {currentUser.nickname}
              </span>
              <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-sky-700 shadow-sm">
                {roleLabel[currentUser.role]}
              </span>
              <span className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-sky-700 shadow-sm">
                user #{currentUser.id}
              </span>
            </div>
          </div>

          {error && (
            <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-600">
              {error}
            </p>
          )}

          <div className="grid grid-cols-1 gap-3">
            <ActionButton onClick={handleSave} disabled={saving || !nickname.trim()}>
              {saved ? "✅ 저장 완료" : saving ? "저장 중…" : "변경사항 저장"}
            </ActionButton>

            <ActionButton dark onClick={onLogout}>
              로그아웃
            </ActionButton>
          </div>
        </div>
      </Panel>

      <Panel className="animate-fade-up p-6">
        <h3 className="text-2xl font-black text-slate-900">연결 상태</h3>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          촬영에 사용하는 장치의 연결 상태입니다.
        </p>

        <div className="mt-6 space-y-4">
          <SettingRow label="📷 카메라" value="사용 중" active />
          <SettingRow label="💡 LED" value="대기 중" active />
          <SettingRow label="🔘 촬영 버튼" value="대기 중" active />
          <SettingRow label="📳 진동 알림" value="켜짐" active />
        </div>
      </Panel>
    </div>
  );
}
