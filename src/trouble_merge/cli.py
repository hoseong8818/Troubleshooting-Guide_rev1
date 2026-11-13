"""명령줄 진입점 (T023, T036, FR-019). 종료 코드: 0 정상, 1 일부 실패, 2 전부 실패 또는 설정 오류.

로그와 오류는 SafeLog 한 길로만 낸다. 예외는 메시지도 종류도 내지 않는다(셀 값이나 내부 이름이 섞일 수 있다).
"""

import argparse
import sys
import warnings
from datetime import datetime
from pathlib import Path

from .audit import Audit, write_check_list, write_name_map
from .check import default_date_range
from .dates import parse_bound
from .mapping import (
    ConfigError, detect_format, extra_names, header_name, is_skipped, load_config_formats,
    load_conversions, load_skip_sheets, skip_keys,
)
from .merge import convert_rows, mark_duplicates, sort_records
from .reader import (
    check_size_limits, exceeds_row_limit, is_readable_extension, list_inputs, read_workbook,
    read_workbook_excel,
)
from .safe_log import SafeLog
from .writer import write_workbook

# 입력 파일 방어 상한의 기본값(NFR-007). 데모용 값이며 실제 업무에서는 옵션으로 바꾼다.
DEFAULT_MAX_FILE_MB = 50
DEFAULT_MAX_UNZIPPED_MB = 200
DEFAULT_MAX_ROWS = 100000

UNMATCHED_TEXT = {
    "none": "대응 규칙 없음 시트",
    "ambiguous": "양식 모호 시트",
    "invalid": "대응 중복 양식 시트",
}


def date_bound(text):
    try:
        return parse_bound(text)
    except ValueError:
        raise argparse.ArgumentTypeError("YYYY-MM-DD 형식이어야 한다")


def build_parser():
    parser = argparse.ArgumentParser(prog="trouble_merge")
    parser.add_argument("--input", nargs="+", required=True, help="폴더 또는 파일")
    parser.add_argument("--config", required=True, help="column_map.csv, conversion_map.csv가 있는 폴더")
    parser.add_argument("--out", required=True, help="출력 폴더")
    parser.add_argument("--max-file-mb", type=float, default=DEFAULT_MAX_FILE_MB,
                        help="파일 크기 상한(MB). 넘는 파일은 건너뛴다")
    parser.add_argument("--max-unzipped-mb", type=float, default=DEFAULT_MAX_UNZIPPED_MB,
                        help="압축 해제 후 크기 상한(MB). 넘는 파일은 건너뛴다")
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS,
                        help="시트당 행 수 상한(헤더 포함). 넘는 파일은 건너뛴다")
    parser.add_argument("--min-date", type=date_bound, default=None,
                        help="이보다 이른 일자는 '확인 필요(일자 범위 밖)'. YYYY-MM-DD, 기본 2000-01-01")
    parser.add_argument("--max-date", type=date_bound, default=None,
                        help="이보다 늦은 일자는 '확인 필요(일자 범위 밖)'. YYYY-MM-DD, 기본 실행한 해의 12월 31일")
    parser.add_argument("--open-with", choices=("openpyxl", "excel"), default="openpyxl",
                        help="파일 여는 방법. excel은 설치된 엑셀을 조종한다(pywin32 필요)")
    parser.add_argument("--show-names", action="store_true",
                        help="로그·감사 결과에 실제 파일명·시트명을 낸다(기본은 마스킹)")
    return parser


def main(argv=None):
    warnings.simplefilter("ignore")  # 라이브러리 경고 문구에 값이 섞이지 않게 한다
    parser = build_parser()
    args = parser.parse_args(argv)
    low, high = default_date_range()
    args.date_range = (args.min_date or low, args.max_date or high)
    if args.date_range[0] > args.date_range[1]:
        parser.error("--min-date가 --max-date보다 늦다")
    try:
        return run(args)
    except Exception:  # 메시지와 종류를 모두 버리고 고정 문구만 낸다
        print("처리 중 예기치 못한 오류", file=sys.stderr)
        return 2


def skip_over_limit(audit, log, name, kind):
    """상한을 넘은 파일은 그 파일만 건너뛰고 사유 종류만 남긴다(NFR-007). 행은 입력 행 수에 넣지 않는다."""
    audit.failed_files.append(name)
    audit.limit_exceeded.append((name, kind))
    log.log("상한 초과(%s)" % kind, file=name)


def run(args):
    try:
        formats, output_columns = load_config_formats(args.config)
        extras = extra_names(output_columns)
        conversions = load_conversions(args.config)
        skip_names = load_skip_sheets(args.config)
    except ConfigError as error:
        print("설정 오류: %s" % error, file=sys.stderr)
        return 2

    if args.open_with == "excel":
        try:
            import win32com.client  # noqa: F401  엑셀 경로에만 필요하다
        except ImportError:
            print("설정 오류: --open-with excel 에는 pywin32가 필요하다", file=sys.stderr)
            return 2

    registered = {name for fmt in formats.values() for name in fmt.source_names()}
    log = SafeLog(registered, show_names=args.show_names)
    audit = Audit(log)
    skip = skip_keys(skip_names)
    if skip is not None:
        audit.excluded_sheets = 0

    files = list_inputs(args.input)
    for path in files:
        log.file_label(Path(path).name)  # 입력 순서대로 file_01, file_02 ... 번호를 정한다

    records = []
    unmatched_sheets = 0

    for path in files:
        name = Path(path).name
        if not is_readable_extension(path):
            audit.failed_files.append(name)
            log.log("건너뜀(지원하지 않는 형식)", file=name)
            continue
        kind = check_size_limits(path, args.max_file_mb, args.max_unzipped_mb)
        if kind is not None:
            skip_over_limit(audit, log, name, kind)
            continue
        try:
            reader = read_workbook_excel if args.open_with == "excel" else read_workbook
            sheets, hidden, formula_missing = reader(path)
        except Exception:  # 예외 종류·메시지 모두 버린다(내부 이름이나 셀 값이 섞일 수 있다)
            audit.failed_files.append(name)
            log.log("열기 실패", file=name)
            continue
        if exceeds_row_limit(sheets, args.max_rows):
            skip_over_limit(audit, log, name, "행 수")
            continue

        audit.hidden.append((name, hidden))
        audit.formula_missing += formula_missing
        if hidden:
            log.log("숨긴 시트 건너뜀", file=name, count=hidden)

        matched = False
        excluded_here = 0
        for sheet in sheets:
            if is_skipped(skip, sheet.name):  # 목차·요약 시트(FR-028): 읽지 않고 세기만 한다
                excluded_here += 1
                continue
            fmt, reason = detect_format(formats, sheet.grid, sheet.name)
            if fmt is None:
                unmatched_sheets += 1
                audit.unmatched.append((UNMATCHED_TEXT[reason], name, sheet.name))
                log.log(UNMATCHED_TEXT[reason], file=name, sheet=sheet.name)
                for position, value in enumerate(sheet.grid[0] if sheet.grid else []):
                    if header_name(value):
                        audit.add_unregistered(name, sheet.name, log.column_label(header_name(value), position))
                continue
            matched = True
            header = [header_name(v) for v in sheet.grid[fmt.header_row - 1]]
            for position, column in enumerate(header):
                if column and fmt.standard_of(column) is None:
                    audit.add_unregistered(name, sheet.name, log.column_label(column, position))

            rows = convert_rows(name, sheet, fmt, conversions, args.date_range, extras)
            audit.input_rows += len(rows)
            for record in rows:
                for standard in record.pop("_blank"):
                    source = fmt.source_of(standard)
                    position = header.index(source) if source in header else 0
                    audit.blank_required.append(
                        (name, sheet.name, record["원본 행"], log.column_label(source, position)))
            records.extend(rows)

        if excluded_here:
            audit.excluded_sheets += excluded_here
            log.log("제외한 시트", file=name, count=excluded_here)
        if matched:
            audit.files_read += 1
        elif excluded_here < len(sheets):
            audit.failed_files.append(name)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if audit.files_read == 0:
        # 통합 파일은 만들지 않지만, 어느 파일이 왜 빠졌는지는 감사 결과로 남긴다
        log.log("처리할 수 있는 파일이 없다")
        Path(args.out).mkdir(parents=True, exist_ok=True)
        audit.write(args.out, stamp)
        write_name_map(log, args.out, stamp)
        return 2

    mark_duplicates(records)
    records = sort_records(records)

    _, audit.prefixed = write_workbook(records, args.out, stamp, output_columns)
    audit.output_rows = len(records)
    audit.check_count = sum(1 for r in records if r["확인 필요 이유"] is not None)
    audit.duplicate_count = sum(1 for r in records if r["중복 의심"] is not None)
    audit.count_reasons(records)
    audit.write(args.out, stamp)
    write_check_list(log, records, args.out, stamp)
    write_name_map(log, args.out, stamp)

    print("완료: 출력 %d행" % len(records))
    return 1 if (audit.failed_files or unmatched_sheets) else 0


if __name__ == "__main__":
    sys.exit(main())
