"""T095: 로컬 서버와 HTML 설정 화면 (FR-029).

`python -m trouble_merge.server --port 0`을 임시 입력·설정·출력 폴더로 띄워 HTTP로 시험한다.
API는 머리글 X-Trouble-Merge: 1이 있어야 하고, Host가 127.0.0.1/localhost가 아니면 거부한다.
예시 값은 API 응답(화면)에만 있고 서버의 stdout·stderr와 저장한 CSV에는 없어야 한다.
"""

import http.client
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import unittest

from tests.support import FAKE, ROOT, SRC, CliCase, make_config, write_xlsx

NEW_HEADER = ["일시", "호기", "현상", "원인내용", "대책", "구분"]
NEW_ROWS = [["2026-11-0%d" % i, "LEAK-호기%d" % i, "LEAK-현상%d" % i, "LEAK-원인%d" % i,
             "LEAK-대책%d" % i, "LEAK-구분%d" % i] for i in range(1, 5)]
NEW_MAPPING = {"일시": "일자", "호기": "설비", "현상": "증상", "원인내용": "원인", "대책": "조치", "구분": "분류"}
STANDARD = [[role, role] for role in ("설비", "일자", "증상", "원인", "조치", "분류")]
API = {"X-Trouble-Merge": "1", "Content-Type": "application/json"}
EXTERNAL = re.compile(r"https?://|<script[^>]+src=|<link\b", re.IGNORECASE)
DATA_RE = re.compile(r'<script[^>]*id="board-data"[^>]*>(.*?)</script>', re.DOTALL)


class Server:
    def __init__(self, folder, config, out):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [sys.executable, "-u", "-m", "trouble_merge.server", "--input", str(folder),
               "--config", str(config), "--out", str(out), "--port", "0"]
        self.proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        self.lines = queue.Queue()
        self.stdout, self.stderr = [], []
        threading.Thread(target=self._pump, args=(self.proc.stdout, self.stdout, True), daemon=True).start()
        threading.Thread(target=self._pump, args=(self.proc.stderr, self.stderr, False), daemon=True).start()
        self.port = None
        try:
            while self.port is None:
                found = re.search(r"주소: http://127\.0\.0\.1:(\d+)/", self.lines.get(timeout=30))
                if found:
                    self.port = int(found.group(1))
        except queue.Empty:
            self.stop()
            raise AssertionError("서버가 주소 줄을 내지 않았다")

    def _pump(self, stream, store, notify):
        for line in stream:
            store.append(line)
            if notify:
                self.lines.put(line)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        try:
            data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
            conn.request(method, path, body=data, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.getheader("Content-Type") or "", response.read().decode("utf-8")
        finally:
            conn.close()

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        return "".join(self.stdout) + "".join(self.stderr)


class WebServerTest(CliCase):
    def setUp(self):
        super().setUp()
        self.folder = self.tmp / "in"
        self.folder.mkdir()
        shutil.copy(FAKE / "A_basic.xlsx", self.folder / "A_basic.xlsx")
        shutil.copy(FAKE / "B_basic.xlsx", self.folder / "B_basic.xlsx")
        write_xlsx(self.folder / "new_form.xlsx", NEW_HEADER, NEW_ROWS)
        self.config = make_config(self.tmp)
        self.server = Server(self.folder, self.config, self.out)
        self.addCleanup(self.server.stop)

    def scan(self):
        status, kind, body = self.server.request("GET", "/api/scan", headers=API)
        self.assertEqual(status, 200, body[-300:])
        self.assertIn("application/json", kind)
        return json.loads(body)

    def new_form(self, scan):
        found = [f for f in scan["forms"] if f["is_new"]]
        self.assertEqual(len(found), 1)
        return found[0]

    def save_body(self, scan, mapping, skip_sheets=()):
        forms = []
        for form in scan["forms"]:
            forms.append({"name": form["name"], "header_row": form["header_row"], "sheet": form["sheet"],
                          "skip": False, "mapping": mapping if form["is_new"] else form["mapping"]})
        return {"forms": forms, "output_columns": STANDARD, "skip_sheets": list(skip_sheets)}

    def test_scan_shows_forms_headers_and_three_sample_values(self):
        scan = self.scan()
        names = sorted(f["name"] for f in scan["forms"])
        self.assertEqual(names, ["A", "B", "양식 1"])
        new = self.new_form(scan)
        self.assertEqual(new["headers"], NEW_HEADER)
        self.assertEqual(new["file_count"], 1)
        self.assertEqual(new["sheets"], ["시트1"])
        self.assertEqual(new["samples"]["호기"], ["LEAK-호기1", "LEAK-호기2", "LEAK-호기3"])
        self.assertEqual(scan["output_columns"], STANDARD)

    def test_pages_have_no_external_addresses(self):
        for path in ("/setup", "/"):
            status, kind, body = self.server.request("GET", path)
            self.assertEqual(status, 200, path)
            self.assertIn("text/html", kind, path)
            self.assertIsNone(EXTERNAL.search(body), path + "에 외부 주소가 있다")

    def test_requests_without_header_or_with_other_host_are_refused(self):
        status, _, _ = self.server.request("GET", "/api/scan")
        self.assertEqual(status, 403, "머리글 없는 API 요청")
        status, _, _ = self.server.request("POST", "/api/save", body={}, headers={"Content-Type": "application/json"})
        self.assertEqual(status, 403, "머리글 없는 저장 요청")
        bad_host = dict(API, Host="evil.example:%d" % self.server.port)
        status, _, _ = self.server.request("GET", "/api/scan", headers=bad_host)
        self.assertEqual(status, 403, "다른 Host")
        status, _, _ = self.server.request("GET", "/setup", headers={"Host": "evil.example"})
        self.assertEqual(status, 403, "다른 Host의 화면 요청")
        self.assertFalse((self.config / "output_columns.csv").exists())

    def test_save_rejects_duplicates_without_writing(self):
        scan = self.scan()
        before = (self.config / "column_map.csv").read_bytes()
        bad = dict(NEW_MAPPING, 구분="설비")
        status, _, body = self.server.request("POST", "/api/save", self.save_body(scan, bad), API)
        self.assertEqual(status, 400, body[-300:])
        self.assertIn("errors", json.loads(body))
        self.assertEqual((self.config / "column_map.csv").read_bytes(), before)

    def test_save_then_merge_shows_the_board(self):
        scan = self.scan()
        status, _, body = self.server.request(
            "POST", "/api/save", self.save_body(scan, NEW_MAPPING, ["인덱스"]), API)
        self.assertEqual(status, 200, body[-300:])
        column_map = (self.config / "column_map.csv").read_text(encoding="utf-8-sig")
        self.assertIn("양식 1,호기,설비", column_map)
        self.assertIn("인덱스", (self.config / "skip_sheets.csv").read_text(encoding="utf-8-sig"))
        for name in ("column_map.csv", "output_columns.csv", "skip_sheets.csv"):
            self.assertNotIn("LEAK-", (self.config / name).read_text(encoding="utf-8-sig"), name)
        status, _, body = self.server.request("POST", "/api/merge", {}, API)
        self.assertEqual(status, 200, body[-300:])
        self.assertIn(json.loads(body)["exit_code"], (0, 1))
        status, _, page = self.server.request("GET", "/")
        self.assertEqual(status, 200)
        found = DATA_RE.search(page)
        self.assertIsNotNone(found, "게시판 데이터가 없다")
        posts = json.loads(found.group(1))
        self.assertEqual(sum(1 for p in posts if p["원본 파일"] == "new_form.xlsx"), 4)

    def test_server_output_has_no_cell_values(self):
        scan = self.scan()
        self.server.request("POST", "/api/save", self.save_body(scan, NEW_MAPPING), API)
        self.server.request("POST", "/api/merge", {}, API)
        self.server.request("GET", "/")
        output = self.server.stop()
        self.assertNotIn("LEAK-", output)
        self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
