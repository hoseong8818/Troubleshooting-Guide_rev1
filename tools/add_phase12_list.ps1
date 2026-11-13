# FR-025의 '시트 목록'을 앞 몇 개 + '외 N개'로 줄이도록 고치고, tasks.md Phase 12에 T079~T081을 추가해 커밋한다. 사람이 직접 실행한다.
# 사용(저장소 루트에서):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\add_phase12_list.ps1
# - spec.md: FR-025의 "컬럼 목록, 시트 목록, "을 줄이는 규칙이 붙은 문구로 바꾼다.
# - tasks.md: T078 줄 바로 뒤에 T079~T081을 넣는다.
# - 이미 들어가 있으면 그 파일은 건너뛴다. 두 파일 모두 BOM 없이 CRLF로 쓴다(기존 형식과 같다).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$enc = New-Object System.Text.UTF8Encoding $false
$bt = [string][char]96
$nl = "`r`n"

# ---- spec.md: FR-025 시트 목록 ----
$specPath = Join-Path $root "specs\001-trouble-merge\spec.md"
$spec = [IO.File]::ReadAllText($specPath, $enc)
if ($spec.Contains("--max-sheet-list")) {
  Write-Host "spec.md에 이미 시트 목록 줄이기 규칙이 있어 건너뜁니다."
} else {
  $old = "컬럼 목록, 시트 목록, "
  if (-not $spec.Contains($old)) { throw "spec.md FR-025에서 '컬럼 목록, 시트 목록, '을 찾지 못했습니다." }
  $new = "컬럼 목록, 시트 목록(앞 10개까지 내고 넘으면 끝에 ${bt} 외 N개${bt}를 붙인다. 개수는 ${bt}--max-sheet-list${bt}로 바꾸며 0이면 전부), "
  $spec = $spec.Replace($old, $new)
  [IO.File]::WriteAllText($specPath, $spec, $enc)
  Write-Host "spec.md FR-025에 시트 목록 줄이기 규칙을 넣었습니다."
}

# ---- tasks.md: T079~T081 ----
$tasksPath = Join-Path $root "specs\001-trouble-merge\tasks.md"
$tasks = [IO.File]::ReadAllText($tasksPath, $enc)
if ($tasks.Contains(" T079 ")) {
  Write-Host "tasks.md에 이미 T079가 있어 건너뜁니다."
} else {
  $start = $tasks.IndexOf(" T078 ")
  if ($start -lt 0) { throw "tasks.md에서 T078 줄을 찾지 못했습니다." }
  $end = $tasks.IndexOf($nl, $start)
  if ($end -lt 0) { throw "tasks.md의 T078 줄 끝을 찾지 못했습니다." }
  $lines = @(
    "- [ ] T079 [US4] ${bt}tests/test_header_survey_list.py${bt}: 양식의 시트가 10개를 넘으면 보고서의 ${bt}시트:${bt} 줄에 앞 10개만 내고 끝에 ${bt} 외 N개${bt}를 붙인다. 10개 이하면 붙이지 않는다. ${bt}--max-sheet-list 3${bt}이면 3개, ${bt}0${bt}이면 전부를 낸다. 음수나 숫자가 아니면 종료 코드 2, 트레이스백 없음(FR-025)",
    "- [ ] T080 [US4] 위 테스트가 기대값 불일치로 실패하는 것을 확인하고 실패 상태로 커밋(${bt}test:${bt}로 시작)",
    "- [ ] T081 [US4] ${bt}src/trouble_merge/survey.py${bt}: 시트 줄 줄이기와 ${bt}--max-sheet-list${bt} 구현, 통과 확인, 커밋. README의 헤더 조사 줄에 옵션 추가"
  )
  $block = $nl + ($lines -join $nl)
  $tasks = $tasks.Substring(0, $end) + $block + $tasks.Substring($end)
  [IO.File]::WriteAllText($tasksPath, $tasks, $enc)
  Write-Host "tasks.md에 T079~T081을 추가했습니다."
}

git add specs/001-trouble-merge/spec.md specs/001-trouble-merge/tasks.md
git commit -m "문서: FR-025 시트 목록 줄이기, tasks.md에 T079~T081 추가" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
