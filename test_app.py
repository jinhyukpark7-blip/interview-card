# 완료 기준(F1)을 자동으로 검사해요. 실행: python -m unittest
# 진짜 data/ 는 건드리지 않고, 시험마다 임시 폴더를 만들어 써요.

import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer
from urllib.parse import quote

import app

HEADER = "id,category,question,tip\n"

# data/questions.csv 가상 데이터와 같은 모양이에요 (10줄, 7번은 질문 칸이 비어 있어요)
SAMPLE = (
    "﻿" + HEADER +
    "1,자기소개,1분 동안 자기소개를 해 보세요,이름 → 강점 1개 → 해외영업과 연결\n"
    "2,자기소개,본인의 강점과 약점을 말해 보세요,약점은 고치고 있는 방법까지\n"
    "3,지원동기,왜 해외영업 직무를 선택했나요?,경험 1개 + 직무와 연결\n"
    '4,지원동기,왜 동남아 시장인가요?,"성장성, 개인 경험, 언어"\n'
    '5,동남아 시장,베트남 시장의 특징을 말해 보세요,"인구 1억, 젊은 소비층, 제조 기지"\n'
    '6,동남아 시장,인도네시아에 우리 제품을 판다면 무엇부터 할까요?,"시장 조사, 현지 파트너, 할랄 인증"\n'
    "7,동남아 시장,,빈 질문 (건너뛰기 시험용)\n"
    "8,동남아 시장,현지 거래처가 납기를 계속 늦추면 어떻게 하나요?,원인 확인 → 대안 → 기록\n"
    "9,영어 질문,Please introduce yourself in English.,\"30초, 쉬운 문장\"\n"
    '10,영어 질문,Why do you want to work in Southeast Asia?,"Growth, experience, passion"\n'
)


def read_bytes(path):
    """파일 내용을 바이트로 읽고 바로 닫아요."""
    with open(path, "rb") as f:
        return f.read()


class TempDataTest(unittest.TestCase):
    """시험마다 새 임시 폴더를 만들고, 끝나면 지워요."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.qpath = os.path.join(self.dir, app.QUESTIONS_FILE)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_questions(self, text):
        with open(self.qpath, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def home(self, query=""):
        return app.build_home(query, self.dir)


class TestF1Read(TempDataTest):
    def test_sample_has_9_cards(self):
        self.write_questions(SAMPLE)
        cards = app.read_questions(self.qpath)
        self.assertEqual(len(cards), 9)

    def test_f1_2_blank_question_skipped(self):
        self.write_questions(SAMPLE)
        ids = [c["id"] for c in app.read_questions(self.qpath)]
        self.assertNotIn(7, ids)

    def test_missing_file_gives_empty_list(self):
        self.assertEqual(app.read_questions(self.qpath), [])

    def test_header_only_gives_empty_list(self):
        self.write_questions(HEADER)
        self.assertEqual(app.read_questions(self.qpath), [])

    def test_weird_lines_skipped(self):
        # 빈 줄, 칸이 모자란 줄, 번호가 글자인 줄, 모르는 분야 줄은 건너뛰어요
        self.write_questions(
            HEADER + "\n" + "2,자기소개\n" + "abc,자기소개,질문,팁\n"
            + "3,없는분야,질문,팁\n" + "4,지원동기,정상 질문,팁\n"
        )
        cards = app.read_questions(self.qpath)
        self.assertEqual([c["id"] for c in cards], [4])

    def test_read_does_not_change_file(self):
        self.write_questions(SAMPLE)
        before = read_bytes(self.qpath)
        app.read_questions(self.qpath)
        self.assertEqual(read_bytes(self.qpath), before)


class TestF1Check(unittest.TestCase):
    def test_check_category(self):
        for name in ["전체", "자기소개", "지원동기", "동남아 시장", "영어 질문"]:
            self.assertIsNone(app.check_category(name))
        self.assertEqual(app.check_category("없는분야"), app.MSG_BAD_CATEGORY)

    def test_clamp_index(self):
        self.assertEqual(app.clamp_index("abc", 3), 0)
        self.assertEqual(app.clamp_index("-5", 3), 0)
        self.assertEqual(app.clamp_index("99", 3), 2)
        self.assertEqual(app.clamp_index("1", 3), 1)
        self.assertEqual(app.clamp_index("1", 0), 0)

    def test_position_text(self):
        self.assertEqual(app.position_text(0, 3), "1 / 3")


class TestF1Screen(TempDataTest):
    def test_f1_1_all_shows_1_of_9(self):
        self.write_questions(SAMPLE)
        self.assertIn("1 / 9", self.home(""))
        self.assertIn("1 / 9", self.home("cat=" + quote("전체")))

    def test_f1_1_category_only_its_cards(self):
        self.write_questions(SAMPLE)
        expected = {"자기소개": 2, "지원동기": 2, "동남아 시장": 3, "영어 질문": 2}
        for name, count in expected.items():
            cards = app.filter_cards(app.read_questions(self.qpath), name)
            self.assertEqual(len(cards), count, name)
            self.assertTrue(all(c["category"] == name for c in cards))
            page = self.home("cat=" + quote(name))
            self.assertIn(f"1 / {count}", page)

    def test_f1_1_southeast_asia_1_of_3(self):
        self.write_questions(SAMPLE)
        page = self.home("cat=" + quote("동남아 시장") + "&i=2")
        self.assertIn("3 / 3", page)
        self.assertIn("현지 거래처가 납기를", page)

    def test_f1_2_no_error_and_blank_not_shown(self):
        self.write_questions(SAMPLE)
        page = self.home("cat=" + quote("동남아 시장"))
        self.assertIn("1 / 3", page)
        self.assertNotIn("빈 질문 (건너뛰기 시험용)", page)

    def test_f1_3_missing_file_message(self):
        page = self.home("")
        self.assertIn("연습할 질문이 없어요", page)

    def test_f1_3_header_only_message(self):
        self.write_questions(HEADER)
        self.assertIn("연습할 질문이 없어요", self.home(""))

    def test_tip_is_on_card_back(self):
        self.write_questions(SAMPLE)
        page = self.home("")
        self.assertIn("class='tip'", page)
        self.assertIn("이름 → 강점 1개 → 해외영업과 연결", page)

    def test_bad_category_falls_back_to_all(self):
        self.write_questions(SAMPLE)
        page = self.home("cat=" + quote("없는분야"))
        self.assertIn(app.MSG_BAD_CATEGORY, page)
        self.assertIn("1 / 9", page)

    def test_html_is_escaped(self):
        self.write_questions(HEADER + "1,자기소개,<b>굵게</b>,팁\n")
        page = self.home("")
        self.assertIn("&lt;b&gt;굵게&lt;/b&gt;", page)


class TestServer(TempDataTest):
    """진짜로 서버를 띄워 화면이 열리는지 봐요 (빈 포트를 골라 써요)."""

    def start(self):
        handler = type("H", (app.Handler,), {"data_dir": self.dir,
                                            "log_message": lambda *a: None})
        self.server = ThreadingHTTPServer(("localhost", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://localhost:{self.server.server_address[1]}"

    def tearDown(self):
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
        super().tearDown()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read().decode("utf-8")

    def test_page_opens_with_sample(self):
        self.write_questions(SAMPLE)
        self.start()
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("1 / 9", body)

    def test_page_opens_without_file(self):
        self.start()
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("연습할 질문이 없어요", body)

    def test_unknown_path_korean(self):
        self.start()
        status, body = self.get("/nothing")
        self.assertEqual(status, 404)
        self.assertIn(app.MSG_NOT_FOUND, body)
        self.assertNotIn("Traceback", body)


class TestBackup(TempDataTest):
    def test_backup_copies_csv(self):
        self.write_questions(SAMPLE)
        target = app.backup_data(self.dir, datetime(2026, 11, 11, 9, 30, 5))
        self.assertEqual(target, os.path.join(self.dir, "backup", "20261111_093005"))
        copied = os.path.join(target, app.QUESTIONS_FILE)
        self.assertEqual(read_bytes(copied), read_bytes(self.qpath))

    def test_backup_without_csv(self):
        self.assertIsNone(app.backup_data(self.dir))
        self.assertIsNone(app.backup_data(os.path.join(self.dir, "없음")))


class TestServerAddress(unittest.TestCase):
    """어디서 켜졌는지에 따라 열 주소와 번호가 맞게 정해지는지 봐요 (가짜 설정 목록을 넣어요)."""

    def test_my_computer_is_localhost_8000(self):
        self.assertEqual(app.server_address({}), ("localhost", 8000))

    def test_my_computer_ignores_port_setting(self):
        # 내 컴퓨터에 PORT 설정이 있어도 바깥에 열리지 않고 그대로예요
        self.assertEqual(app.server_address({"PORT": "5000"}), ("localhost", 8000))

    def test_render_uses_given_port(self):
        env = {"RENDER": "true", "PORT": "10000"}
        self.assertEqual(app.server_address(env), ("0.0.0.0", 10000))

    def test_render_bad_port_uses_default(self):
        for port in ["", "abc", None]:
            env = {"RENDER": "true", "PORT": port}
            self.assertEqual(app.server_address(env), ("0.0.0.0", 10000))


if __name__ == "__main__":
    unittest.main()
