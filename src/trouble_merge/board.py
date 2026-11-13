"""통합 엑셀을 QnA 게시판 HTML 한 장으로 만든다 (T054, 데모).

화면 틀은 같은 폴더의 `board_page.html`에 있다(Apple 개발자 제품 페이지 형식: 고정 로컬 막대, 히어로,
요약 카드, 오류 현황, 사례 찾기, 글 보기). 이 모듈은 틀의 `__DATA__` 자리에 게시글 JSON을 넣는다.

외부 서비스·LLM 없이 브라우저 안에서만 검색한다(헌법 원칙 1). 게시글 데이터는 JSON으로 넣고
화면에는 textContent로만 그려서 셀 값이 코드로 실행되지 않게 한다. 외부 폰트·이미지·스크립트를 쓰지 않는다.
이미 있는 파일은 덮어쓰지 않는다.
사용: python -m trouble_merge.board --merged <통합 xlsx> --out <폴더>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from .mapping import ROLE_SHEET, STANDARD_COLUMNS
from .writer import unique_path

TEMPLATE = Path(__file__).with_name("board_page.html")


def read_posts(path):
    """통합 엑셀의 첫 시트를 게시글 목록(헤더 이름 -> 값)으로 읽는다. 빈 문자열은 None.

    '컬럼 역할' 시트가 있으면 판정 컬럼의 표시 이름을 역할 이름으로 바꿔 지금과 같은 화면을 만든다.
    """
    wb = load_workbook(path, data_only=True)
    try:
        rows = list(wb.worksheets[0].iter_rows(values_only=True))
        roles = {}
        if ROLE_SHEET in wb.sheetnames:  # 표시 이름을 바꾼 통합 엑셀(FR-026): 역할 이름으로 되돌린다
            for name, role in list(wb[ROLE_SHEET].iter_rows(values_only=True))[1:]:
                if role in STANDARD_COLUMNS:
                    roles[name] = role
    finally:
        wb.close()
    header = [roles.get(name, name) for name in rows[0]]
    return [
        dict(zip(header, [None if v == "" else v for v in row]))
        for row in rows[1:] if any(v is not None for v in row)
    ]


def to_json(posts):
    """</script>로 데이터 블록을 닫지 못하도록 <, >, &와 줄 구분자를 이스케이프한다."""
    raw = json.dumps(posts, ensure_ascii=False, default=str)
    for char, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                          (" ", "\\u2028"), (" ", "\\u2029")):
        raw = raw.replace(char, escaped)
    return raw


def build_board(merged, out_dir, stamp):
    posts = read_posts(merged)
    page = TEMPLATE.read_text(encoding="utf-8")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    path = unique_path(out_dir, "board", ".html", stamp)
    path.write_text(page.replace("__DATA__", to_json(posts), 1), encoding="utf-8")
    return path, len(posts)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="trouble_merge.board")
    parser.add_argument("--merged", required=True, help="통합 엑셀(merged.xlsx)")
    parser.add_argument("--out", required=True, help="게시판 HTML을 만들 폴더")
    args = parser.parse_args(argv)
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _, count = build_board(args.merged, args.out, stamp)
    except Exception:  # 메시지와 종류를 버리고 고정 문구만 낸다(셀 값이 섞일 수 있다)
        print("게시판을 만들 수 없음: 통합 엑셀을 열 수 없다", file=sys.stderr)
        return 2
    print("완료: 게시글 %d건" % count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
