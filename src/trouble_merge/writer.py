"""통합 엑셀과 감사 결과 쓰기 (T023). 덮어쓰지 않고, 이미 있으면 실행 시각을 붙인다."""

from pathlib import Path

from openpyxl import Workbook

from .mapping import EXTRA_ROLE, FIXED_COLUMNS, ROLE_SHEET
from .merge import OUTPUT_HEADER

DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def unique_path(out_dir, stem, suffix, stamp):
    out_dir = Path(out_dir)
    path = out_dir / (stem + suffix)
    if not path.exists():
        return path
    path = out_dir / ("%s_%s%s" % (stem, stamp, suffix))
    counter = 2
    while path.exists():
        path = out_dir / ("%s_%s_%d%s" % (stem, stamp, counter, suffix))
        counter += 1
    return path


def output_columns_layout(output_columns):
    """[(헤더에 쓸 이름, 행 사전의 키)]. output_columns가 없으면 지금 헤더 그대로(FR-026)."""
    if output_columns is None:
        return [(name, name) for name in OUTPUT_HEADER]
    layout = [(name, name if role == EXTRA_ROLE else role) for name, role in output_columns]
    return layout + [(name, name) for name in FIXED_COLUMNS]


def write_workbook(records, out_dir, stamp, output_columns=None):
    """통합 엑셀을 쓰고 (경로, 수식 방지 접두사를 붙인 셀 수)를 돌려준다(NFR-008).

    output_columns가 있으면 결과 컬럼을 그 순서·표시 이름으로 쓰고, '컬럼 역할' 시트를 더한다(FR-026).
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    layout = output_columns_layout(output_columns)
    wb = Workbook()
    ws = wb.active
    ws.title = "통합"
    ws.append([header for header, _ in layout])
    for cell in ws[1]:
        cell.data_type = "s"  # 설정의 표시 이름도 수식으로 저장하지 않는다
    prefixed = 0
    for row_number, record in enumerate(records, start=2):
        for column_number, (_, key) in enumerate(layout, start=1):
            value = record[key]
            cell = ws.cell(row=row_number, column=column_number)
            if isinstance(value, str):
                if value.startswith(DANGEROUS_PREFIXES):
                    value = "'" + value
                    prefixed += 1
                cell.value = value
                cell.data_type = "s"  # 항상 문자열로 저장
            else:
                cell.value = value
    if output_columns is not None:
        roles = wb.create_sheet(ROLE_SHEET)
        roles.append(["표시 이름", "역할"])
        for name, role in output_columns:
            roles.append([name, role])
            for cell in roles[roles.max_row]:
                cell.data_type = "s"
    path = unique_path(out_dir, "merged", ".xlsx", stamp)
    wb.save(path)
    return path, prefixed

