"""T079: 헤더 조사 보고서의 '시트:' 줄 줄이기 (FR-025).

양식의 시트가 10개를 넘으면 앞 10개만 내고 끝에 ' 외 N개'를 붙인다. --max-sheet-list로 개수를 바꾸며 0이면 전부.
입력은 임시로 만든 같은 헤더의 파일만 쓴다.
"""

import re
import unittest
from pathlib import Path

from tests.support import CONFIG, CliCase, write_xlsx
from tests.test_header_survey import B_HEADER, one, parse_report, run_survey

SHEETS_LINE = re.compile(r"^(?P<items>.*?)(?: 외 (?P<rest>\d+)개)?$")


class SheetListTest(CliCase):
    def make_inputs(self, count):
        folder = self.tmp / "in"
        folder.mkdir()
        for number in range(1, count + 1):
            write_xlsx(folder / ("f%02d.xlsx" % number), B_HEADER, [["2026-11-01"] + ["x"] * 6])
        return folder

    def sheets_line(self, count, *extra):
        result = run_survey([self.make_inputs(count)], CONFIG, self.out, *extra)
        self.assertEqual(result.returncode, 0, "stderr: " + result.stderr[-300:])
        reports = sorted(Path(self.out).glob("survey_*.txt"))
        self.assertEqual(len(reports), 1)
        _, sections = parse_report(reports[0].read_text(encoding="utf-8"))
        self.assertEqual(sorted(sections), [1])
        self.assertEqual(one(sections[1], "시트 수"), str(count))
        found = SHEETS_LINE.match(one(sections[1], "시트"))
        items = found.group("items").split(", ")
        rest = found.group("rest")
        return items, None if rest is None else int(rest)

    def test_more_than_ten_sheets_are_cut_to_ten(self):
        items, rest = self.sheets_line(12)
        self.assertEqual(len(items), 10)
        self.assertEqual(items[0], "file_01 sheet_01")
        self.assertEqual(items[-1], "file_10 sheet_01")
        self.assertEqual(rest, 2)

    def test_ten_sheets_are_listed_without_suffix(self):
        items, rest = self.sheets_line(10)
        self.assertEqual(len(items), 10)
        self.assertIsNone(rest)

    def test_option_changes_the_count(self):
        items, rest = self.sheets_line(12, "--max-sheet-list", "3")
        self.assertEqual(items, ["file_01 sheet_01", "file_02 sheet_01", "file_03 sheet_01"])
        self.assertEqual(rest, 9)

    def test_zero_lists_all(self):
        items, rest = self.sheets_line(12, "--max-sheet-list", "0")
        self.assertEqual(len(items), 12)
        self.assertIsNone(rest)

    def test_bad_option_exits_2_without_traceback(self):
        folder = self.make_inputs(1)
        for value in ("-1", "abc"):
            result = run_survey([folder], CONFIG, self.tmp / ("out_" + value), "--max-sheet-list", value)
            self.assertEqual(result.returncode, 2, value)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(sorted((self.tmp / ("out_" + value)).glob("survey_*.txt")), [])


if __name__ == "__main__":
    unittest.main()
