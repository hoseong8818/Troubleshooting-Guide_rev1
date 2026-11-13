# 컬럼 설정 창 제안서 2~4단계: spec.md에 FR-026(결과 컬럼 설정), FR-027(컬럼 설정 창)을,
# tasks.md에 Phase 13·14를 추가하고 커밋한다. 사람이 직접 실행한다.
# 사용(저장소 루트에서):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\add_phase13.ps1
# 사람이 정한 것(2026-11-13): 판정 컬럼 6개는 이름·순서만 변경(빼기 불가), 추천은 공백·대소문자 차이와
# 이전에 저장한 대응만, 게시판의 표시 이름·순서 적용은 나중에(게시판 화면은 지금과 같게 유지).
# - spec.md: FR-025 줄 바로 뒤에 FR-026, FR-027 줄을 넣는다.
# - tasks.md: '## 의존 관계' 바로 앞에 Phase 13, 14 절을 넣는다.
# - 이미 들어가 있으면 그 파일은 건너뛴다. 두 파일 모두 BOM 없이 CRLF로 쓴다(기존 형식과 같다).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$enc = New-Object System.Text.UTF8Encoding $false
$bt = [string][char]96
$nl = "`r`n"

# ---- spec.md: FR-026, FR-027 ----
$specPath = Join-Path $root "specs\001-trouble-merge\spec.md"
$spec = [IO.File]::ReadAllText($specPath, $enc)
if ($spec.Contains("**FR-026")) {
  Write-Host "spec.md에 이미 FR-026이 있어 건너뜁니다."
} else {
  $start = $spec.IndexOf("- **FR-025")
  if ($start -lt 0) { throw "spec.md에서 FR-025 줄을 찾지 못했습니다." }
  $end = $spec.IndexOf($nl, $start)
  if ($end -lt 0) { throw "spec.md의 FR-025 줄 끝을 찾지 못했습니다." }
  $fr26 = "- **FR-026 (결과 컬럼 설정)** ${bt}--config${bt} 폴더에 ${bt}output_columns.csv${bt}(UTF-8 BOM, 컬럼: 순서, 표시 이름, 역할)가 있으면 통합 시트의 앞쪽 컬럼을 그 순서와 표시 이름으로 쓴다. 역할은 판정 컬럼(설비, 일자, 증상, 원인, 조치, 분류) 또는 ${bt}추가${bt}다. 판정 컬럼 6개는 모두 정확히 한 번씩 있어야 하며 뺄 수 없다(확인 필요·중복 의심 판정은 표시 이름과 상관없이 역할로 한다). 역할이 ${bt}추가${bt}인 컬럼은 ${bt}column_map.csv${bt}의 '표준 컬럼' 칸에 그 표시 이름으로 지정할 수 있고, 지정된 원본 컬럼의 값은 '기타 항목' 대신 그 컬럼에 FR-021대로 정리해 넣는다(확인 필요 판정 없음). 표시 이름은 비어 있지 않고 서로 다르며 고정 컬럼(기타 항목, 확인 필요 이유, 원래 값, 중복 의심, 원본 파일, 원본 시트, 원본 행)과 겹치지 않아야 한다. 이를 어기거나 ${bt}column_map.csv${bt}의 '표준 컬럼'이 판정 컬럼도 추가 컬럼도 아니면 설정 오류(종료 코드 2, 줄 번호만)다. 고정 컬럼은 지금 이름과 순서 그대로 결과 컬럼 뒤에 둔다. 이 파일이 있으면 통합 엑셀에 두 번째 시트 ${bt}컬럼 역할${bt}(컬럼: 표시 이름, 역할)을 함께 쓰고, 게시판(FR-019 이후의 board)은 이 시트로 역할을 찾아 지금과 같은 화면을 만든다. 이 파일이 없으면 출력은 지금과 같다. 입력 행 수 = 출력 행 수 원칙은 그대로다."
  $fr27 = "- **FR-027 (컬럼 설정 창)** ${bt}python -m trouble_merge.setup_gui --input <폴더 또는 파일...> --config <폴더>${bt}는 tkinter 창을 띄운다(표준 라이브러리만). ① 양식 찾기: FR-025와 같은 방법으로 헤더 행만 읽어 양식별 파일 수와 ${bt}새 양식${bt}을 보여 준다. 헤더 행은 대응 표의 값 또는 1행이며 창에서 바꾸지 않는다(데이터 행을 화면에 보이지 않기 위함. 바꾸려면 사람이 ${bt}column_map.csv${bt}를 고친다). ② 결과 컬럼: 판정 컬럼 6개의 표시 이름과 순서를 바꾸고, 추가 컬럼을 더하거나 뺀다. ③ 양식별 대응: 원본 컬럼마다 결과 컬럼 하나 또는 ${bt}기타 항목${bt}(기본값)을 고른다. 추천은 결과 컬럼 이름 또는 이전에 저장한 대응의 원본 컬럼명과 앞뒤 공백·대소문자만 다른 경우에만 미리 채우고, 그 밖의 비슷한 이름은 묶지 않는다. 새 양식 이름은 ${bt}양식 N${bt}으로 붙이고 창에서 바꿀 수 있다. 저장 전에 한 양식에서 두 원본 컬럼이 같은 결과 컬럼에 대응되면 저장하지 않고 겹치는 컬럼을 표시하며, 설비·증상·원인·조치에 대응이 없는 양식은 경고 후 저장을 허용한다. 저장은 ${bt}column_map.csv${bt}(지금 형식)와 ${bt}output_columns.csv${bt}(FR-026)를 UTF-8 BOM으로 쓰고, 기존 파일은 덮어쓰지 않고 ${bt}<이름>_<실행 시각>.csv${bt}로 옮겨 보관한 뒤 새로 쓴다. 창은 실제 헤더 이름을 사람 PC 화면에만 보이며 셀 값은 보이지 않는다. 로그와 stdout·stderr는 safe_log 규칙(NFR-009)을 따른다. 판단 로직(양식 찾기, 추천, 검사, 저장)은 화면과 나눈 ${bt}setup_config${bt} 모듈에 둔다. ${bt}run_merge.bat${bt}은 설정이 있으면 ${bt}1 기존 설정으로 실행 / 2 설정 창 열기${bt}를 묻고, 없으면 창을 열며, 창에서 ${bt}이 설정으로 통합 실행${bt}을 고르면 통합으로 넘어가고 ${bt}저장만 하고 닫기${bt}면 멈춘다. 맨 위 ${bt}GUI${bt} 줄을 0으로 두면 창 없이 지금처럼 실행한다."
  $spec = $spec.Substring(0, $end) + $nl + $fr26 + $nl + $fr27 + $spec.Substring($end)
  [IO.File]::WriteAllText($specPath, $spec, $enc)
  Write-Host "spec.md에 FR-026, FR-027을 추가했습니다."
}

# ---- tasks.md: Phase 13, 14 ----
$tasksPath = Join-Path $root "specs\001-trouble-merge\tasks.md"
$tasks = [IO.File]::ReadAllText($tasksPath, $enc)
if ($tasks.Contains("## Phase 13:")) {
  Write-Host "tasks.md에 이미 Phase 13이 있어 건너뜁니다."
} else {
  $marker = "## 의존 관계"
  $idx = $tasks.IndexOf($marker)
  if ($idx -lt 0) { throw "tasks.md에서 '## 의존 관계' 줄을 찾지 못했습니다." }
  $lines = @(
    "## Phase 13: 스토리 4 보강 (P2) 결과 컬럼 설정(output_columns.csv)",
    "",
    "컬럼 설정 창 제안서 2단계(FR-026). 사람이 정한 것: 판정 컬럼 6개는 이름·순서만 바꾸고 빼지 않는다. 게시판 화면은 지금과 같게 유지한다(표시 이름 적용은 나중에). 테스트는 설정 사본(${bt}make_config${bt})에 파일을 더해 쓰고, 기존 정답 파일과 테스트는 바꾸지 않는다.",
    "",
    "- [ ] T082 [P] [US4] ${bt}tests/test_output_columns.py${bt}: 가짜 데이터로 ① 판정 컬럼 6개를 지금 이름·순서로 적은 ${bt}output_columns.csv${bt}면 첫 시트가 파일이 없을 때와 같다 ② 이름을 바꾸고 순서를 섞으면(예: ${bt}호기, 발생일, 현상, 원인, 조치, 부품${bt}) 헤더가 그 순서·이름이고 각 행의 값은 역할별로 파일이 없을 때와 같다 ③ 추가 컬럼(${bt}A,에러코드,알람코드,,${bt} + ${bt}7,알람코드,추가${bt})이면 그 컬럼에 값이 들어가고 '기타 항목'에서 ${bt}에러코드:${bt}가 빠진다 ④ 두 번째 시트 ${bt}컬럼 역할${bt}이 있다 ⑤ 판정 컬럼 누락·중복, 표시 이름 중복·빈 칸·고정 컬럼과 겹침, 대응 표의 모르는 표준 컬럼은 종료 코드 2, 트레이스백 없음 ⑥ 입력 행 수 = 출력 행 수, 확인 필요 건수는 파일이 없을 때와 같다(FR-026)",
    "- [ ] T083 [P] [US4] ${bt}tests/test_board_roles.py${bt}: 표시 이름을 바꾼 통합 엑셀로 만든 게시판 데이터(JSON)가 파일 없이 만든 통합 엑셀의 게시판 데이터와 같다(FR-026)",
    "- [ ] T084 [US4] 위 테스트가 기대값 불일치로 실패하는 것을 확인하고 실패 상태로 커밋(${bt}test:${bt}로 시작)",
    "- [ ] T085 [US4] ${bt}src/trouble_merge/mapping.py${bt}, ${bt}merge.py${bt}, ${bt}writer.py${bt}, ${bt}cli.py${bt}, ${bt}board.py${bt}: ${bt}output_columns.csv${bt} 읽기·검사, 추가 컬럼 값, 표시 이름 헤더, ${bt}컬럼 역할${bt} 시트, 게시판의 역할 찾기",
    "- [ ] T086 [US4] 통과 확인, 감사관 판정, 커밋. README에 ${bt}output_columns.csv${bt} 형식 추가",
    "",
    "## Phase 14: 스토리 4 보강 (P2) 컬럼 설정 창",
    "",
    "컬럼 설정 창 제안서 3·4단계(FR-027). 사람이 정한 것: 비슷한 이름 추천은 앞뒤 공백·대소문자 차이와 이전에 저장한 대응만. 헤더 행 선택과 데이터 행 미리 보기는 하지 않는다. 판단 로직은 ${bt}setup_config${bt}에 두고 테스트하며, 화면(${bt}setup_gui${bt})은 그 함수만 부른다.",
    "",
    "- [ ] T087 [P] [US4] ${bt}tests/test_setup_config.py${bt}: 가짜 데이터와 임시 새 양식 파일로 ① 양식 목록(양식별 파일 수, 기존 양식 이름 또는 새 양식, 실제 헤더 이름, 새 양식 이름 ${bt}양식 N${bt}) ② 추천(공백·대소문자만 다른 이름과 이전 대응에 있는 이름만, ${bt}조치 내용${bt}처럼 가운데 공백이 다른 이름은 추천 없음) ③ 검사(한 양식에서 같은 결과 컬럼 두 번이면 저장 불가와 겹치는 컬럼, 설비·증상·원인·조치 대응 없음은 경고) ④ 저장(${bt}column_map.csv${bt}·${bt}output_columns.csv${bt}를 UTF-8 BOM으로, 기존 파일은 ${bt}<이름>_<시각>.csv${bt}로 보관, 저장한 설정으로 통합하면 종료 코드 0이고 새 양식 행이 들어간다) ⑤ stdout·stderr에 표식 값 ${bt}LEAK-${bt}가 없다(FR-027)",
    "- [ ] T088 [US4] 위 테스트가 기대값 불일치로 실패하는 것을 확인하고 실패 상태로 커밋(${bt}test:${bt}로 시작)",
    "- [ ] T089 [US4] ${bt}src/trouble_merge/setup_config.py${bt}: 양식 찾기(${bt}survey${bt} 재사용), 추천, 검사, 저장",
    "- [ ] T090 [US4] ${bt}src/trouble_merge/setup_gui.py${bt}: tkinter 창(① 양식 찾기 ② 결과 컬럼 ③ 양식별 대응, ${bt}이 설정으로 통합 실행${bt} / ${bt}저장만 하고 닫기${bt}). 종료 코드 0 통합 실행, 3 저장만, 4 취소",
    "- [ ] T091 [US4] ${bt}run_merge.bat${bt}: 맨 위에 ${bt}GUI${bt} 줄 추가. 설정이 있으면 ${bt}1 기존 설정으로 실행 / 2 설정 창 열기${bt}, 없으면 창. 창 종료 코드 0이면 통합으로 넘어간다",
    "- [ ] T092 [사람] 예시 데이터(${bt}data\sample${bt})로 ${bt}run_merge.bat${bt}을 실행해 창의 세 단계, 저장, 통합 실행까지 화면을 확인한다",
    "- [ ] T093 [US4] 통과 확인, 감사관 판정, 커밋. README에 설정 창 사용법 추가",
    "",
    ""
  )
  $block = ($lines -join $nl)
  $tasks = $tasks.Substring(0, $idx) + $block + $tasks.Substring($idx)
  [IO.File]::WriteAllText($tasksPath, $tasks, $enc)
  Write-Host "tasks.md에 Phase 13, 14를 추가했습니다."
}

git add specs/001-trouble-merge/spec.md specs/001-trouble-merge/tasks.md
git commit -m "문서: spec.md에 FR-026(결과 컬럼 설정)·FR-027(컬럼 설정 창), tasks.md에 Phase 13·14 추가" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
