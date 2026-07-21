// 이모지를 "눈에 보이는 한 글자" 단위로 다룹니다.
//
// 농인 아이디가 이모지 조합(🐶🍎⭐)이라, 문자열을 코드포인트나 UTF-16 단위로 자르면
// 글자가 깨집니다:
//   "🐶".length === 2          — 서로게이트 페어라 slice(0,1)이 반쪽만 남깁니다
//   "✈️", "❤️"                 — 기호 + 변이 선택자(U+FE0F)라 코드포인트가 2개입니다
//   Array.from("✈️").length === 2  — 코드포인트로 쪼개서 역시 깨집니다
//
// Intl.Segmenter만 자소(grapheme) 단위를 제대로 셉니다.

// Segmenter 생성이 싸지 않아 한 번 만들어 재사용합니다.
const segmenter =
  typeof Intl !== "undefined" && "Segmenter" in Intl
    ? new Intl.Segmenter("ko", { granularity: "grapheme" })
    : null;

function split(value: string): string[] {
  if (!segmenter) {
    // 낡은 브라우저 대비. 이모지 하나가 둘로 세어질 수 있지만 깨지진 않습니다.
    return Array.from(value);
  }

  return Array.from(segmenter.segment(value), (item) => item.segment);
}

/** 눈에 보이는 글자 수. 이모지 하나는 1로 셉니다. */
export function countGraphemes(value: string): number {
  return value ? split(value).length : 0;
}

/** 맨 뒤 한 글자를 지웁니다 (⌫). */
export function removeLastGrapheme(value: string): string {
  return value ? split(value).slice(0, -1).join("") : value;
}

/** 첫 글자. 아바타에 씁니다. */
export function firstGrapheme(value: string): string {
  return value ? (split(value)[0] ?? "") : "";
}
