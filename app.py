# 면접 카드 연습장 — 지금은 F1(질문 카드 연습)만 들어 있어요.
# 켜는 법: python app.py  →  브라우저에서 http://localhost:8000
# 파이썬 기본 기능만 써요. 따로 설치할 것이 없어요.

import csv
import html
import os
import shutil
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

# ──────────────────────────────────────────────
# 화면 문구 (PRD와 글자 하나 다르지 않게 여기에 모아 둬요)
# ──────────────────────────────────────────────
MSG_TITLE = "면접 카드 연습장"
MSG_NO_QUESTIONS = "연습할 질문이 없어요"          # F1-3
MSG_POSITION = "{now} / {total}"                  # F1-1 예: "1 / 3"
MSG_BAD_CATEGORY = "없는 분야예요. 전체 카드를 보여 줄게요"
MSG_PAGE_ERROR = "화면을 열지 못했어요. 다시 시도해 주세요"
MSG_NOT_FOUND = "없는 페이지예요. 첫 화면으로 가 주세요"
MSG_TIP_LABEL = "답변 포인트"
MSG_BTN_FLIP = "뒤집기"
MSG_BTN_PREV = "이전 카드"
MSG_BTN_NEXT = "다음 카드"
MSG_BTN_HOME = "첫 화면"

# 분야 이름 (PRD 3장 · F1 그대로)
CATEGORY_ALL = "전체"
CATEGORIES = ["자기소개", "지원동기", "동남아 시장", "영어 질문"]

# ──────────────────────────────────────────────
# 숫자 · 경로 기준 (여기 한 곳만 고치면 돼요)
# ──────────────────────────────────────────────
# 내 컴퓨터에서 켤 때: 지금처럼 localhost:8000 (내 컴퓨터 안에서만 열려요)
LOCAL_HOST = "localhost"
LOCAL_PORT = 8000
# Render 무료 서버에서 켤 때: 바깥에서 들어올 수 있게 열고, Render가 정해 준 번호를 써요
RENDER_HOST = "0.0.0.0"
RENDER_DEFAULT_PORT = 10000      # Render가 번호를 안 알려 줄 때 쓰는 Render 기본 번호예요
ENV_RENDER = "RENDER"            # Render 서버에만 있는 표시 이름이에요
ENV_PORT = "PORT"                # Render가 번호를 적어 두는 칸 이름이에요
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
QUESTIONS_FILE = "questions.csv"
BACKUP_DIR_NAME = "backup"
BACKUP_TIME_FORMAT = "%Y%m%d_%H%M%S"


# ──────────────────────────────────────────────
# 1) 읽기 — 파일을 읽어서 목록으로 돌려줘요 (파일은 절대 바꾸지 않아요)
# ──────────────────────────────────────────────
def read_questions(path):
    """questions.csv를 읽어 카드 목록을 돌려줘요.

    파일이 없거나, 머리줄만 있거나, 읽다가 문제가 생기면 빈 목록을 돌려줘요.
    질문 칸이 빈 줄, 번호가 숫자가 아닌 줄, 모르는 분야 줄은 건너뛰어요.
    """
    cards = []
    if not os.path.exists(path):
        return cards
    try:
        # utf-8-sig: 엑셀이 붙이는 BOM 글자가 있어도 잘 읽어요
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                qid = (row.get("id") or "").strip()
                category = (row.get("category") or "").strip()
                question = (row.get("question") or "").strip()
                tip = (row.get("tip") or "").strip()
                if not question:          # 질문이 비면 카드가 아니에요 (F1-2)
                    continue
                if not qid.isdigit():     # 번호가 이상하면 건너뛰어요
                    continue
                if category not in CATEGORIES:  # 모르는 분야도 건너뛰어요
                    continue
                cards.append({"id": int(qid), "category": category,
                              "question": question, "tip": tip})
    except Exception:
        # 파일이 망가져도 화면은 열려야 해서, 자세한 내용은 터미널에만 남겨요
        print("[알림] 질문 파일을 읽지 못했어요:", path)
        traceback.print_exc()
        return []
    return cards


def backup_data(data_dir, now=None):
    """data/ 안의 CSV를 data/backup/YYYYMMDD_HHMMSS/ 에 복사해 둬요.

    원본은 건드리지 않고 복사만 해요. 만든 백업 폴더 경로를 돌려주고,
    복사할 CSV가 없으면 None을 돌려줘요.
    """
    if not os.path.isdir(data_dir):
        return None
    csv_files = [name for name in os.listdir(data_dir)
                 if name.lower().endswith(".csv")
                 and os.path.isfile(os.path.join(data_dir, name))]
    if not csv_files:
        return None
    stamp = (now or datetime.now()).strftime(BACKUP_TIME_FORMAT)
    target = os.path.join(data_dir, BACKUP_DIR_NAME, stamp)
    os.makedirs(target, exist_ok=True)
    for name in csv_files:
        shutil.copy2(os.path.join(data_dir, name), os.path.join(target, name))
    return target


# ──────────────────────────────────────────────
# 2) 입력 검사 — 화면 없이 문구만 돌려줘요 (문제없으면 None)
# ──────────────────────────────────────────────
def check_category(value):
    """고른 분야가 맞는 이름인지 봐요. 맞으면 None, 아니면 안내 문구."""
    if value in ([CATEGORY_ALL] + CATEGORIES):
        return None
    return MSG_BAD_CATEGORY


def filter_cards(cards, category):
    """분야에 맞는 카드만 골라 줘요. "전체"면 모든 카드예요."""
    if category == CATEGORY_ALL:
        return list(cards)
    return [c for c in cards if c["category"] == category]


def clamp_index(value, total):
    """몇 번째 카드인지(0부터) 안전한 숫자로 맞춰 줘요.

    숫자가 아니거나 범위를 벗어나면 첫 카드나 마지막 카드로 맞춰요.
    """
    if total <= 0:
        return 0
    try:
        i = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(i, total - 1))


def position_text(index, total):
    """"1 / 3" 같은 위치 글자를 만들어요."""
    return MSG_POSITION.format(now=index + 1, total=total)


# ──────────────────────────────────────────────
# 3) 화면 그리기 — 받은 값으로 HTML 글자를 만들어요
# ──────────────────────────────────────────────
CSS = """
:root { --ink:#1f2a44; --accent:#2f6fde; --paper:#f4f6fb; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
  font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;
  font-size:18px; line-height:1.6; }
main { max-width:560px; margin:0 auto; padding:20px 16px 40px; }
h1 { font-size:22px; margin:0 0 14px; }
.tabs { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
.tab { padding:6px 12px; border:1px solid var(--accent); border-radius:999px;
  color:var(--accent); text-decoration:none; font-size:16px; background:#fff; }
.tab.on { background:var(--accent); color:#fff; }
.pos { text-align:center; font-weight:bold; margin-bottom:8px; }
.card { background:#fff; border:1px solid #d6dcea; border-radius:14px;
  padding:28px 20px; min-height:200px; display:flex; flex-direction:column;
  justify-content:center; text-align:center; overflow-wrap:anywhere; }
.cat { font-size:15px; color:var(--accent); margin-bottom:8px; }
.q { font-size:21px; font-weight:bold; }
.tip { display:none; margin-top:18px; padding-top:14px; border-top:1px dashed #c3cbe0; }
.card.flipped .tip { display:block; }
.label { font-size:15px; color:var(--accent); }
.btns { display:flex; gap:8px; margin-top:16px; }
.btn { flex:1; padding:12px 8px; border:none; border-radius:10px; font-size:17px;
  text-align:center; text-decoration:none; background:var(--accent); color:#fff;
  cursor:pointer; font-family:inherit; }
.btn.sub { background:#fff; color:var(--accent); border:1px solid var(--accent); }
.btn.off { opacity:.35; pointer-events:none; }
.notice { background:#fff; border:1px solid #d6dcea; border-radius:14px;
  padding:28px 20px; text-align:center; }
"""

# 뒤집기 버튼: 누르면 카드 뒷면(답변 포인트)이 보였다 숨었다 해요
FLIP_JS = """
document.getElementById('flip').addEventListener('click', function () {
  document.getElementById('card').classList.toggle('flipped');
});
"""


def esc(text):
    """화면에 넣을 글자를 안전하게 바꿔요 (<, > 같은 글자 때문에 화면이 깨지지 않게)."""
    return html.escape(str(text), quote=True)


def page_url(category, index):
    """분야와 카드 번호로 주소를 만들어요."""
    return "/?" + urlencode({"cat": category, "i": index})


def render_layout(body):
    """모든 화면에 공통으로 쓰는 틀이에요."""
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{esc(MSG_TITLE)}</title><style>{CSS}</style></head>"
        f"<body><main><h1>{esc(MSG_TITLE)}</h1>{body}</main></body></html>"
    )


def render_tabs(current):
    """분야 고르기 버튼 줄을 그려요."""
    parts = []
    for name in [CATEGORY_ALL] + CATEGORIES:
        on = " on" if name == current else ""
        parts.append(f"<a class='tab{on}' href='{esc(page_url(name, 0))}'>{esc(name)}</a>")
    return "<nav class='tabs'>" + "".join(parts) + "</nav>"


def render_practice_page(cards, category, index, notice=None):
    """F1 연습 화면을 그려요. cards는 이미 분야로 골라 둔 카드 목록이에요."""
    body = render_tabs(category)
    if notice:
        body += f"<p class='pos'>{esc(notice)}</p>"
    if not cards:
        body += f"<div class='notice'>{esc(MSG_NO_QUESTIONS)}</div>"
        return render_layout(body)

    total = len(cards)
    card = cards[index]
    prev_cls = "btn sub" + (" off" if index == 0 else "")
    next_cls = "btn sub" + (" off" if index >= total - 1 else "")
    body += (
        f"<div class='pos'>{esc(position_text(index, total))}</div>"
        f"<section id='card' class='card'>"
        f"<div class='cat'>{esc(card['category'])}</div>"
        f"<div class='q'>{esc(card['question'])}</div>"
        f"<div class='tip'><div class='label'>{esc(MSG_TIP_LABEL)}</div>"
        f"{esc(card['tip'])}</div>"
        f"</section>"
        f"<div class='btns'><button id='flip' class='btn' type='button'>{esc(MSG_BTN_FLIP)}</button></div>"
        f"<div class='btns'>"
        f"<a class='{prev_cls}' href='{esc(page_url(category, max(index - 1, 0)))}'>{esc(MSG_BTN_PREV)}</a>"
        f"<a class='{next_cls}' href='{esc(page_url(category, min(index + 1, total - 1)))}'>{esc(MSG_BTN_NEXT)}</a>"
        f"</div>"
        f"<script>{FLIP_JS}</script>"
    )
    return render_layout(body)


def render_message_page(message):
    """에러처럼 문구 하나만 보여 주는 화면이에요."""
    return render_layout(
        f"<div class='notice'>{esc(message)}</div>"
        f"<div class='btns'><a class='btn' href='/'>{esc(MSG_BTN_HOME)}</a></div>"
    )


# ──────────────────────────────────────────────
# 연결 — 주소로 들어온 요청을 읽기·검사·그리기에 이어 줘요
# ──────────────────────────────────────────────
def build_home(query, data_dir):
    """주소의 ?cat=...&i=... 를 보고 연습 화면 HTML을 만들어요."""
    params = parse_qs(query)
    category = params.get("cat", [CATEGORY_ALL])[0]
    notice = check_category(category)
    if notice:
        category = CATEGORY_ALL
    all_cards = read_questions(os.path.join(data_dir, QUESTIONS_FILE))
    cards = filter_cards(all_cards, category)
    index = clamp_index(params.get("i", ["0"])[0], len(cards))
    return render_practice_page(cards, category, index, notice)


class Handler(BaseHTTPRequestHandler):
    data_dir = DATA_DIR  # 시험할 때는 임시 폴더로 바꿔 끼워요

    def send_html(self, status, text):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            url = urlparse(self.path)
            if url.path == "/":
                self.send_html(200, build_home(url.query, self.data_dir))
            else:
                self.send_html(404, render_message_page(MSG_NOT_FOUND))
        except Exception:
            # 화면에는 쉬운 한국어만, 자세한 에러는 터미널에만 남겨요
            traceback.print_exc()
            self.send_html(500, render_message_page(MSG_PAGE_ERROR))


def server_address(env):
    """어디서 켜졌는지 보고 (열 주소, 번호)를 돌려줘요.

    env는 컴퓨터의 설정 목록(os.environ)이에요. 시험할 때는 가짜 목록을 넣어요.
    - Render 표시(RENDER)가 있으면: 바깥에 열고, Render가 준 PORT 번호를 써요
    - 없으면(내 컴퓨터): 언제나 localhost:8000 이에요. PORT 설정이 있어도 무시해요
    """
    if not env.get(ENV_RENDER):
        return LOCAL_HOST, LOCAL_PORT
    port = (env.get(ENV_PORT) or "").strip()
    if port.isdigit():
        return RENDER_HOST, int(port)
    return RENDER_HOST, RENDER_DEFAULT_PORT


def main():
    try:
        target = backup_data(DATA_DIR)
        if target:
            print("백업했어요:", target)
    except Exception:
        # 백업이 실패해도 연습은 할 수 있게 앱은 켜 둬요
        print("[알림] 백업하지 못했어요. 자세한 내용:")
        traceback.print_exc()
    host, port = server_address(os.environ)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"켜졌어요 → http://{host}:{port}  (끄려면 Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("앱을 껐어요.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
