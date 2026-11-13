"""헤더 조사 보고서 (T076, FR-025). 종료 코드: 0 정상, 1 건너뛴 파일 있음, 2 읽은 파일 없음 또는 설정 오류.

입력 폴더의 `.xlsx`에서 보이는 시트의 헤더 행만 읽어(데이터 행은 읽지 않는다) 양식별로 묶고,
현재 컬럼 대응 표와 비교한 결과를 `survey_<실행 시각>.txt`로 낸다. 통합 파일은 만들지 않는다.
보고서와 로그에는 셀 값을 넣지 않고, 이름 표시는 SafeLog 규칙(NFR-009)을 그대로 따른다.

    python -m trouble_merge.survey --input <폴더 또는 파일...> --config <폴더> --out <폴더> [--show-names]
"""

import argparse
import sys
import warnings
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from .audit import write_name_map
from .cli import DEFAULT_MAX_FILE_MB, DEFAULT_MAX_UNZIPPED_MB
from .mapping import ConfigError, detect_format, header_name, load_formats
from .reader import check_size_limits, is_readable_extension, list_inputs
from .safe_log import SafeLog
from .writer import unique_path

RELATION_TEXT = {
    "none": "새 양식",
    "ambiguous": "양식 모호",
    "invalid": "대응 중복",
}


def build_parser():
    parser = argparse.ArgumentParser(prog="trouble_merge.survey")
    parser.add_argument("--input", nargs="+", required=True, help="폴더 또는 파일")
    parser.add_argument("--config", required=True, help="column_map.csv가 있는 폴더")
    parser.add_argument("--out", required=True, help="보고서를 쓸 폴더")
    parser.add_argument("--max-file-mb", type=float, default=DEFAULT_MAX_FILE_MB,
                        help="파일 크기 상한(MB). 넘는 파일은 건너뛴다")
    parser.add_argument("--max-unzipped-mb", type=float, default=DEFAULT_MAX_UNZIPPED_MB,
                        help="압축 해제 후 크기 상한(MB). 넘는 파일은 건너뛴다")
    parser.add_argument("--show-names", action="store_true",
                        help="보고서·로그에 실제 파일명·시트명을 낸다(기본은 마스킹)")
    parser.add_argument("--max-sheet-list", type=sheet_list_count, default=DEFAULT_MAX_SHEET_LIST,
                        help="양식마다 '시트:' 줄에 낼 시트 수. 넘으면 ' 외 N개'. 0이면 전부")
    return parser


DEFAULT_MAX_SHEET_LIST = 10


def sheet_list_count(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("0 이상의 정수여야 한다")
    if value < 0:
        raise argparse.ArgumentTypeError("0 이상의 정수여야 한다")
    return value


def sheet_list(labels, limit):
    """앞 limit개만 쉼표로 잇고, 넘으면 ' 외 N개'를 붙인다. limit이 0이면 전부."""
    if limit == 0 or len(labels) <= limit:
        return ", ".join(labels)
    return "%s 외 %d개" % (", ".join(labels[:limit]), len(labels) - limit)


def main(argv=None):
    warnings.simplefilter("ignore")  # 라이브러리 경고 문구에 값이 섞이지 않게 한다
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception:  # 메시지와 종류를 모두 버리고 고정 문구만 낸다
        print("처리 중 예기치 못한 오류", file=sys.stderr)
        return 2


def read_headers(path, rows):
    """보이는 시트마다 (시트 이름, 위쪽 rows행)을, 그리고 숨긴 시트 수를 돌려준다.

    read_only로 열어 위쪽 몇 행만 읽는다. 데이터 행은 읽지 않으며, 병합 칸은 채우지 않는다.
    """
    wb = load_workbook(path, read_only=True, data_only=True)
    sheets = []
    hidden = 0
    try:
        for ws in wb.worksheets:
            if ws.sheet_state != "visible":
                hidden += 1
                continue
            grid = [list(r) for r in ws.iter_rows(min_row=1, max_row=rows, values_only=True)]
            sheets.append((ws.title, grid))
    finally:
        wb.close()
    return sheets, hidden


class Group:
    def __init__(self, names, relation, columns, order):
        self.names = names          # 빈 칸을 뺀 헤더 이름의 집합
        self.relation = relation    # 보고서의 '설정' 값
        self.columns = columns      # 첫 시트 기준의 컬럼 표시(SafeLog.column_label)
        self.order = order          # 처음 나온 순서
        self.files = []
        self.sheets = []            # (파일명, 시트명)

    def add(self, file, sheet):
        if file not in self.files:
            self.files.append(file)
        self.sheets.append((file, sheet))


def nearest_group(group, groups):
    """이름 목록의 대칭 차집합이 가장 작은 다른 양식(같으면 앞 번호). 없으면 None."""
    best = None
    for number, other in enumerate(groups, start=1):
        if other is group:
            continue
        diff = len(group.names ^ other.names)
        if best is None or diff < best[1]:
            best = (number, diff)
    return best


def nearest_format(group, formats):
    """등록 컬럼이 가장 많이 들어 있는 기존 양식과 빠진 등록 컬럼 수. 하나도 없으면 None."""
    best = None
    for fmt in formats.values():
        names = set(fmt.source_names())
        present = len(names & group.names)
        if present and (best is None or present > best[1]):
            best = (fmt.name, present, len(names) - present)
    return None if best is None else (best[0], best[2])


def run(args):
    try:
        formats = load_formats(args.config)
    except ConfigError as error:
        print("설정 오류: %s" % error, file=sys.stderr)
        return 2

    registered = {name for fmt in formats.values() for name in fmt.source_names()}
    log = SafeLog(registered, show_names=args.show_names)
    top_rows = max([fmt.header_row for fmt in formats.values()] + [1])

    files = list_inputs(args.input)
    for path in files:
        log.file_label(Path(path).name)  # 입력 순서대로 file_01, file_02 ... 번호를 정한다

    skipped = []  # (파일명, 사유 문구)
    files_read = 0
    hidden_total = 0
    headerless = 0
    groups = {}

    for path in files:
        name = Path(path).name
        if not is_readable_extension(path):
            skipped.append((name, "지원하지 않는 형식"))
            log.log("건너뜀(지원하지 않는 형식)", file=name)
            continue
        kind = check_size_limits(path, args.max_file_mb, args.max_unzipped_mb)
        if kind is not None:
            skipped.append((name, "상한 초과(%s)" % kind))
            log.log("상한 초과(%s)" % kind, file=name)
            continue
        try:
            sheets, hidden = read_headers(path, top_rows)
        except Exception:  # 예외 종류·메시지 모두 버린다(내부 이름이나 셀 값이 섞일 수 있다)
            skipped.append((name, "열기 실패"))
            log.log("열기 실패", file=name)
            continue
        files_read += 1
        hidden_total += hidden

        for sheet_name, grid in sheets:
            fmt, reason = detect_format(formats, grid, sheet_name)
            header_row = fmt.header_row if fmt is not None else 1
            header = grid[header_row - 1] if len(grid) >= header_row else []
            cells = [(pos, header_name(v)) for pos, v in enumerate(header) if header_name(v)]
            if not cells:
                headerless += 1
                continue
            relation = "기존 양식 %s" % fmt.name if fmt is not None else RELATION_TEXT[reason]
            names = frozenset(n for _, n in cells)
            key = (names, relation)
            group = groups.get(key)
            if group is None:
                columns = [log.column_label(n, pos) for pos, n in cells]
                group = groups[key] = Group(names, relation, columns, len(groups))
            group.add(name, sheet_name)

    ordered = sorted(groups.values(), key=lambda g: (-len(g.sheets), g.order))
    lines = render(log, formats, ordered, len(files), files_read, skipped, hidden_total, headerless,
                   args.max_sheet_list)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path(args.out).mkdir(parents=True, exist_ok=True)
    report = unique_path(args.out, "survey_" + stamp, ".txt", stamp)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_name_map(log, args.out, stamp)

    new_forms = sum(1 for g in ordered if g.relation == RELATION_TEXT["none"])
    print("완료: 양식 %d개, 새 양식 %d개, 보고서 %s" % (len(ordered), new_forms, report.name))
    if files_read == 0:
        log.log("읽은 파일이 없다")
        return 2
    return 1 if skipped else 0


def render(log, formats, groups, total, files_read, skipped, hidden, headerless, max_list):
    new_forms = sum(1 for g in groups if g.relation == RELATION_TEXT["none"])
    lines = [
        "헤더 조사 보고서",
        "조사한 파일 수: %d" % total,
        "읽은 파일 수: %d" % files_read,
    ]
    if skipped:
        lines += ["건너뛴 파일: %s %s" % (log.file_label(name), why) for name, why in skipped]
    else:
        lines.append("건너뛴 파일: 없음")
    lines += [
        "숨긴 시트 수: %d" % hidden,
        "헤더 없는 시트 수: %d" % headerless,
        "양식 수: %d" % len(groups),
        "새 양식 수: %d" % new_forms,
    ]
    for number, group in enumerate(groups, start=1):
        lines += [
            "",
            "양식 %d" % number,
            "설정: %s" % group.relation,
            "파일 수: %d" % len(group.files),
            "시트 수: %d" % len(group.sheets),
            "컬럼 수: %d" % len(group.columns),
            "컬럼: %s" % ", ".join(group.columns),
            "시트: %s" % sheet_list(
                ["%s %s" % (log.file_label(f), log.sheet_label(s)) for f, s in group.sheets], max_list),
        ]
        near = nearest_group(group, groups)
        lines.append("가장 가까운 양식: %s" % (
            "없음" if near is None else "양식 %d (컬럼 %d개 차이)" % near))
        if group.relation == RELATION_TEXT["none"]:
            existing = nearest_format(group, formats)
            lines.append("가장 가까운 기존 양식: %s" % (
                "없음" if existing is None else "%s (빠진 등록 컬럼 %d개)" % existing))
    return lines


if __name__ == "__main__":
    sys.exit(main())
