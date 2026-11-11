"""면접 카드 연습장 — 시험용 가상 데이터를 data/ 에 만든다.

사용법
    python make_sample.py          # 질문 10줄 + 답변 3줄 + 자신감 표시 4줄
    python make_sample.py --empty  # 질문 10줄만, 답변·자신감은 머리줄만 (기록 0개 시험용)

이미 파일이 있으면 덮어쓴다. 실제 개인 정보는 들어 있지 않다.
"""

import csv
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

QUESTIONS_HEADER = ["id", "category", "question", "tip"]
QUESTIONS = [
    [1, "자기소개", "1분 동안 자기소개를 해 보세요", "이름 → 강점 1개 → 해외영업과 연결"],
    [2, "자기소개", "본인의 강점과 약점을 말해 보세요", "약점은 고치고 있는 방법까지"],
    [3, "지원동기", "왜 해외영업 직무를 선택했나요?", "경험 1개 + 직무와 연결"],
    [4, "지원동기", "왜 동남아 시장인가요?", "성장성, 개인 경험, 언어"],
    [5, "동남아 시장", "베트남 시장의 특징을 말해 보세요", "인구 1억, 젊은 소비층, 제조 기지"],
    [6, "동남아 시장", "인도네시아에 우리 제품을 판다면 무엇부터 할까요?", "시장 조사, 현지 파트너, 할랄 인증"],
    [7, "동남아 시장", "", "빈 질문 (건너뛰기 시험용)"],
    [8, "동남아 시장", "현지 거래처가 납기를 계속 늦추면 어떻게 하나요?", "원인 확인 → 대안 → 기록"],
    [9, "영어 질문", "Please introduce yourself in English.", "30초, 쉬운 문장"],
    [10, "영어 질문", "Why do you want to work in Southeast Asia?", "Growth, experience, passion"],
]

ANSWERS_HEADER = ["question_id", "saved_at", "answer"]
ANSWERS = [
    [1, "2026-11-09 21:00:00", "안녕하세요, 저는 해외영업을 꿈꾸는 신입 지원자입니다."],
    [1, "2026-11-10 21:30:00", "안녕하세요, 저는 끈기가 강점인 지원자입니다. 교환학생 때 현지 시장 조사 프로젝트를 끝까지 마친 경험을 해외영업에서 살리고 싶습니다."],
    [5, "2026-11-10 22:00:00", "베트남은 젊은 인구가 많고 소비가 빠르게 늘고 있어, 새 제품을 알리기 좋은 시장이라고 생각합니다."],
]

CONFIDENCE_HEADER = ["question_id", "saved_at", "level"]
CONFIDENCE = [
    [1, "2026-11-09 21:05:00", "애매"],
    [1, "2026-11-10 21:35:00", "자신 있음"],
    [3, "2026-11-10 21:40:00", "모름"],
    [5, "2026-11-10 22:05:00", "애매"],
]


def write_csv(name, header, rows):
    path = DATA_DIR / name
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"{path.relative_to(DATA_DIR.parent)}: {len(rows)}줄")


def main():
    empty = "--empty" in sys.argv[1:]
    DATA_DIR.mkdir(exist_ok=True)
    write_csv("questions.csv", QUESTIONS_HEADER, QUESTIONS)
    write_csv("answers.csv", ANSWERS_HEADER, [] if empty else ANSWERS)
    write_csv("confidence.csv", CONFIDENCE_HEADER, [] if empty else CONFIDENCE)


if __name__ == "__main__":
    main()
