"""컬럼 설정 창의 판단 로직 (T089, FR-027). 화면(setup_gui)은 이 모듈의 함수만 부른다.

- scan: 입력의 헤더 행만 읽어 양식 목록을 만든다(FR-025와 같은 방법, 셀 값은 읽지 않는다).
- recommend: 앞뒤 공백·대소문자만 다른 이름과 이전에 저장한 대응만 추천한다. 그 밖의 비슷한 이름은 묶지 않는다.
- validate: 한 양식에서 같은 결과 컬럼을 두 번 쓰면 오류, 설비·증상·원인·조치 대응이 없으면 경고.
- save: 기존 파일을 <이름>_<시각>.csv로 옮겨 보관하고 column_map.csv, output_columns.csv를 UTF-8 BOM으로 쓴다.

대응 값(키)은 판정 컬럼이면 역할 이름(설비 등), 추가 컬럼이면 그 표시 이름이다. None은 '기타 항목'.
이 모듈은 아무것도 출력하지 않는다. 헤더 이름은 화면과 설정 파일에만 쓰인다.
"""

import csv
from pathlib import Path

from .cli import DEFAULT_MAX_FILE_MB, DEFAULT_MAX_UNZIPPED_MB
from .mapping import (
    EXTRA_ROLE, OUTPUT_COLUMNS_FILE, STANDARD_COLUMNS, load_config_formats, norm_key,
)
from .merge import REQUIRED_STANDARD
from .reader import list_inputs
from .survey import collect
from .writer import unique_path

COLUMN_MAP_FILE = "column_map.csv"
COLUMN_MAP_HEADER = ["양식", "원본 컬럼명", "표준 컬럼", "헤더행", "시트"]
OUTPUT_COLUMNS_HEADER = ["순서", "표시 이름", "역할"]
NEW_FORM = "양식 %d"


class SaveError(Exception):
    """저장할 수 없는 설정. 메시지에는 양식 이름과 결과 컬럼 이름만 담는다."""


class FormInfo:
    def __init__(self, name, is_new, relation, header_row, sheet):
        self.name = name
        self.is_new = is_new
        self.relation = relation    # '기존 양식 A', '새 양식', '양식 모호', '대응 중복'
        self.header_row = header_row
        self.sheet = sheet          # 기존 양식의 시트 지정(없으면 None)
        self.headers = []           # 실제 헤더 이름(처음 나온 순서, 중복 없음)
        self.files = set()
        self.sheet_count = 0
        self.mapping = {}           # 헤더 이름 -> 키 또는 None

    @property
    def file_count(self):
        return len(self.files)

    def add_headers(self, names):
        for name in names:
            if name not in self.headers:
                self.headers.append(name)


class Scan:
    def __init__(self, forms, output_columns, previous, skipped):
        self.forms = forms
        self.output_columns = output_columns    # [(표시 이름, 역할)]
        self.previous = previous                # 정리한 원본 컬럼명 -> 키(이전에 저장한 대응)
        self.skipped = skipped                  # (파일명, 사유)


def default_output_columns():
    return [(role, role) for role in STANDARD_COLUMNS]


def scan(inputs, config_dir, max_file_mb=DEFAULT_MAX_FILE_MB, max_unzipped_mb=DEFAULT_MAX_UNZIPPED_MB):
    """양식 목록. 설정 폴더에 column_map.csv가 없으면 빈 설정으로 본다. 설정 오류는 ConfigError."""
    config_dir = Path(config_dir)
    if (config_dir / COLUMN_MAP_FILE).exists():
        formats, output_columns = load_config_formats(config_dir)
    else:
        formats, output_columns = {}, None
    output_columns = output_columns or default_output_columns()

    previous = {}
    for fmt in formats.values():
        for source, standard in fmt.columns:
            previous.setdefault(norm_key(source), standard)

    found = collect(list_inputs(inputs), formats, max_file_mb, max_unzipped_mb)
    forms = []
    by_format = {}
    used = set(formats)
    number = 0
    for group in found.groups:
        names = [n for _, n in group.cells]
        if group.fmt is not None:
            form = by_format.get(group.fmt.name)
            if form is None:
                form = by_format[group.fmt.name] = FormInfo(
                    group.fmt.name, False, group.relation, group.fmt.header_row, group.fmt.sheet)
                forms.append(form)
        else:
            number += 1
            while NEW_FORM % number in used:
                number += 1
            used.add(NEW_FORM % number)
            form = FormInfo(NEW_FORM % number, True, group.relation, group.header_row, None)
            forms.append(form)
        form.add_headers(names)
        form.files.update(f for f, _ in group.sheets)
        form.sheet_count += len(group.sheets)

    for fmt in formats.values():  # 입력에 없는 기존 양식도 지우지 않도록 목록에 남긴다
        if fmt.name not in by_format:
            form = by_format[fmt.name] = FormInfo(fmt.name, False, "기존 양식 %s" % fmt.name,
                                                  fmt.header_row, fmt.sheet)
            form.add_headers(fmt.source_names())
            forms.append(form)

    for form in forms:
        if form.is_new:
            form.mapping = recommend(form.headers, output_columns, previous)
        else:
            fmt = formats[form.name]
            form.mapping = {h: fmt.standard_of(h) for h in form.headers}
    return Scan(forms, output_columns, previous, found.skipped)


def keys_of(output_columns):
    """대응에 쓸 수 있는 키: 판정 컬럼 역할 이름과 추가 컬럼 표시 이름."""
    return [name if role == EXTRA_ROLE else role for name, role in output_columns]


def recommend(headers, output_columns, previous):
    """헤더 이름마다 추천 키 또는 None. 정리(앞뒤 공백·대소문자)한 이름이 정확히 같을 때만 추천한다."""
    allowed = set(keys_of(output_columns))
    by_name = {}
    for name, role in output_columns:
        key = name if role == EXTRA_ROLE else role
        by_name.setdefault(norm_key(name), key)
        if role != EXTRA_ROLE:
            by_name.setdefault(norm_key(role), key)
    result = {}
    for header in headers:
        nk = norm_key(header)
        key = previous.get(nk)
        if key not in allowed:
            key = by_name.get(nk)
        result[header] = key
    return result


def validate(forms):
    """forms: [(양식 이름, {헤더: 키 또는 None})]. (오류, 경고)를 돌려준다.

    오류: (양식, 키, [겹치는 헤더들]) — 저장 불가. 경고: (양식, [대응 없는 필수 역할]) — 확인 후 저장 가능.
    """
    errors, warnings = [], []
    for name, mapping in forms:
        by_key = {}
        for header, key in mapping.items():
            if key is not None:
                by_key.setdefault(key, []).append(header)
        for key, headers in by_key.items():
            if len(headers) > 1:
                errors.append((name, key, headers))
        missing = [role for role in REQUIRED_STANDARD if role not in by_key]
        if missing:
            warnings.append((name, missing))
    return errors, warnings


def check_output_columns(output_columns):
    names = [name for name, _ in output_columns]
    roles = [role for _, role in output_columns if role != EXTRA_ROLE]
    if any(not name.strip() for name in names) or len(names) != len(set(names)):
        raise SaveError("결과 컬럼 표시 이름이 비었거나 겹친다")
    if sorted(roles) != sorted(STANDARD_COLUMNS):
        raise SaveError("판정 컬럼 6개가 한 번씩 있어야 한다")


def save(config_dir, forms, output_columns, stamp):
    """forms: [(양식 이름, 헤더행, 시트 또는 None, {헤더: 키 또는 None})]. 검사를 통과해야 쓴다."""
    check_output_columns(output_columns)
    errors, _ = validate([(name, mapping) for name, _, _, mapping in forms])
    if errors:
        raise SaveError("한 양식에서 같은 결과 컬럼을 두 번 지정했다")
    allowed = set(keys_of(output_columns))
    for _, _, _, mapping in forms:
        if any(key is not None and key not in allowed for key in mapping.values()):
            raise SaveError("결과 컬럼에 없는 대응이 있다")

    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    for file_name in (COLUMN_MAP_FILE, OUTPUT_COLUMNS_FILE):
        path = config_dir / file_name
        if path.exists():
            stem = Path(file_name).stem
            path.replace(unique_path(config_dir, "%s_%s" % (stem, stamp), ".csv", stamp))

    with open(config_dir / COLUMN_MAP_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMN_MAP_HEADER)
        for name, header_row, sheet, mapping in forms:
            for header, key in mapping.items():
                if key is not None:
                    writer.writerow([name, header, key, "" if header_row == 1 else header_row, sheet or ""])
    with open(config_dir / OUTPUT_COLUMNS_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(OUTPUT_COLUMNS_HEADER)
        for order, (name, role) in enumerate(output_columns, start=1):
            writer.writerow([order, name, role])
