"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { createSignTranslation } from "@/lib/api/endpoints";
import { toUserMessage } from "@/lib/api/errors";

// 명세 7.1: 권장 최대 길이 30초. 넘으면 알아서 멈춥니다.
const MAX_SECONDS = 30;

// 명세 7.1은 video/mp4 · video/webm을 받습니다. 브라우저 MediaRecorder는 webm을
// 내주므로 webm으로 찍습니다. 코덱이 붙은 "video/webm;codecs=vp9" 형태로 나오는데,
// 백엔드 serializer가 앞부분만 보고 판단하므로 그대로 보내도 됩니다.
const MIME_CANDIDATES = [
  "video/webm;codecs=vp9",
  "video/webm;codecs=vp8",
  "video/webm",
];

function pickMimeType() {
  if (typeof MediaRecorder === "undefined") {
    return null;
  }

  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) ?? null;
}

// "failed"가 따로 있는 이유: 카메라를 못 열었을 때 idle로 돌아가면 모달이 닫히고,
// 모달 안에 있던 오류 메시지도 같이 사라집니다 — 버튼을 눌렀는데 아무 일도 안
// 일어난 것처럼 보입니다. 실패해도 창은 열어둬야 이유를 읽고 다시 시도할 수 있습니다.
type Phase = "idle" | "opening" | "ready" | "recording" | "uploading" | "failed";

/**
 * 브라우저 카메라로 수어를 찍어 올립니다.
 *
 * 원래 설계는 아두이노 물리 버튼이 촬영을 시작하는 것이지만, 그 경로만 있으면
 * 하드웨어가 없는 자리에서는 농인이 아무것도 보낼 수 없습니다 — 수어가 주 입력인데
 * 필담만 남죠. 이 버튼은 같은 API(POST /sign-translations/)를 그대로 쓰는 대체
 * 경로입니다. 기기가 붙으면 둘 다 동작합니다.
 *
 * conversationId를 주면 그 대화방으로, null이면 번역기 모드(대면)로 올라갑니다.
 * 업로드 뒤 결과 메시지는 백엔드가 분석을 마치고 알아서 만들어 주므로
 * (recognitions/services.py), 여기서는 올리기만 하면 됩니다.
 */
export function CaptureButton({
  conversationId,
  onUploaded,
  label = "🎥 수어 촬영",
}: {
  conversationId: number | null;
  onUploaded?: () => void;
  label?: string;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // 카메라를 놓지 않으면 촬영이 끝나도 카메라 불이 계속 켜져 있습니다.
  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  // 화면을 벗어나거나 창을 닫을 때도 반드시 놓습니다.
  useEffect(() => stopCamera, [stopCamera]);

  const close = () => {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }

    stopCamera();
    setPhase("idle");
    setSeconds(0);
    setError(null);
  };

  const open = async () => {
    setError(null);
    setPhase("opening");

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("이 브라우저는 카메라를 지원하지 않아요.");
      setPhase("failed");
      return;
    }

    try {
      // 수어는 손과 표정이라 소리는 필요 없습니다. audio를 끄면 마이크 권한도
      // 묻지 않아서 시연에서 걸리는 단계가 하나 줄어듭니다.
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });

      streamRef.current = stream;
      setPhase("ready");
    } catch (cause) {
      // 권한 거부 / 카메라 없음 / 다른 앱이 점유 중
      const name = (cause as Error)?.name;
      setError(
        name === "NotAllowedError"
          ? "카메라 사용을 허용해주세요. 주소창의 📷 아이콘에서 바꿀 수 있어요."
          : name === "NotFoundError"
            ? "카메라를 찾지 못했어요. 연결을 확인해주세요."
            : `카메라를 열지 못했어요 (${name ?? "알 수 없음"}). 다른 앱이 쓰고 있는지 확인해주세요.`
      );
      setPhase("failed");
    }
  };

  // 스트림이 준비되면 미리보기에 붙입니다. <video>는 모달이 열린 뒤에야 존재하므로
  // open() 안에서 바로 붙일 수 없습니다.
  useEffect(() => {
    if (streamRef.current && videoRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [phase]);

  const upload = useCallback(
    async (blob: Blob) => {
      setPhase("uploading");

      try {
        await createSignTranslation(conversationId, blob, `capture-${Date.now()}.webm`);
        stopCamera();
        setPhase("idle");
        setSeconds(0);
        onUploaded?.();
      } catch (cause) {
        setError(toUserMessage(cause));
        setPhase("ready");
      }
    },
    [conversationId, onUploaded, stopCamera]
  );

  const startRecording = () => {
    const stream = streamRef.current;
    if (!stream) {
      return;
    }

    const mimeType = pickMimeType();
    if (!mimeType) {
      setError("이 브라우저는 영상 녹화를 지원하지 않아요.");
      return;
    }

    chunksRef.current = [];
    const recorder = new MediaRecorder(stream, { mimeType });
    recorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      // 코덱 파라미터를 뗀 순수 타입으로 올립니다.
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      chunksRef.current = [];

      if (blob.size > 0) {
        upload(blob);
      } else {
        setError("녹화된 영상이 비어 있어요. 다시 시도해주세요.");
        setPhase("ready");
      }
    };

    recorder.start();
    setSeconds(0);
    setPhase("recording");
  };

  const stopRecording = () => {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop(); // onstop이 업로드로 이어집니다
    }
  };

  // 녹화 시간 표시 + 30초에서 자동 정지.
  useEffect(() => {
    if (phase !== "recording") {
      return;
    }

    const timer = setInterval(() => {
      setSeconds((current) => {
        if (current + 1 >= MAX_SECONDS) {
          stopRecording();
          return MAX_SECONDS;
        }
        return current + 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [phase]);

  const open_ = phase !== "idle";

  return (
    <>
      <button
        type="button"
        onClick={open}
        className="flex shrink-0 items-center gap-2 rounded-2xl bg-[linear-gradient(180deg,#22C1FF_0%,#1D4ED8_100%)] px-5 py-3 text-sm font-black text-white shadow-[0_14px_34px_rgba(29,78,216,0.32)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0"
      >
        {label}
      </button>

      {open_ && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl animate-soft-scale rounded-[30px] bg-white p-5 shadow-[0_40px_120px_rgba(0,0,0,0.4)]">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-sky-600">
                  🤟 수어 촬영
                </p>
                <h3 className="mt-1 text-xl font-black text-slate-900">
                  {conversationId === null
                    ? "번역기 모드 · 대화방 없이 번역합니다"
                    : "이 대화에 올라갑니다"}
                </h3>
              </div>

              <button
                type="button"
                onClick={close}
                className="rounded-xl px-3 py-1.5 text-sm font-black text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            <div className="relative overflow-hidden rounded-[24px] bg-slate-900">
              {/* 거울처럼 좌우를 뒤집어야 자기 손이 어디 있는지 헷갈리지 않습니다. */}
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="aspect-video w-full -scale-x-100 object-cover"
              />

              {phase === "opening" && (
                <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white/80">
                  📷 카메라를 여는 중…
                </div>
              )}

              {phase === "failed" && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-white/80">
                  <span className="text-4xl">📷</span>
                  <span className="text-sm font-bold">카메라를 열지 못했어요</span>
                </div>
              )}

              {phase === "recording" && (
                <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full bg-rose-500 px-3 py-1.5 text-xs font-black text-white">
                  <span className="h-2 w-2 animate-soft-pulse rounded-full bg-white" />
                  {seconds}초 / {MAX_SECONDS}초
                </div>
              )}

              {phase === "uploading" && (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70 text-sm font-black text-white">
                  ⏳ 올리는 중…
                </div>
              )}
            </div>

            {error && (
              <p className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-600">
                {error}
              </p>
            )}

            <div className="mt-4 flex gap-2">
              {phase === "failed" ? (
                <button
                  type="button"
                  onClick={open}
                  className="flex-1 rounded-2xl bg-slate-900 px-5 py-3.5 text-sm font-black text-white transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
                >
                  🔄 다시 시도
                </button>
              ) : phase === "recording" ? (
                <button
                  type="button"
                  onClick={stopRecording}
                  className="flex-1 rounded-2xl bg-rose-500 px-5 py-3.5 text-sm font-black text-white shadow-[0_14px_34px_rgba(244,63,94,0.3)] transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0"
                >
                  ⏹ 촬영 끝 · 보내기
                </button>
              ) : (
                <button
                  type="button"
                  onClick={startRecording}
                  disabled={phase !== "ready"}
                  className="flex-1 rounded-2xl bg-[linear-gradient(180deg,#22C1FF_0%,#1D4ED8_100%)] px-5 py-3.5 text-sm font-black text-white shadow-[0_14px_34px_rgba(29,78,216,0.32)] transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50"
                >
                  🔴 촬영 시작
                </button>
              )}
            </div>

            <p className="mt-3 text-center text-xs leading-5 text-slate-400">
              최대 {MAX_SECONDS}초까지 찍을 수 있어요. 촬영을 마치면 AI가 분석해서
              {conversationId === null ? " 아래에" : " 대화에"} 올려줍니다.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
