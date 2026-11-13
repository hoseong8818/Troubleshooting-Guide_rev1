# spec.md에 FR-025(헤더 조사 보고서)를, tasks.md에 Phase 12를 추가하고 커밋한다. 사람이 직접 실행한다.
# 사용(저장소 루트에서):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\add_phase12.ps1
# - spec.md: FR-024 줄 바로 뒤에 FR-025 줄을 넣는다.
# - tasks.md: '## 의존 관계' 바로 앞에 Phase 12 절을 넣는다.
# - 이미 들어가 있으면 그 파일은 건너뛴다. 두 파일 모두 BOM 없이 CRLF로 쓴다(기존 형식과 같다).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$enc = New-Object System.Text.UTF8Encoding $false
$bt = [string][char]96
$nl = "`r`n"

# ---- spec.md: FR-025 ----
$specPath = Join-Path $root "specs\001-trouble-merge\spec.md"
$spec = [IO.File]::ReadAllText($specPath, $enc)
if ($spec.Contains("**FR-025")) {
  Write-Host "spec.md에 이미 FR-025가 있어 건너뜁니다."
} else {
  $start = $spec.IndexOf("- **FR-024")
  if ($start -lt 0) { throw "spec.md에서 FR-024 줄을 찾지 못했습니다." }
  $end = $spec.IndexOf($nl, $start)
  if ($end -lt 0) { throw "spec.md의 FR-024 줄 끝을 찾지 못했습니다." }
  $fr = "- **FR-025 (헤더 조사 보고서)** ${bt}python -m trouble_merge.survey --input <폴더 또는 파일...> --config <폴더> --out <폴더>${bt}는 입력의 ${bt}.xlsx${bt}에서 보이는 시트의 헤더 행만 읽고(데이터 행은 읽지 않는다. 병합 칸은 채우지 않는다), 헤더 이름 목록(빈 칸 제외, 순서 무관)과 컬럼 대응 표 판별 결과가 같은 시트끼리 한 양식으로 묶어 ${bt}--out${bt}에 ${bt}survey_<실행 시각>.txt${bt}와 ${bt}names_<실행 시각>.txt${bt}를 만든다. 헤더 행은 컬럼 대응 표의 양식에 맞으면 그 양식의 헤더 행, 아니면 1행이다. 보고서는 줄마다 ${bt}이름: 값${bt} 형식이며 조사한 파일 수, 읽은 파일 수, 건너뛴 파일(지원하지 않는 형식, 상한 초과, 열기 실패), 숨긴 시트 수, 헤더 없는 시트 수, 양식 수, 새 양식 수를 내고, 양식마다(시트 수가 많은 순, 같으면 먼저 나온 순으로 ${bt}양식 1${bt}, ${bt}양식 2${bt} ...) 파일 수·시트 수·컬럼 수, 현재 컬럼 대응 표와의 관계(${bt}기존 양식 <이름>${bt}, ${bt}새 양식${bt}, ${bt}양식 모호${bt}, ${bt}대응 중복${bt}), 컬럼 목록, 시트 목록, 가장 가까운 다른 양식과 컬럼 몇 개 차이인지(이름 목록의 대칭 차집합 크기), 새 양식이면 등록 컬럼이 가장 많이 들어 있는 기존 양식과 그 양식에서 빠진 등록 컬럼 수를 낸다. 셀 값은 내지 않고 이름 표시는 NFR-009를 따른다(등록되지 않은 컬럼은 위치, 파일명·시트명은 마스킹, ${bt}--show-names${bt}로 실제 이름). 크기 상한은 NFR-007의 ${bt}--max-file-mb${bt}, ${bt}--max-unzipped-mb${bt}를 같은 기본값으로 받는다(데이터 행을 읽지 않으므로 행 수 상한은 없다). 통합 파일은 만들지 않으며 기존 통합 동작과 출력은 바꾸지 않는다. 종료 코드는 0 정상, 1 건너뛴 파일 있음, 2 읽은 파일 없음 또는 설정 오류이고, 예외의 메시지와 종류는 출력하지 않는다."
  $spec = $spec.Substring(0, $end) + $nl + $fr + $spec.Substring($end)
  [IO.File]::WriteAllText($specPath, $spec, $enc)
  Write-Host "spec.md에 FR-025를 추가했습니다."
}

# ---- tasks.md: Phase 12 ----
$tasksPath = Join-Path $root "specs\001-trouble-merge\tasks.md"
$tasks = [IO.File]::ReadAllText($tasksPath, $enc)
if ($tasks.Contains("## Phase 12:")) {
  Write-Host "tasks.md에 이미 Phase 12가 있어 건너뜁니다."
} else {
  $marker = "## 의존 관계"
  $idx = $tasks.IndexOf($marker)
  if ($idx -lt 0) { throw "tasks.md에서 '## 의존 관계' 줄을 찾지 못했습니다." }
  $lines = @(
    "## Phase 12: 스토리 4 보강 (P2) 헤더 조사 보고서(창 없음)",
    "",
    "컬럼 설정 창 제안서(${bt}docs/proposals/column-setup-popup.md${bt})의 1단계. 실제 엑셀이 수백 개일 때 양식이 몇 종인지 창 없이 텍스트로 알려 준다. 기존 통합 동작과 출력은 바꾸지 않는다(FR-025).",
    "",
    "- [ ] T074 [P] [US4] ${bt}tests/test_header_survey.py${bt}: ${bt}python -m trouble_merge.survey${bt}가 가짜 데이터(${bt}data/fake/${bt})와 임시로 만든 새 양식·컬럼 하나 더한 양식 파일을 읽어 양식별 파일 수·시트 수·컬럼 수, 기존 양식 이름 또는 ${bt}새 양식${bt}, 가장 가까운 양식과의 컬럼 차이, 숨긴 시트 수, 건너뛴 파일을 ${bt}survey_*.txt${bt}에 낸다. 헤더 행이 1행이 아닌 양식은 대응 표의 헤더 행으로 판별한다. 보고서·stdout·stderr에 표식 값 ${bt}LEAK-${bt}, 등록되지 않은 컬럼명, 기본 설정의 실제 파일명이 없고(${bt}--show-names${bt}이면 실제 파일명), 통합 엑셀을 만들지 않으며 입력 파일이 바뀌지 않는다. 설정 오류는 종료 코드 2, 트레이스백 없음(FR-025, NFR-009)",
    "- [ ] T075 [US4] 위 테스트가 기대값 불일치로 실패하는 것을 확인하고 실패 상태로 커밋(${bt}test:${bt}로 시작)",
    "- [ ] T076 [US4] ${bt}src/trouble_merge/survey.py${bt}: 헤더 행만 읽기, 양식 묶기, 대응 표와 비교, 보고서 쓰기(${bt}reader${bt}·${bt}mapping${bt}·${bt}safe_log${bt} 재사용, openpyxl만)",
    "- [ ] T077 [US4] ${bt}run_survey.bat${bt}: 맨 위 세 줄(입력, 설정, 출력 폴더)만 고치면 더블클릭으로 헤더 조사 보고서를 만들고 연다. 기본 경로는 저장소 밖 실제 폴더 자리표시자이며, 실제 데이터 실행은 사람이 한다(헌법 원칙 1)",
    "- [ ] T078 [US4] 통과 확인, 감사관 판정, 커밋. README에 사용법 한 줄 추가",
    "",
    ""
  )
  $block = ($lines -join $nl)
  $tasks = $tasks.Substring(0, $idx) + $block + $tasks.Substring($idx)
  [IO.File]::WriteAllText($tasksPath, $tasks, $enc)
  Write-Host "tasks.md에 Phase 12를 추가했습니다."
}

git add specs/001-trouble-merge/spec.md specs/001-trouble-merge/tasks.md
git commit -m "문서: spec.md에 FR-025(헤더 조사 보고서), tasks.md에 Phase 12 추가" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
