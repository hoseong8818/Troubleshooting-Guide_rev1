"""컬럼 대응 표와 변환 표 읽기, 양식 판별 (T019)."""

import csv
from pathlib import Path

STANDARD_COLUMNS = ("설비", "일자", "증상", "원인", "조치", "분류")


UNKNOWN_CAUSE = "원인 미상"  # conversion_map.csv의 종류: 정보가 없는 원인 단어 목록(T059)


class ConfigError(Exception):
    """설정 파일 오류. 메시지에는 파일 이름과 줄 번호만 담는다(셀 값 금지)."""


def norm_key(value):
    """변환 표 비교용 키: 앞뒤 공백을 빼고 소문자로 바꾼다(FR-009, FR-018)."""
    return str(value).strip().lower()


def header_name(value):
    return "" if value is None else str(value).strip()


class Format:
    def __init__(self, name):
        self.name = name
        self.columns = []  # (원본 컬럼명, 표준 컬럼)
        self.header_row = 1
        self.sheet = None  # None이면 보이는 시트 전체
        self.invalid = False  # 한 표준 컬럼에 원본 컬럼이 여럿 대응되면 처리하지 않는다

    def source_names(self):
        return [source for source, _ in self.columns]

    def source_of(self, standard):
        for src, std in self.columns:
            if std == standard:
                return src
        return None

    def standard_of(self, source):
        for src, std in self.columns:
            if src == source:
                return std
        return None


FIXED_COLUMNS = ("기타 항목", "확인 필요 이유", "원래 값", "중복 의심", "원본 파일", "원본 시트", "원본 행")
EXTRA_ROLE = "추가"
OUTPUT_COLUMNS_FILE = "output_columns.csv"
ROLE_SHEET = "컬럼 역할"


def load_output_columns(config_dir):
    """output_columns.csv(FR-026)를 [(표시 이름, 역할)]로 순서대로 읽는다. 파일이 없으면 None.

    역할은 판정 컬럼(STANDARD_COLUMNS) 또는 '추가'. 판정 컬럼은 정확히 한 번씩 있어야 한다.
    표시 이름은 비어 있지 않고 서로 다르며 고정 컬럼과 겹치지 않는다. 추가 컬럼의 이름은
    판정 컬럼 이름과도 겹치지 않는다(column_map.csv의 '표준 컬럼' 칸에서 구분할 수 없으므로).
    """
    path = Path(config_dir) / OUTPUT_COLUMNS_FILE
    if not path.exists():
        return None
    entries = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row or not any(c.strip() for c in row):
                    continue
                row = [c.strip() for c in row] + [""] * 3
                order, name, role = row[:3]
                line = reader.line_num
                if not name:
                    raise ConfigError("%s %d줄: 표시 이름이 비어 있음" % (OUTPUT_COLUMNS_FILE, line))
                if role not in STANDARD_COLUMNS and role != EXTRA_ROLE:
                    raise ConfigError("%s %d줄: 역할이 아님" % (OUTPUT_COLUMNS_FILE, line))
                if name in FIXED_COLUMNS:
                    raise ConfigError("%s %d줄: 고정 컬럼과 같은 표시 이름" % (OUTPUT_COLUMNS_FILE, line))
                if role == EXTRA_ROLE and name in STANDARD_COLUMNS:
                    raise ConfigError("%s %d줄: 추가 컬럼 이름이 판정 컬럼과 같음" % (OUTPUT_COLUMNS_FILE, line))
                entries.append((int(order), line, name, role))
    except ValueError:
        raise ConfigError("%s 형식 오류(순서는 정수)" % OUTPUT_COLUMNS_FILE)
    names = [name for _, _, name, _ in entries]
    if len(names) != len(set(names)):
        raise ConfigError("%s: 표시 이름 중복" % OUTPUT_COLUMNS_FILE)
    roles = [role for _, _, _, role in entries if role != EXTRA_ROLE]
    if sorted(roles) != sorted(STANDARD_COLUMNS):
        raise ConfigError("%s: 판정 컬럼 6개가 한 번씩 있어야 함" % OUTPUT_COLUMNS_FILE)
    entries.sort(key=lambda e: (e[0], e[1]))
    return [(name, role) for _, _, name, role in entries]


SKIP_SHEETS_FILE = "skip_sheets.csv"


def load_skip_sheets(config_dir):
    """skip_sheets.csv(FR-028)의 시트 이름 목록(적힌 그대로, 앞뒤 공백만 뺌). 파일이 없으면 None."""
    path = Path(config_dir) / SKIP_SHEETS_FILE
    if not path.exists():
        return None
    names = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row and row[0].strip() and row[0].strip() not in names:
                names.append(row[0].strip())
    return names


def skip_keys(names):
    """시트 이름 비교용 키 집합(앞뒤 공백·대소문자 정리). names가 None이면 None."""
    return None if names is None else {norm_key(n) for n in names}


def is_skipped(keys, sheet_name):
    return keys is not None and norm_key(sheet_name) in keys


def extra_names(output_columns):
    return tuple(name for name, role in (output_columns or ()) if role == EXTRA_ROLE)


def load_config_formats(config_dir):
    """(양식 사전, output_columns 또는 None). 추가 컬럼 이름을 대응 표의 표준 컬럼으로 허용한다."""
    output_columns = load_output_columns(config_dir)
    return load_formats(config_dir, extra_names(output_columns)), output_columns


def load_formats(config_dir, extras=()):
    path = Path(config_dir) / "column_map.csv"
    formats = {}
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row or not any(c.strip() for c in row):
                    continue
                row = [c.strip() for c in row] + [""] * 5
                name, source, standard, header_row, sheet = row[:5]
                if standard not in STANDARD_COLUMNS and standard not in extras:
                    raise ConfigError("column_map.csv %d줄: 표준 컬럼이 아님" % reader.line_num)
                fmt = formats.setdefault(name, Format(name))
                fmt.columns.append((source, standard))
                if header_row:
                    fmt.header_row = int(header_row)
                if sheet:
                    fmt.sheet = sheet
    except FileNotFoundError:
        raise ConfigError("column_map.csv 없음")
    except ValueError:
        raise ConfigError("column_map.csv 형식 오류")
    for fmt in formats.values():
        standards = [std for _, std in fmt.columns]
        if len(standards) != len(set(standards)):
            fmt.invalid = True
    return formats


def load_conversions(config_dir):
    """{'설비': {키: 표준 값}, '분류': {키: 표준 값}, '원인 미상': {키: ''}}.

    같은 키가 표준 값을 달리하면 ConfigError. '원인 미상'은 단어 목록이라 표준 값을 비워 둔다(T059).
    """
    path = Path(config_dir) / "conversion_map.csv"
    tables = {"설비": {}, "분류": {}, UNKNOWN_CAUSE: {}}
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row or not any(c.strip() for c in row):
                    continue
                row = [c.strip() for c in row] + [""] * 3
                kind, original, standard = row[:3]
                if kind not in tables:
                    raise ConfigError("conversion_map.csv %d줄: 종류가 아님" % reader.line_num)
                key = norm_key(original)
                if key in tables[kind] and tables[kind][key] != standard:
                    raise ConfigError("conversion_map.csv %d줄: 같은 키에 다른 표준 값" % reader.line_num)
                tables[kind][key] = standard
    except FileNotFoundError:
        raise ConfigError("conversion_map.csv 없음")
    return tables


def detect_format(formats, grid, sheet_name):
    """헤더로 양식을 판별한다(FR-017). (양식 또는 None, 사유)를 돌려준다.

    사유: 'ok', 'none'(대응 규칙 없음), 'ambiguous'(양식 모호), 'invalid'(대응 중복)
    """
    best = []
    best_size = -1
    for fmt in formats.values():
        if fmt.sheet is not None and fmt.sheet != sheet_name:
            continue
        if len(grid) < fmt.header_row:
            continue
        header = {header_name(v) for v in grid[fmt.header_row - 1]}
        names = fmt.source_names()
        if not names or not all(n in header for n in names):
            continue
        size = len(names)
        if size > best_size:
            best, best_size = [fmt], size
        elif size == best_size:
            best.append(fmt)
    if not best:
        return None, "none"
    if len(best) > 1:
        return None, "ambiguous"
    if best[0].invalid:
        return None, "invalid"
    return best[0], "ok"
