# HTML 설정 화면과 실행 파일 4개: spec.md에 FR-028(제외 시트), FR-029(로컬 서버와 HTML 설정 화면),
# FR-030(실행 파일 4개)을, tasks.md에 Phase 15를 추가하고 커밋한다. 사람이 직접 실행한다.
# 사용(저장소 루트에서):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\add_phase15.ps1
# 사람이 정한 것(2026-11-13): 실행 파일은 검사·설정·서버 실행·서버 종료 4개. 설정은 브라우저(HTML) 화면.
# 설정 화면은 칸마다 예시 값을 보여 준다(이 PC 화면에만, 로그·파일에는 남기지 않음).
# - spec.md: FR-027 줄 바로 뒤에 FR-028~FR-030 줄을 넣는다.
# - tasks.md: '## 의존 관계' 바로 앞에 Phase 15 절을 넣는다.
# - 이미 들어가 있으면 그 파일은 건너뛴다. 두 파일 모두 BOM 없이 CRLF로 쓴다(기존 형식과 같다).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$enc = New-Object System.Text.UTF8Encoding $false
$bt = [string][char]96
$nl = "`r`n"

# ---- spec.md: FR-028 ~ FR-030 ----
$specPath = Join-Path $root "specs\001-trouble-merge\spec.md"
$spec = [IO.File]::ReadAllText($specPath, $enc)
if ($spec.Contains("**FR-028")) {
  Write-Host "spec.md에 이미 FR-028이 있어 건너뜁니다."
} else {
  $start = $spec.IndexOf("- **FR-027")
  if ($start -lt 0) { throw "spec.md에서 FR-027 줄을 찾지 못했습니다." }
  $end = $spec.IndexOf($nl, $start)
  if ($end -lt 0) { throw "spec.md의 FR-027 줄 끝을 찾지 못했습니다." }
  $fr28 = "- **FR-028 (제외 시트)** ${bt}--config${bt} 폴더에 ${bt}skip_sheets.csv${bt}(UTF-8 BOM, 컬럼: 시트)가 있으면 이름이 같은(앞뒤 공백·대소문자만 정리) 보이는 시트는 통합과 헤더 조사에서 읽지 않는다(목차·요약 시트용). 감사 결과와 헤더 조사 보고서에 ${bt}제외한 시트 수: N${bt} 줄을 내고, 제외한 시트는 '대응 규칙 없음'으로 세지 않으며 종료 코드 1의 원인이 되지 않는다. 파일이 없으면 지금과 같다."
  $fr29 = "- **FR-029 (로컬 서버와 HTML 설정 화면)** ${bt}python -m trouble_merge.server --input <폴더...> --config <폴더> --out <폴더> [--port 3456] [--merge]${bt}는 표준 라이브러리 HTTP 서버를 ${bt}127.0.0.1${bt}에만 연다(${bt}--port 0${bt}이면 빈 포트, 시작할 때 ${bt}주소: http://127.0.0.1:<포트>/${bt} 한 줄을 낸다). ${bt}--merge${bt}면 시작할 때 통합(FR-019)과 게시판을 ${bt}--out${bt}의 ${bt}run_<실행 시각>${bt} 폴더에 만든다. ${bt}/${bt}는 가장 최근 ${bt}run_*${bt}의 게시판을, 없으면 안내 화면을 보인다. ${bt}/setup${bt}은 설정 화면이다: 양식(모양)마다 파일 수와 시트 이름, 원본 칸마다 예시 값(그 양식 첫 시트의 데이터 행에서 빈 칸이 아닌 값 앞 3개, 30자까지)과 결과 칸 고르기(판정 컬럼, 추가 컬럼, ${bt}따로 보관${bt}=기타 항목), ${bt}이 모양은 통합하지 않음${bt}(그 시트 이름을 ${bt}skip_sheets.csv${bt}에 저장), 접어 둔 고급 칸(결과 컬럼 이름·순서·추가)을 한 화면에 보인다. 추천·검사·저장은 FR-027의 ${bt}setup_config${bt}을 그대로 쓴다. 저장 뒤 ${bt}통합하고 게시판 보기${bt}로 통합을 다시 하고 ${bt}/${bt}로 간다. 예시 값은 그 화면 응답에만 담고 로그·파일·stdout·stderr에는 남기지 않는다. 안전: Host 머리글이 ${bt}127.0.0.1:<포트>${bt} 또는 ${bt}localhost:<포트>${bt}가 아니면 거부, 데이터를 바꾸는 요청은 POST와 ${bt}Content-Type: application/json${bt}과 머리글 ${bt}X-Trouble-Merge: 1${bt}이 있어야 하고 본문은 1MB까지, CORS 머리글은 내지 않으며 외부 주소를 불러오지 않는다. 서버 로그는 고정 문구(요청 종류와 상태 코드)만 낸다."
  $fr30 = "- **FR-030 (실행 파일 4개)** 저장소 루트의 ${bt}1_검사.bat${bt}(FR-025 보고서를 만들고 열며 새 양식이 있으면 2번을 안내), ${bt}2_설정.bat${bt}(서버가 꺼져 있으면 켜고 ${bt}/setup${bt}을 연다), ${bt}3_서버실행.bat${bt}(켜진 서버를 끄고 ${bt}--merge${bt}로 다시 켠 뒤 ${bt}/${bt}를 연다. 엑셀이 늘면 이것만 다시 실행), ${bt}4_서버종료.bat${bt}(그 포트의 python 서버만 끈다)로 쓴다. 네 파일은 맨 위의 같은 네 줄(INPUT, CONFIG, OUT, PORT)만 고친다. 기본 경로는 예시 데이터이며 실제 데이터 경로로 바꾸는 것과 실제 데이터 실행은 사람이 한다(헌법 원칙 1). 서버는 별도 창에서 돌고 그 창을 닫아도 꺼진다."
  $spec = $spec.Substring(0, $end) + $nl + $fr28 + $nl + $fr29 + $nl + $fr30 + $spec.Substring($end)
  [IO.File]::WriteAllText($specPath, $spec, $enc)
  Write-Host "spec.md에 FR-028~FR-030을 추가했습니다."
}

# ---- tasks.md: Phase 15 ----
$tasksPath = Join-Path $root "specs\001-trouble-merge\tasks.md"
$tasks = [IO.File]::ReadAllText($tasksPath, $enc)
if ($tasks.Contains("## Phase 15:")) {
  Write-Host "tasks.md에 이미 Phase 15가 있어 건너뜁니다."
} else {
  $marker = "## 의존 관계"
  $idx = $tasks.IndexOf($marker)
  if ($idx -lt 0) { throw "tasks.md에서 '## 의존 관계' 줄을 찾지 못했습니다." }
  $lines = @(
    "## Phase 15: 스토리 4·5 보강 (P2) HTML 설정 화면과 실행 파일 4개",
    "",
    "사람이 정한 것: 실행 파일은 검사·설정·서버 실행·서버 종료 4개, 설정은 브라우저 화면, 칸마다 예시 값을 보인다(이 PC 화면에만). tkinter 창(Phase 14)의 판단 로직 ${bt}setup_config${bt}은 그대로 쓰고 화면만 HTML로 바꾼다(FR-028~FR-030).",
    "",
    "- [ ] T094 [P] [US4] ${bt}tests/test_skip_sheets.py${bt}: 설정 사본에 ${bt}skip_sheets.csv${bt}를 두고 이름이 같은 시트(앞뒤 공백·대소문자 차이 포함)가 통합과 헤더 조사에서 빠지고, 감사 결과·보고서에 ${bt}제외한 시트 수${bt}가 나오며, 그 시트만 대응 규칙이 없던 입력의 종료 코드가 0이 된다. 다른 시트의 행 수는 그대로다(FR-028)",
    "- [ ] T095 [P] [US4] ${bt}tests/test_web_server.py${bt}: ${bt}python -m trouble_merge.server --port 0${bt}을 임시 입력·설정·출력 폴더로 띄워 ① ${bt}/api/scan${bt} JSON에 양식·실제 헤더·예시 값(앞 3개)·새 양식이 있다 ② ${bt}/setup${bt}과 ${bt}/${bt} 화면에 외부 주소가 없다 ③ 머리글 ${bt}X-Trouble-Merge${bt}이 없거나 Host가 다르면 거부(403) ④ ${bt}/api/save${bt}가 대응·제외 시트를 저장하고(오류면 저장 안 함) ${bt}/api/merge${bt} 뒤 ${bt}/${bt}가 게시판을 보인다 ⑤ 서버의 stdout·stderr와 저장한 CSV에 표식 값 ${bt}LEAK-${bt}가 없다(FR-029)",
    "- [ ] T096 [US4] 위 테스트가 기대값 불일치로 실패하는 것을 확인하고 실패 상태로 커밋(${bt}test:${bt}로 시작)",
    "- [ ] T097 [US4] ${bt}src/trouble_merge/mapping.py${bt}, ${bt}cli.py${bt}, ${bt}audit.py${bt}, ${bt}survey.py${bt}: 제외 시트",
    "- [ ] T098 [US4] ${bt}src/trouble_merge/setup_config.py${bt}: 예시 값 읽기(화면용, 출력 없음)와 제외 시트 저장",
    "- [ ] T099 [US4] ${bt}src/trouble_merge/server.py${bt}, ${bt}setup_page.html${bt}: 로컬 서버와 설정 화면(외부 주소 없음, 화면에는 textContent로만 그림)",
    "- [ ] T100 [US4] ${bt}1_검사.bat${bt}, ${bt}2_설정.bat${bt}, ${bt}3_서버실행.bat${bt}, ${bt}4_서버종료.bat${bt}: 맨 위 네 줄(INPUT, CONFIG, OUT, PORT), 기본은 예시 데이터 경로",
    "- [ ] T101 [사람] 예시 데이터로 1 → 2 → 3 → 4 순서로 실행해 화면을 확인한다",
    "- [ ] T102 [사람] 옛 실행 파일(${bt}run_merge.bat${bt}, ${bt}run_survey.bat${bt}, ${bt}demo_start.bat${bt}, ${bt}demo_stop.bat${bt})을 지운다(Claude가 명령을 준다)",
    "- [ ] T103 [US4] 통과 확인, 감사관 판정, 커밋. README의 실행 방법을 4단계로 다시 쓴다",
    "",
    ""
  )
  $block = ($lines -join $nl)
  $tasks = $tasks.Substring(0, $idx) + $block + $tasks.Substring($idx)
  [IO.File]::WriteAllText($tasksPath, $tasks, $enc)
  Write-Host "tasks.md에 Phase 15를 추가했습니다."
}

git add specs/001-trouble-merge/spec.md specs/001-trouble-merge/tasks.md
git commit -m "문서: spec.md에 FR-028~FR-030(제외 시트, HTML 설정 화면, 실행 파일 4개), tasks.md에 Phase 15 추가" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
