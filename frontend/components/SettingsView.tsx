"use client";

import { useState } from "react";

import {
  EmojiIdDisplay,
  EmojiPalette,
  MAX_ID_EMOJIS,
  MIN_ID_EMOJIS,
} from "@/components/EmojiKeypad";
import { ActionButton, MemoText, Panel, SettingRow } from "@/components/ui";
import { updateNickname } from "@/lib/api/endpoints";
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
      const updated = await updateNickname(nickname.trim());
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
        <h3 className="text-2xl font-black text-slate-900">장치 상태</h3>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          아직 표시용입니다. Mobius/tinyIoT 센서 연동 후 실제 값이 들어옵니다.
        </p>

        <div className="mt-6 space-y-4">
          <SettingRow label="📷 카메라" value="브라우저 카메라 사용 중" active />
          <SettingRow label="💡 LED 상태" value="연동 전" />
          <SettingRow label="🔘 버튼 상태" value="연동 전" />
          <SettingRow label="📳 진동 알림" value="연동 전" />
        </div>

        <div className="mt-8">
          <h3 className="text-2xl font-black text-slate-900">구현 현황</h3>
          <div className="mt-5 space-y-4">
            <MemoText
              title="실제로 동작하는 것"
              desc="Django 프-백과 실제 HTTP로 통신합니다. 계정·친구·대화·촬영 업로드(202) → 상태 폴링(PENDING→PROCESSING→COMPLETED) → 메시지 폴링(after_id)까지 전 구간이 진짜입니다."
            />
            <MemoText
              title="문장 → 수어 (진짜 AI)"
              desc="번역기·채팅에서 문장을 입력하면 Gemini가 수어 사전 안의 키워드로 분해합니다. 실제 API 호출입니다."
            />
            <MemoText
              title="아직 가짜인 것"
              desc="수어 영상 → 텍스트 인식. 모델(키포인트 기반)이 학습 중이라 백엔드 recognitions/ai_client.py가 고정 예시를 순서대로 돌려줍니다. 업로드·상태 전이·저장은 진짜입니다. 시연에서 반드시 밝혀야 합니다."
            />
            <MemoText
              title="수어 영상"
              desc="46개 키워드 중 3개(약속/토요일/미안)만 예시 파일이 있습니다. 나머지는 이모지 카드로 대체되며, AI 개발 완료 후 AI DB에서 공급될 예정입니다."
            />
          </div>
        </div>
      </Panel>
    </div>
  );
}
