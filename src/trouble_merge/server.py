"""로컬 서버: 게시판과 HTML 설정 화면 (T099, FR-029). 표준 라이브러리 http.server만 쓴다.

    python -m trouble_merge.server --input <폴더...> --config <폴더> --out <폴더> [--port 3456] [--merge]

- 127.0.0.1에만 연다. Host 머리글이 127.0.0.1:<포트>나 localhost:<포트>가 아니면 거부한다(다른 사이트 이름으로 우회 방지).
- /api/는 머리글 X-Trouble-Merge: 1이 있어야 한다. 바꾸는 요청은 POST + application/json, 본문 1MB까지.
  다른 사이트의 페이지는 이 머리글을 붙여 보낼 수 없다(CORS 머리글을 내지 않으므로).
- 예시 값(셀 값)은 /api/scan 응답에만 담는다. 서버 로그는 요청 종류와 상태 코드만 낸다.
"""

import argparse
import json
import sys
import threading
import warnings
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import cli as merge_cli
from .board import build_board
from .mapping import EXTRA_ROLE, STANDARD_COLUMNS, ConfigError
from .setup_config import SaveError, save, scan, validate

PAGE = Path(__file__).with_name("setup_page.html")
MAX_BODY = 1024 * 1024
SAMPLE_COUNT = 3
API_HEADER = "X-Trouble-Merge"
CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
GUIDE = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>게시판 없음</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:60px auto;padding:0 16px;line-height:1.6}
a{color:#0a58ca}</style></head><body><h1>아직 통합 결과가 없습니다</h1>
<p><a href="/setup">설정 화면</a>에서 저장한 뒤 <b>통합하고 게시판 보기</b>를 누르거나,
<b>3_서버실행.bat</b>을 실행하세요.</p></body></html>"""


class App:
    def __init__(self, inputs, config, out):
        self.inputs = inputs
        self.config = config
        self.out = Path(out)
        self.lock = threading.Lock()

    def scan_json(self):
        result = scan(self.inputs, self.config, samples=SAMPLE_COUNT)
        return {
            "forms": [{
                "name": f.name, "is_new": f.is_new, "relation": f.relation, "file_count": f.file_count,
                "sheet_count": f.sheet_count, "sheets": f.sheets, "header_row": f.header_row, "sheet": f.sheet,
                "headers": f.headers, "samples": f.samples, "mapping": f.mapping,
            } for f in result.forms],
            "output_columns": [list(c) for c in result.output_columns],
            "skip_sheets": result.skip_sheets,
            "roles": list(STANDARD_COLUMNS),
            "skipped_files": len(result.skipped),
        }

    def save_json(self, body):
        """(상태 코드, 응답 사전). 검사에 걸리면 아무것도 쓰지 않는다."""
        try:
            forms = []
            for f in body["forms"]:
                if f.get("skip"):
                    continue
                mapping = {str(h): (None if k is None else str(k)) for h, k in dict(f["mapping"]).items()}
                forms.append((str(f["name"]).strip(), int(f.get("header_row") or 1), f.get("sheet") or None,
                              mapping))
            output_columns = [(str(name).strip(), str(role)) for name, role in body["output_columns"]]
            skip_sheets = [str(s) for s in body.get("skip_sheets", [])]
        except (KeyError, TypeError, ValueError):
            return 400, {"errors": [{"message": "요청 형식이 맞지 않습니다"}]}
        names = [name for name, _, _, _ in forms]
        if any(not n for n in names) or len(names) != len(set(names)):
            return 400, {"errors": [{"message": "양식 이름이 비었거나 겹칩니다"}]}
        errors, warnings_ = validate([(name, mapping) for name, _, _, mapping in forms])
        if errors:
            return 400, {"errors": [{"form": f, "key": k, "headers": h} for f, k, h in errors]}
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            with self.lock:
                save(self.config, forms, output_columns, stamp, skip_sheets)
        except SaveError as error:
            return 400, {"errors": [{"message": str(error)}]}
        return 200, {"ok": True, "warnings": [{"form": f, "missing": m} for f, m in warnings_]}

    def merge(self):
        """통합(FR-019)과 게시판을 out/run_<시각>에 만든다. 통합 종료 코드를 돌려준다."""
        with self.lock:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = self.out / ("run_" + stamp)
            code = merge_cli.main(["--input", *[str(p) for p in self.inputs], "--config", str(self.config),
                                   "--out", str(run_dir)])
            merged = run_dir / "merged.xlsx"
            if code < 2 and merged.exists():
                build_board(merged, run_dir, stamp)
            return code

    def latest_board(self):
        if not self.out.exists():
            return None
        runs = sorted((d for d in self.out.glob("run_*") if (d / "board.html").exists()),
                      key=lambda d: d.name, reverse=True)
        return runs[0] / "board.html" if runs else None


def make_handler(app, port):
    allowed_hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}

    class Handler(BaseHTTPRequestHandler):
        server_version = "trouble-merge"
        sys_version = ""

        # ---- 로그: 고정 문구만(경로·본문·예외 메시지를 내지 않는다) ----
        def log_request(self, code="-", size="-"):
            print("요청 %s %s" % (self.command, code), file=sys.stderr)

        def log_error(self, *args):
            print("요청 오류", file=sys.stderr)

        def log_message(self, *args):
            pass

        # ---- 응답 ----
        def send(self, status, body, ctype):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, status, obj):
            self.send(status, json.dumps(obj, ensure_ascii=False, default=str), "application/json; charset=utf-8")

        def refuse(self):
            self.send_json(403, {"error": "거부한 요청"})

        def host_ok(self):
            return self.headers.get("Host", "") in allowed_hosts

        def api_ok(self):
            return self.headers.get(API_HEADER) == "1"

        def route(self):
            return self.path.split("?", 1)[0]

        # ---- GET ----
        def do_GET(self):
            try:
                if not self.host_ok():
                    return self.refuse()
                path = self.route()
                if path == "/":
                    board = app.latest_board()
                    if board is None:
                        return self.send(200, GUIDE, "text/html; charset=utf-8")
                    return self.send(200, board.read_bytes(), "text/html; charset=utf-8")
                if path == "/setup":
                    return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
                if path == "/api/scan":
                    if not self.api_ok():
                        return self.refuse()
                    try:
                        return self.send_json(200, app.scan_json())
                    except ConfigError as error:
                        return self.send_json(400, {"errors": [{"message": "설정 오류: %s" % error}]})
                return self.send_json(404, {"error": "없는 주소"})
            except Exception:  # 메시지와 종류를 버리고 고정 문구만(셀 값이 섞일 수 있다)
                return self.send_json(500, {"error": "처리 중 오류"})

        # ---- POST ----
        def do_POST(self):
            try:
                if not self.host_ok() or not self.api_ok():
                    return self.refuse()
                if not self.headers.get("Content-Type", "").startswith("application/json"):
                    return self.send_json(415, {"error": "JSON만 받는다"})
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    return self.send_json(413, {"error": "본문이 너무 크다"})
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    return self.send_json(400, {"error": "JSON 형식 오류"})
                path = self.route()
                if path == "/api/save":
                    status, obj = app.save_json(body if isinstance(body, dict) else {})
                    return self.send_json(status, obj)
                if path == "/api/merge":
                    return self.send_json(200, {"exit_code": app.merge()})
                return self.send_json(404, {"error": "없는 주소"})
            except Exception:
                return self.send_json(500, {"error": "처리 중 오류"})

        def do_PUT(self):
            self.send_json(405, {"error": "쓰지 않는 방식"})

        do_DELETE = do_PATCH = do_OPTIONS = do_PUT

    return Handler


def build_parser():
    parser = argparse.ArgumentParser(prog="trouble_merge.server")
    parser.add_argument("--input", nargs="+", required=True, help="폴더 또는 파일")
    parser.add_argument("--config", required=True, help="설정 폴더(column_map.csv 등)")
    parser.add_argument("--out", required=True, help="통합 결과 폴더(run_<시각>을 만든다)")
    parser.add_argument("--port", type=int, default=3456, help="포트(0이면 빈 포트)")
    parser.add_argument("--merge", action="store_true", help="시작할 때 통합과 게시판을 만든다")
    return parser


def main(argv=None):
    warnings.simplefilter("ignore")
    args = build_parser().parse_args(argv)
    app = App(args.input, args.config, args.out)
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app, args.port))
    except OSError:
        print("서버를 열 수 없음: 포트를 이미 쓰고 있다", file=sys.stderr)
        return 2
    port = httpd.server_address[1]
    httpd.RequestHandlerClass = make_handler(app, port)
    if args.merge:
        try:
            code = app.merge()
            print("통합 종료 코드: %d" % code)
        except Exception:
            print("통합 중 예기치 못한 오류", file=sys.stderr)
    print("주소: http://127.0.0.1:%d/" % port, flush=True)
    print("설정 화면: http://127.0.0.1:%d/setup" % port, flush=True)
    print("끄려면 이 창을 닫거나 Ctrl+C", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
