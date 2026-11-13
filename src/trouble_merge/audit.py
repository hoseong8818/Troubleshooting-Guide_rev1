"""감사 결과 텍스트 (T035, FR-008, US3).

한국어 텍스트 한 장. 파일명·시트명·컬럼명은 SafeLog가 정한 표시(마스킹·위치)로만 쓰고 셀 값은 넣지 않는다.
"""

import csv

from .writer import unique_path


class Audit:
    def __init__(self, log):
        self.log = log
        self.input_rows = 0
        self.output_rows = 0
        self.check_count = 0
        self.duplicate_count = 0
        self.files_read = 0
        self.failed_files = []       # 파일명
        self.limit_exceeded = []     # (파일명, 사유 종류) 크기·행 수 상한 초과(NFR-007)
        self.unmatched = []          # (사유 문구, 파일명, 시트명)
        self.unregistered = []       # (파일명, 시트명, 컬럼 표시)
        self.blank_required = []     # (파일명, 시트명, 행 번호, 컬럼 표시)
        self.hidden = []             # (파일명, 숨긴 시트 수)
        self.formula_missing = 0
        self.prefixed = 0
        self.reason_counts = {}      # 확인 필요 이유 -> 건수(한 행에 이유가 여럿이면 각각 센다, T060)
        self.excluded_sheets = None  # skip_sheets.csv로 뺀 시트 수(FR-028). 파일이 없으면 None(줄을 내지 않음)

    def count_reasons(self, records):
        counts = {}
        for record in records:
            for reason in (record["확인 필요 이유"] or "").split("; "):
                if reason:
                    counts[reason] = counts.get(reason, 0) + 1
        self.reason_counts = dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def add_unregistered(self, file, sheet, label):
        entry = (file, sheet, label)
        if entry not in self.unregistered:
            self.unregistered.append(entry)

    def render(self):
        log = self.log
        lines = ["감사 결과", ""]
        lines.append("입력 행 수: %d" % self.input_rows)
        lines.append("출력 행 수: %d" % self.output_rows)
        lines.append("행 수 일치: %s" % ("예" if self.input_rows == self.output_rows else "아니오"))
        lines.append("확인 필요 건수: %d" % self.check_count)
        for reason, count in self.reason_counts.items():
            lines.append("확인 필요 이유별 건수: %s %d" % (reason, count))
        lines.append("중복 의심 건수: %d" % self.duplicate_count)
        lines.append("읽은 파일 수: %d" % self.files_read)
        if self.files_read == 0:
            # 0행 대 0행이라 '행 수 일치: 예'가 나오므로 정상 처리로 오해하지 않게 분명히 적는다
            lines.append("처리 결과: 처리된 파일 없음")
        if self.failed_files:
            lines.append("실패한 파일: " + ", ".join(log.file_label(f) for f in self.failed_files))
        else:
            lines.append("실패한 파일: 없음")
        for file, kind in self.limit_exceeded:
            lines.append("상한 초과 파일: %s %s" % (log.file_label(file), kind))
        for reason, file, sheet in self.unmatched:
            lines.append("%s: %s %s" % (reason, log.file_label(file), log.sheet_label(sheet)))
        for file, sheet, label in self.unregistered:
            lines.append("대응 규칙 없는 컬럼: %s %s %s" % (log.file_label(file), log.sheet_label(sheet), label))
        for file, sheet, row, label in self.blank_required:
            lines.append("필수값 빈 칸: %s %s 행 %d 컬럼 %s" % (
                log.file_label(file), log.sheet_label(sheet), row, label))
        lines.append("숨긴 시트 수: %d" % sum(n for _, n in self.hidden))
        for file, count in self.hidden:
            if count:
                lines.append("숨긴 시트: %s %d개" % (log.file_label(file), count))
        if self.excluded_sheets is not None:
            lines.append("제외한 시트 수: %d" % self.excluded_sheets)
        lines.append("수식 값 없음 건수: %d" % self.formula_missing)
        lines.append("수식 방지 접두사 처리 건수: %d" % self.prefixed)
        return "\n".join(lines) + "\n"

    def write(self, out_dir, stamp):
        path = unique_path(out_dir, "audit_" + stamp, ".txt", stamp)
        path.write_text(self.render(), encoding="utf-8")
        return path


def write_check_list(log, records, out_dir, stamp):
    """확인 필요 행 목록 CSV(T060). 현장에 돌려주어 원본을 고치게 하는 용도라 위치와 이유만 쓴다(셀 값 없음)."""
    path = unique_path(out_dir, "check_list_" + stamp, ".csv", stamp)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["파일", "시트", "행", "이유"])
        flagged = [r for r in records if r["확인 필요 이유"]]
        flagged.sort(key=lambda r: (log.file_label(r["원본 파일"]), log.sheet_label(r["원본 시트"]), r["원본 행"]))
        for record in flagged:
            if record["확인 필요 이유"]:
                writer.writerow([log.file_label(record["원본 파일"]), log.sheet_label(record["원본 시트"]),
                                 record["원본 행"], record["확인 필요 이유"]])
    return path


def write_name_map(log, out_dir, stamp):
    """마스킹 이름과 실제 이름의 대응표를 감사 결과 옆에 따로 쓴다(NFR-009)."""
    path = unique_path(out_dir, "names_" + stamp, ".txt", stamp)
    path.write_text("\n".join(log.name_map_lines()) + "\n", encoding="utf-8")
    return path
