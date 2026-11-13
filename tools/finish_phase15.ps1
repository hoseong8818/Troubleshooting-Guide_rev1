# Phase 15 마무리(사람이 실행): 옛 실행 파일 4개 삭제(T102), tasks.md T094~T103 완료 표시,
# CLAUDE.md '현재 상태' 줄을 실행 파일 4개 기준으로 고치고 커밋한다.
# 사용(저장소 루트에서):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\finish_phase15.ps1
# - tasks.md와 CLAUDE.md는 BOM 없이 CRLF로 쓴다(기존 형식과 같다). 이미 반영돼 있으면 그 부분은 건너뛴다.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$enc = New-Object System.Text.UTF8Encoding $false
$bt = [string][char]96

# ---- T102: 옛 실행 파일 지우기 ----
$old = @("run_merge.bat", "run_survey.bat", "demo_start.bat", "demo_stop.bat") | Where-Object { Test-Path (Join-Path $root $_) }
if ($old) {
  git rm -q -- $old
  Write-Host ("지웠습니다: " + ($old -join ", "))
} else {
  Write-Host "옛 실행 파일이 이미 없습니다."
}

# ---- tasks.md: T094~T103 완료 표시 ----
$tasksPath = Join-Path $root "specs\001-trouble-merge\tasks.md"
$tasks = [IO.File]::ReadAllText($tasksPath, $enc)
$tasks = $tasks -replace '- \[ \] (T(09[4-9]|10[0-3])) ', '- [x] $1 '
[IO.File]::WriteAllText($tasksPath, $tasks, $enc)
Write-Host "tasks.md에 T094~T103 완료 표시를 했습니다."

# ---- CLAUDE.md: 현재 상태 줄 ----
$claudePath = Join-Path $root "CLAUDE.md"
$claude = [IO.File]::ReadAllText($claudePath, $enc)
$pairs = @(
  @("구현은 Phase 10까지 끝났고 테스트 119개가 통과한다", "구현은 Phase 15까지 끝났고 테스트 157개가 통과한다"),
  @("실제 업무 실행은 ${bt}run_merge.bat${bt}(맨 위 세 줄만 고치고 사람이 더블클릭)",
    "실제 업무 실행은 ${bt}1_검사.bat${bt} ~ ${bt}4_서버종료.bat${bt}(맨 위 네 줄만 고치고 사람이 더블클릭. 설정은 ${bt}2_설정.bat${bt}이 여는 브라우저 화면, 서버는 127.0.0.1에서만)")
)
foreach ($p in $pairs) {
  if ($claude.Contains($p[0])) {
    $claude = $claude.Replace($p[0], $p[1])
  } elseif ($claude.Contains($p[1])) {
    Write-Host "CLAUDE.md에 이미 반영돼 있습니다."
  } else {
    throw "CLAUDE.md에서 고칠 문장을 찾지 못했습니다. 아무것도 커밋하지 않았습니다."
  }
}
[IO.File]::WriteAllText($claudePath, $claude, $enc)
Write-Host "CLAUDE.md 현재 상태 줄을 고쳤습니다."

git add specs/001-trouble-merge/tasks.md CLAUDE.md
git commit -m "정리: 옛 실행 파일 4개 삭제(T102), tasks.md Phase 15 완료 표시, CLAUDE.md 현재 상태 갱신" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
