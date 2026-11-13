"""T087: 컬럼 설정 창의 판단 로직 setup_config (FR-027).

화면(setup_gui)은 이 모듈의 함수만 부른다. 여기서는 화면 없이 함수를 직접 시험한다.
- scan(inputs, config_dir): 양식 목록(실제 헤더 이름, 파일 수, 새 양식 이름 '양식 N', 현재 대응 또는 추천)
- recommend(headers, output_columns, previous): 공백·대소문자만 다른 이름과 이전 대응만 추천
- validate(forms): (오류, 경고). 오류는 한 양식에서 같은 결과 컬럼 두 번, 경고는 설비·증상·원인·조치 대응 없음
- save(config_dir, forms, output_columns, stamp): 기존 파일을 <이름>_<시각>.csv로 보관하고 UTF-8 BOM으로 새로 쓴다
입력은 가짜 데이터와 임시 파일만 쓴다. 원본 config/는 건드리지 않는다.
"""

import contextlib
import io
import shutil
import sys
import unittest
from pathlib import Path

from tests.support import FAKE, SRC, CliCase, make_config, read_sheet, result_files, run_cli, write_xlsx

STANDARD = [(role, role) for role in ("설비", "일자", "증상", "원인", "조치", "분류")]
NEW_HEADER = ["일시", "호기", " 증상 ", "원인내용", "조치 내용", "구분", "LEAK-컬럼"]
NEW_ROW = ["2026-11-01", "LEAK-설비", "LEAK-증상", "LEAK-원인", "LEAK-조치", "LEAK-구분", "LEAK-값"]
A_HEADER = ["설비코드", "에러코드", "증상", "원인", "조치내용", "부품분류"]


class SetupConfigTest(CliCase):
    def setUp(self):
        super().setUp()
        try:
            if str(SRC) not in sys.path:
                sys.path.insert(0, str(SRC))
            from trouble_merge import setup_config
        except ImportError:
            self.fail("trouble_merge.setup_config 모듈이 없다")
        self.sc = setup_config
        self.folder = self.tmp / "in"
        self.folder.mkdir()
        shutil.copy(FAKE / "A_basic.xlsx", self.folder / "A_basic.xlsx")
        shutil.copy(FAKE / "B_basic.xlsx", self.folder / "B_basic.xlsx")
        write_xlsx(self.folder / "new_form.xlsx", NEW_HEADER, [NEW_ROW])
        self.config = make_config(self.tmp)
        self.stdout, self.stderr = io.StringIO(), io.StringIO()

    def scan(self):
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            return self.sc.scan([self.folder], self.config)

    def form(self, scan, name):
        found = [f for f in scan.forms if f.name == name]
        self.assertEqual(len(found), 1, "양식 %s가 하나가 아님" % name)
        return found[0]

    def test_scan_lists_existing_and_new_forms_with_real_headers(self):
        scan = self.scan()
        self.assertEqual(sorted(f.name for f in scan.forms), ["A", "B", "양식 1"])
        a = self.form(scan, "A")
        self.assertFalse(a.is_new)
        self.assertEqual(a.file_count, 1)
        self.assertEqual(a.headers, A_HEADER)
        self.assertEqual(a.mapping, {"설비코드": "설비", "에러코드": None, "증상": "증상",
                                     "원인": "원인", "조치내용": "조치", "부품분류": "분류"})
        new = self.form(scan, "양식 1")
        self.assertTrue(new.is_new)
        self.assertEqual(new.file_count, 1)
        self.assertEqual(new.header_row, 1)
        self.assertEqual(new.headers, [h.strip() for h in NEW_HEADER])
        self.assertEqual(scan.output_columns, STANDARD)

    def test_new_form_gets_only_safe_recommendations(self):
        scan = self.scan()
        new = self.form(scan, "양식 1")
        self.assertEqual(new.mapping["증상"], "증상", "앞뒤 공백만 다른 결과 컬럼 이름")
        self.assertIsNone(new.mapping["조치 내용"], "가운데 공백이 다르면 추천하지 않는다")
        self.assertIsNone(new.mapping["호기"])
        self.assertIsNone(new.mapping["원인내용"])

    def test_recommend_uses_case_and_previous_mapping_only(self):
        scan = self.scan()
        columns = STANDARD + [("Alarm", "추가")]
        got = self.sc.recommend(["설비코드", "고장원인", "조치 내용", "현상", "ALARM", "분류"],
                                columns, scan.previous)
        self.assertEqual(got, {"설비코드": "설비", "고장원인": "원인", "조치 내용": None,
                               "현상": None, "ALARM": "Alarm", "분류": "분류"})

    def test_validate_blocks_duplicates_and_warns_missing_required(self):
        errors, warnings = self.sc.validate([
            ("양식 1", {"일시": "일자", "호기": "설비", "증상": "증상", "원인내용": "원인",
                       "조치 내용": "조치", "구분": "설비"}),
        ])
        self.assertEqual(errors, [("양식 1", "설비", ["호기", "구분"])])
        self.assertEqual(warnings, [])
        errors, warnings = self.sc.validate([("양식 2", {"호기": "설비", "증상": "증상", "메모": None})])
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [("양식 2", ["원인", "조치"])])

    def saved_forms(self, scan):
        forms = []
        for f in scan.forms:
            mapping = dict(f.mapping)
            if f.is_new:
                mapping.update({"일시": "일자", "호기": "설비", "원인내용": "원인",
                                "조치 내용": "조치", "구분": "구분코드"})
            forms.append((f.name, f.header_row, None, mapping))
        return forms

    def test_save_backs_up_and_the_saved_settings_merge_the_new_form(self):
        scan = self.scan()
        old_map = (self.config / "column_map.csv").read_bytes()
        columns = STANDARD + [("구분코드", "추가")]
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            self.sc.save(self.config, self.saved_forms(scan), columns, "20261113_120000")
        self.assertEqual((self.config / "column_map_20261113_120000.csv").read_bytes(), old_map)
        for name in ("column_map.csv", "output_columns.csv"):
            data = (self.config / name).read_bytes()
            self.assertTrue(data.startswith(b"\xef\xbb\xbf"), name + "이 UTF-8 BOM이 아니다")
            self.assertNotIn("LEAK-".encode("utf-8"), data, name + "에 셀 값이 들어갔다")
        out = self.tmp / "out_saved"
        result = run_cli([self.folder], self.config, out)
        self.assertEqual(result.returncode, 0, "stderr: " + result.stderr[-300:])
        header, rows = read_sheet(result_files(out)[0])
        self.assertIn("구분코드", header)
        new_rows = [r for r in rows if r["원본 파일"] == "new_form.xlsx"]
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(new_rows[0]["구분코드"], "LEAK-구분")
        self.assertEqual(new_rows[0]["일자"], "2026-11-01")

    def test_save_refuses_duplicates_and_keeps_files(self):
        scan = self.scan()
        forms = self.saved_forms(scan)
        mapping = [f for f in forms if f[0] == "양식 1"][0][3]
        mapping["구분"] = "설비"
        before = (self.config / "column_map.csv").read_bytes()
        with self.assertRaises(self.sc.SaveError):
            self.sc.save(self.config, forms, STANDARD, "20261113_120001")
        self.assertEqual((self.config / "column_map.csv").read_bytes(), before)
        self.assertFalse((self.config / "output_columns.csv").exists())
        self.assertEqual(list(self.config.glob("column_map_*.csv")), [])

    def test_nothing_printed_with_cell_values(self):
        self.scan()
        for text in (self.stdout.getvalue(), self.stderr.getvalue()):
            self.assertNotIn("LEAK-", text)


if __name__ == "__main__":
    unittest.main()
