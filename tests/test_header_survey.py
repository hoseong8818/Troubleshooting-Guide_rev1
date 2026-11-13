"""T074: 헤더 조사 보고서 (FR-025, NFR-009).

`python -m trouble_merge.survey`가 보이는 시트의 헤더 행만 읽어 양식별로 묶고,
현재 컬럼 대응 표와 비교한 결과를 `survey_*.txt`에 낸다. 셀 값과 등록되지 않은 컬럼명은 내지 않는다.
입력은 가짜 데이터와 임시로 만든 파일만 쓴다. 원본 config/는 건드리지 않는다.
"""

import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from openpyxl import Workbook

from tests.support import FAKE, ROOT, SRC, CliCase, make_config, sha256, write_xlsx

FAKE_FILES = ["A_basic.xlsx", "A_trap.xlsx", "B_basic.xlsx", "B_more.xlsx", "B_trap.xlsx"]
B_HEADER = ["발생일", "장비번호", "고장내용", "고장원인", "처리결과", "부품구분", "작업자"]
NEW_HEADER = ["일시", "장비번호", "현상", "LEAK-컬럼", "처리결과"]
C_HEADER = ["접수일", "호기", "현상내용", "원인내용", "대책", "유형"]
C_LINES = [
    "C,접수일,일자,3,",
    "C,호기,설비,3,",
    "C,현상내용,증상,3,",
    "C,원인내용,원인,3,",
    "C,대책,조치,3,",
    "C,유형,분류,3,",
]
SECTION = re.compile(r"^양식 (\d+)$")


def run_survey(inputs, config, out, *extra):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [
        sys.executable, "-m", "trouble_merge.survey",
        "--input", *[str(p) for p in inputs],
        "--config", str(config),
        "--out", str(out),
        *extra,
    ]
    return subprocess.run(
        cmd, cwd=str(ROOT), env=env, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=120,
    )


def parse_report(text):
    """(요약 사전, {양식 번호: 사전})로 나눈다. 같은 이름이 여러 줄이면 목록으로 모은다."""
    summary, sections, current = {}, {}, None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        found = SECTION.match(line)
        if found:
            current = sections.setdefault(int(found.group(1)), {})
            continue
        if ": " not in line:
            continue
        name, value = line.split(": ", 1)
        target = summary if current is None else current
        target.setdefault(name, []).append(value)
    return summary, sections


def one(table, name):
    values = table.get(name, [])
    if len(values) != 1:
        raise AssertionError("'%s' 줄이 하나가 아님: %d개" % (name, len(values)))
    return values[0]


class HeaderSurveyTest(CliCase):
    def setUp(self):
        super().setUp()
        self.folder = self.tmp / "in"
        self.folder.mkdir()
        for name in FAKE_FILES:
            shutil.copy(FAKE / name, self.folder / name)
        write_xlsx(self.folder / "b_extra.xlsx", B_HEADER + ["LEAK-추가"],
                   [["2026-11-01", "PMP01", "LEAK-증상", "LEAK-원인", "LEAK-조치", "LEAK-분류", "LEAK-사람", "LEAK-값"]])
        write_xlsx(self.folder / "new_form.xlsx", NEW_HEADER,
                   [["LEAK-일시", "LEAK-설비", "LEAK-현상", "LEAK-값", "LEAK-처리"]])
        wb = Workbook()
        ws = wb.active
        ws.title = "시트1"
        ws.append(["LEAK-제목"])
        ws.append([])
        ws.append(C_HEADER)
        ws.append(["LEAK-일", "LEAK-호기", "LEAK-현상", "LEAK-원인", "LEAK-대책", "LEAK-유형"])
        wb.save(self.folder / "c_title.xlsx")
        (self.folder / "old.xls").write_bytes(b"not an xlsx")
        self.config = make_config(self.tmp, column_map_extra=C_LINES)

    def survey(self, *extra, inputs=None, config=None):
        result = run_survey(inputs or [self.folder], config or self.config, self.out, *extra)
        reports = sorted(Path(self.out).glob("survey_*.txt"))
        text = reports[0].read_text(encoding="utf-8") if len(reports) == 1 else None
        return result, reports, text

    def find(self, sections, relation, columns):
        found = [n for n, s in sections.items()
                 if s.get("설정") == [relation] and s.get("컬럼 수") == [str(columns)]]
        self.assertEqual(len(found), 1, "%s, 컬럼 %d개인 양식이 하나가 아님: %r" % (relation, columns, found))
        return found[0], sections[found[0]]

    def test_summary_lines(self):
        result, reports, text = self.survey()
        self.assertEqual(result.returncode, 1, "건너뛴 파일이 있으면 종료 코드 1. stderr: " + result.stderr[-300:])
        self.assertEqual(len(reports), 1)
        summary, sections = parse_report(text)
        self.assertEqual(one(summary, "조사한 파일 수"), "9")
        self.assertEqual(one(summary, "읽은 파일 수"), "8")
        self.assertRegex(one(summary, "건너뛴 파일"), r"^file_\d\d 지원하지 않는 형식$")
        self.assertEqual(one(summary, "숨긴 시트 수"), "4")
        self.assertEqual(one(summary, "헤더 없는 시트 수"), "0")
        self.assertEqual(one(summary, "양식 수"), "5")
        self.assertEqual(one(summary, "새 양식 수"), "1")
        self.assertEqual(sorted(sections), [1, 2, 3, 4, 5])

    def test_groups_are_counted_and_compared_with_the_column_map(self):
        _, _, text = self.survey()
        _, sections = parse_report(text)
        b_no, b = self.find(sections, "기존 양식 B", 7)
        self.assertEqual(b_no, 1, "시트 수가 가장 많은 양식이 양식 1")
        self.assertEqual(one(b, "파일 수"), "3")
        self.assertEqual(one(b, "시트 수"), "3")
        a_no, a = self.find(sections, "기존 양식 A", 6)
        self.assertEqual(a_no, 2)
        self.assertEqual(one(a, "파일 수"), "2", "숨긴 시트는 세지 않는다")
        self.assertEqual(one(a, "시트 수"), "2")

    def test_one_extra_column_is_a_separate_group_one_column_away(self):
        _, _, text = self.survey()
        _, sections = parse_report(text)
        b_no, _ = self.find(sections, "기존 양식 B", 7)
        _, extra = self.find(sections, "기존 양식 B", 8)
        self.assertEqual(one(extra, "파일 수"), "1")
        self.assertEqual(one(extra, "가장 가까운 양식"), "양식 %d (컬럼 1개 차이)" % b_no)

    def test_new_form_is_marked_with_the_nearest_existing_form(self):
        _, _, text = self.survey()
        _, sections = parse_report(text)
        _, new = self.find(sections, "새 양식", 5)
        self.assertEqual(one(new, "파일 수"), "1")
        self.assertEqual(one(new, "가장 가까운 기존 양식"), "B (빠진 등록 컬럼 4개)")

    def test_header_row_from_the_column_map(self):
        _, _, text = self.survey()
        _, sections = parse_report(text)
        _, c = self.find(sections, "기존 양식 C", 6)
        self.assertEqual(one(c, "컬럼"), ", ".join(C_HEADER))

    def test_unregistered_columns_are_shown_by_position(self):
        _, _, text = self.survey()
        _, sections = parse_report(text)
        _, b = self.find(sections, "기존 양식 B", 7)
        self.assertEqual(one(b, "컬럼"), "발생일, 장비번호, 고장내용, 고장원인, 처리결과, 부품구분, 열 7(G)")
        _, new = self.find(sections, "새 양식", 5)
        self.assertEqual(one(new, "컬럼"), "열 1(A), 장비번호, 열 3(C), 열 4(D), 처리결과")

    def test_no_cell_values_or_real_names_by_default(self):
        before = {p.name: sha256(p) for p in self.folder.iterdir()}
        result, _, text = self.survey()
        for where, content in (("보고서", text), ("stdout", result.stdout), ("stderr", result.stderr)):
            for word in ("LEAK-", "작업자", "에러코드", "일시", "A_basic", "new_form", "시트1", "Traceback"):
                self.assertNotIn(word, content, "%s에 '%s'가 있다" % (where, word))
        self.assertRegex(text, r"(?m)^시트: .*file_\d\d sheet_\d\d")
        names = sorted(Path(self.out).glob("names_*.txt"))
        self.assertEqual(len(names), 1, "실제 이름 대응표는 별도 파일")
        self.assertIn("new_form.xlsx", names[0].read_text(encoding="utf-8"))
        self.assertEqual(sorted(Path(self.out).glob("*.xlsx")), [], "통합 엑셀을 만들지 않는다")
        self.assertEqual({p.name: sha256(p) for p in self.folder.iterdir()}, before, "입력 파일이 바뀌었다")

    def test_show_names_prints_real_file_names(self):
        _, _, text = self.survey("--show-names")
        self.assertIn("new_form.xlsx", text)
        self.assertNotIn("LEAK-", text)

    def test_config_error_exits_2_without_traceback(self):
        empty = self.tmp / "empty_config"
        empty.mkdir()
        result, reports, _ = self.survey(config=empty)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(reports, [])

    def test_no_readable_file_exits_2(self):
        result, reports, text = self.survey(inputs=[self.folder / "old.xls"])
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(len(reports), 1, "읽은 파일이 없어도 보고서는 남긴다")
        summary, _ = parse_report(text)
        self.assertEqual(one(summary, "읽은 파일 수"), "0")
        self.assertEqual(one(summary, "양식 수"), "0")


if __name__ == "__main__":
    unittest.main()
