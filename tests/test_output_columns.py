"""T082: 결과 컬럼 설정 output_columns.csv (FR-026).

설정 사본(make_config)에 output_columns.csv를 더해 쓴다. 원본 config/와 정답 파일은 건드리지 않는다.
비교 기준은 같은 입력을 output_columns.csv 없이 통합한 결과다.
"""

import unittest
from pathlib import Path

from openpyxl import load_workbook

from tests.support import (
    CONFIG, FAKE, CliCase, audit_files, make_config, read_sheet, result_files, run_cli,
)

ROLES = ["설비", "일자", "증상", "원인", "조치", "분류"]
FIXED = ["기타 항목", "확인 필요 이유", "원래 값", "중복 의심", "원본 파일", "원본 시트", "원본 행"]
INPUTS = [FAKE / "A_basic.xlsx", FAKE / "A_trap.xlsx", FAKE / "B_basic.xlsx"]
# (순서, 표시 이름, 역할). 파일에는 순서를 섞어 적는다.
RENAMED = [(4, "분류명", "분류"), (1, "호기", "설비"), (3, "현상", "증상"),
           (2, "발생일", "일자"), (5, "원인", "원인"), (6, "조치", "조치")]
RENAMED_HEADER = ["호기", "발생일", "현상", "분류명", "원인", "조치"]


def write_output_columns(config, rows):
    lines = ["순서,표시 이름,역할"] + ["%s,%s,%s" % row for row in rows]
    (Path(config) / "output_columns.csv").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def audit_value(out, name):
    text = audit_files(out)[0].read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(name + ": "):
            return line.split(": ", 1)[1]
    raise AssertionError("감사 결과에 '%s' 줄이 없음" % name)


class OutputColumnsTest(CliCase):
    def merged(self, inputs, config, name):
        out = self.tmp / name
        result = run_cli(inputs, config, out)
        self.assertEqual(result.returncode, 0, "stderr: " + result.stderr[-300:])
        files = result_files(out)
        self.assertEqual(len(files), 1)
        return out, files[0]

    def base(self, inputs=INPUTS):
        return self.merged(inputs, CONFIG, "base")

    def config_with(self, rows, column_map_extra=()):
        folder = self.tmp / ("cfg_%d" % len(list(self.tmp.glob("cfg_*"))))
        folder.mkdir()
        config = make_config(folder, column_map_extra=column_map_extra)
        write_output_columns(config, rows)
        return config

    def test_same_names_and_order_give_the_same_first_sheet(self):
        _, base = self.base()
        config = self.config_with([(i + 1, role, role) for i, role in enumerate(ROLES)])
        _, path = self.merged(INPUTS, config, "same")
        self.assertEqual(read_sheet(path), read_sheet(base))

    def test_renamed_and_reordered_columns_keep_values_by_role(self):
        _, base = self.base()
        config = self.config_with(RENAMED)
        _, path = self.merged(INPUTS, config, "renamed")
        base_header, base_rows = read_sheet(base)
        header, rows = read_sheet(path)
        self.assertEqual(header, RENAMED_HEADER + FIXED)
        self.assertEqual(len(rows), len(base_rows))
        names = {role: name for _, name, role in RENAMED}
        for index, (row, expect) in enumerate(zip(rows, base_rows), start=2):
            with self.subTest(행=index):
                for role in ROLES:
                    self.assertEqual(row[names[role]], expect[role], role)
                for column in FIXED:
                    self.assertEqual(row[column], expect[column], column)

    def test_role_sheet_is_written(self):
        config = self.config_with(RENAMED)
        _, path = self.merged(INPUTS, config, "roles")
        wb = load_workbook(path)
        self.assertEqual(wb.sheetnames[1], "컬럼 역할")
        rows = [tuple(r) for r in wb["컬럼 역할"].iter_rows(values_only=True)]
        self.assertEqual(rows[0], ("표시 이름", "역할"))
        self.assertEqual(rows[1:], [(name, role) for name, role in zip(
            RENAMED_HEADER, ["설비", "일자", "증상", "분류", "원인", "조치"])])

    def test_extra_column_takes_its_value_out_of_other_items(self):
        inputs = [FAKE / "A_basic.xlsx", FAKE / "B_basic.xlsx"]
        _, base = self.base(inputs)
        rows = [(i + 1, role, role) for i, role in enumerate(ROLES)] + [(7, "알람코드", "추가")]
        config = self.config_with(rows, column_map_extra=["A,에러코드,알람코드,,"])
        _, path = self.merged(inputs, config, "extra")
        _, base_rows = read_sheet(base)
        header, got = read_sheet(path)
        self.assertEqual(header, ROLES + ["알람코드"] + FIXED)
        self.assertEqual(len(got), len(base_rows))
        filled = 0
        for index, (row, expect) in enumerate(zip(got, base_rows), start=2):
            with self.subTest(행=index):
                other = expect["기타 항목"]
                if expect["원본 파일"] == "A_basic.xlsx" and other and other.startswith("에러코드: "):
                    self.assertEqual(row["알람코드"], other[len("에러코드: "):])
                    self.assertIsNone(row["기타 항목"])
                    filled += 1
                else:
                    self.assertIsNone(row["알람코드"])
                    self.assertEqual(row["기타 항목"], expect["기타 항목"])
                for role in ROLES:
                    self.assertEqual(row[role], expect[role], role)
        self.assertGreater(filled, 0, "알람코드에 값이 들어간 행이 없다")

    def test_row_counts_and_check_count_are_unchanged(self):
        base_out, _ = self.base()
        config = self.config_with(RENAMED)
        out, _ = self.merged(INPUTS, config, "counts")
        for name in ("입력 행 수", "출력 행 수", "행 수 일치", "확인 필요 건수", "중복 의심 건수"):
            self.assertEqual(audit_value(out, name), audit_value(base_out, name), name)

    def test_invalid_settings_exit_2_without_traceback(self):
        standard = [(i + 1, role, role) for i, role in enumerate(ROLES)]
        cases = {
            "판정 컬럼 누락": (standard[:5], ()),
            "판정 컬럼 중복": (standard + [(7, "설비2", "설비")], ()),
            "표시 이름 중복": (standard[:5] + [(6, "설비", "분류")], ()),
            "표시 이름 빈 칸": (standard[:5] + [(6, "", "분류")], ()),
            "고정 컬럼과 겹침": (standard + [(7, "원본 파일", "추가")], ()),
            "모르는 역할": (standard + [(7, "메모", "기타")], ()),
            "대응 표의 모르는 표준 컬럼": (standard, ["A,에러코드,알람코드,,"]),
        }
        for name, (rows, extra) in cases.items():
            with self.subTest(경우=name):
                config = self.config_with(rows, column_map_extra=extra)
                out = self.tmp / ("bad_%d" % len(list(self.tmp.glob("bad_*"))))
                result = run_cli(INPUTS, config, out)
                self.assertEqual(result.returncode, 2, name)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(result_files(out) if out.exists() else [], [])


if __name__ == "__main__":
    unittest.main()
