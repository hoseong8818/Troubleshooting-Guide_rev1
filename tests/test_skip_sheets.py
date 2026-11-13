"""T094: 제외 시트 skip_sheets.csv (FR-028).

목차·요약 시트처럼 통합할 필요가 없는 시트를 이름으로 빼 둔다. 설정 사본에만 파일을 둔다.
"""

import unittest
from pathlib import Path

from openpyxl import Workbook

from tests.support import CONFIG, CliCase, audit_files, make_config, run_cli
from tests.test_header_survey import one, parse_report, run_survey

ROWS = [
    ["PMP01", "E01", "증상1", "원인1", "조치1", "베어링"],
    ["CNV01", "E02", "증상2", "원인2", "조치2", "모터"],
]
A_FULL_HEADER = ["설비코드", "에러코드", "증상", "원인", "조치내용", "부품분류"]


def write_book(path):
    """'인덱스', 'Index'(목차)와 양식 A 데이터 시트가 있는 파일."""
    wb = Workbook()
    index = wb.active
    index.title = "인덱스"
    index.append(["번호", "파일", "비고"])
    index.append([1, "LEAK-목차", "LEAK-비고"])
    other = wb.create_sheet("Index")
    other.append(["항목", "설명"])
    other.append(["LEAK-항목", "LEAK-설명"])
    data = wb.create_sheet("시트1")
    data.append(A_FULL_HEADER)
    for row in ROWS:
        data.append(row)
    wb.save(path)
    return Path(path)


def audit_lines(out):
    return audit_files(out)[0].read_text(encoding="utf-8").splitlines()


def value(lines, name):
    found = [line.split(": ", 1)[1] for line in lines if line.startswith(name + ": ")]
    if len(found) != 1:
        raise AssertionError("'%s' 줄이 하나가 아님: %d개" % (name, len(found)))
    return found[0]


class SkipSheetsTest(CliCase):
    def setUp(self):
        super().setUp()
        self.folder = self.tmp / "in"
        self.folder.mkdir()
        write_book(self.folder / "book.xlsx")
        self.config = make_config(self.tmp)
        (self.config / "skip_sheets.csv").write_text("시트\n 인덱스 \nINDEX\n", encoding="utf-8-sig")

    def test_without_file_nothing_changes(self):
        out = self.tmp / "base"
        result = run_cli([self.folder], CONFIG, out)
        self.assertEqual(result.returncode, 1, "목차 시트는 대응 규칙이 없어 종료 코드 1")
        lines = audit_lines(out)
        self.assertEqual(sum(1 for l in lines if l.startswith("대응 규칙 없음 시트: ")), 2)
        self.assertFalse(any(l.startswith("제외한 시트 수") for l in lines))

    def test_listed_sheets_are_skipped_in_merge(self):
        base = self.tmp / "base"
        run_cli([self.folder], CONFIG, base)
        out = self.tmp / "skip"
        result = run_cli([self.folder], self.config, out)
        self.assertEqual(result.returncode, 0, "stderr: " + result.stderr[-300:])
        lines = audit_lines(out)
        self.assertEqual(value(lines, "제외한 시트 수"), "2")
        self.assertFalse(any(l.startswith("대응 규칙 없음 시트: ") for l in lines))
        self.assertEqual(value(lines, "입력 행 수"), value(audit_lines(base), "입력 행 수"))
        self.assertEqual(value(lines, "출력 행 수"), "2")

    def test_listed_sheets_are_skipped_in_survey(self):
        result = run_survey([self.folder], self.config, self.out)
        self.assertEqual(result.returncode, 0, "stderr: " + result.stderr[-300:])
        text = sorted(Path(self.out).glob("survey_*.txt"))[0].read_text(encoding="utf-8")
        summary, sections = parse_report(text)
        self.assertEqual(one(summary, "제외한 시트 수"), "2")
        self.assertEqual(one(summary, "양식 수"), "1")
        self.assertEqual(one(summary, "새 양식 수"), "0")
        self.assertEqual(one(sections[1], "설정"), "기존 양식 A")


if __name__ == "__main__":
    unittest.main()
