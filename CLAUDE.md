# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 현재 상태

구현은 Phase 15까지 끝났고 테스트 157개가 통과한다(`src/trouble_merge/`, `tests/`). 데모는 `tools\run_demo.ps1 -Serve`(가짜·예시 데이터 통합 + 게시판 http://localhost:3456), 실제 업무 실행은 `1_검사.bat` ~ `4_서버종료.bat`(맨 위 네 줄만 고치고 사람이 더블클릭. 설정은 `2_설정.bat`이 여는 브라우저 화면, 서버는 127.0.0.1에서만). 남은 사람 작업은 T003a, T003b, T047, T050, T063. 보호 훅(`protect_files.py`)은 구현·등록했고 보호할 파일은 모두 커밋되어 실제로 보호된다. 입력 크기와 행 수 상한(NFR-007)은 명령줄 옵션으로 구현했고(기본값은 데모용), 운영체제 권한과 회사 PC 확인은 데모 범위에서 하지 않았으며 실제 업무 이관 시 T050에서 한다(README 참고). 작업은 `specs/001-trouble-merge/tasks.md`의 Phase 순서를 따른다. 문서와 출력 문구는 모두 한국어다.

## 이 도구가 하는 일

양식이 다른 설비 트러블슈팅 엑셀 여러 개를 읽어 표준 컬럼(설비, 일자, 증상, 원인, 조치, 분류 + 기타 항목)의 통합 시트 1장으로 만들고, 감사 결과 텍스트를 함께 낸다. 설비는 설비 코드 컬럼 기준이며, 자유 텍스트 추정은 범위 밖이다.

## 문서 읽는 순서

1. `docs/constitution.md` — 다섯 원칙. 이를 어기는 계획은 진행하지 않고 계획을 고친다.
2. `specs/001-trouble-merge/spec.md` — 요구사항 ID(FR/NFR/SC)와 수용 기준
3. `specs/001-trouble-merge/plan.md` — 기술 선택, 폴더 구조, 데이터 모델, 요구사항 추적표
4. `specs/001-trouble-merge/tasks.md` — Phase별 작업 (`[사람]` 표시는 사람이 직접 확정)

## 지켜야 할 규칙 (헌법 요약)

- **실제 엑셀은 읽지 않는다.** 가짜 데이터(`data/fake/`)와 사람이 쓴 컬럼 설명 문서(`docs/columns-*.md`)만 쓴다. 실제 입력·결과·변환표는 저장소 밖 고정 폴더(`real_data`, `real_out`, `real_config`)에 두고, 실제 데이터에 도구를 돌리는 것은 사람이 자기 터미널에서만 한다. 저장소 안의 `out/`과 `config/`는 가짜 데이터 전용이다. deny와 훅은 문자열 검사라 완전하지 않아 운영체제 권한을 병행한다(헌법 v1.2.0).
- **로그·에러에 셀 값 금지.** 로그는 `safe_log` 한 길만 쓰고, 종류·파일명·시트명·행 번호·컬럼명·건수만 받는다. 컬럼명은 대응 표에 등록된 것만 그대로 내고 나머지는 `열 3(C)`로, 파일명·시트명은 기본 마스킹. 예외 메시지도 같은 길로 낸다.
- **입력 엑셀은 신뢰하지 않는다.** `.xlsx`만 읽고, 크기·행 수 상한을 넘으면 건너뛰며, 출력 문자열 셀이 `=+-@`로 시작하면 `'`를 붙여 수식 실행을 막는다(NFR-007, NFR-008).
- **판단이 안 되면 '확인 필요'.** 설비 코드 빈 칸/미등록, 분류 미등록, 필수값 빈 행, 해석 불가 날짜는 행을 빼지 않고 '확인 필요' + 원래 값 + 이유로 남긴다. 입력 행 수 = 출력 행 수.
- **보호 대상 수정 금지:** `expected/`, `data/fake/`, `tests/`, `config/*.csv`, `.claude/settings.json`, `.claude/hooks/`, `.claude/agents/`, `docs/constitution.md`, `CLAUDE.md`, `specs/**/spec.md`·`plan.md`·`tasks.md`. 이미 git에 커밋된 파일은 훅이 막고(deny가 아니라 훅), 아직 없는 파일은 `tasks.md`에 이름이 적힌 것만 새로 만들 수 있다. `.claude/` 아래(`settings.local.json` 포함)는 새 파일도 만들지 않는다. git은 `status`·`diff`·`log`·`show`·`add`·`commit`만 쓰고, `rm`·`reset`·`restore`·`checkout --`·`stash`·`config`·`rebase`는 쓰지 않는다. 되돌리기는 사람이 한다. 변환표·매핑표는 추가할 줄을 제안만 하고 사람이 반영한다. 정답이 의심되면 고치지 말고 어느 행·컬럼이 왜 이상한지 보고하고 멈춘다.
- **테스트가 먼저.** 비교 테스트를 실패 상태로 먼저 커밋하고, 구현은 테스트 파일을 고치지 않는다. 같은 실패는 원인을 한 줄로 적고 3회까지만 고친 뒤 멈춰서 보고한다.
- **완료 보고에 포함:** 실행한 명령과 출력, 통과·실패 개수, 감사 결과(입력·출력 행 수, '확인 필요' 건수), `git status` 변경 파일 목록.

## 계획된 구조와 명령

계획(plan.md) 기준이며 현재 모두 존재한다. Python 3.13, 외부 패키지는 openpyxl만(버전 고정, `defusedxml`은 있으면 쓰고 필수 아님), 테스트는 표준 `unittest`.

```bash
python -m unittest                          # 전체 테스트
python -m unittest tests.test_compare       # 단일 테스트 모듈
python .claude/hooks/hook_test.py           # 보호 훅 시험 (FAIL 0이어야 함)
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_demo.ps1 -Serve   # 데모(통합 + 게시판 localhost:3456)
```

- `src/trouble_merge/`: `mapping`(컬럼 대응·양식 판별) → `reader`(보이는 시트만) → `dates` → `check`(확인 필요 판정) → `merge` → `writer`/`cli`, 그리고 `safe_log`, `audit`. 게시판은 `board`(화면 틀 `board_page.html`).
- `config/column_map.csv`(양식별 컬럼 대응), `config/conversion_map.csv`(설비·분류 변환, 종류 열로 구분): UTF-8 BOM CSV. 새 양식은 코드 수정 없이 이 표에 줄만 추가해 처리한다.
- 양식은 헤더로 판별한다(한 양식의 원본 컬럼명이 모두 입력 헤더에 있으면 그 양식). 어느 양식에도 안 맞으면 감사 결과에 '대응 규칙 없음'. 표에 없는 컬럼은 '기타 항목'에 `이름: 값`으로 보관.
- 변환표 일치는 앞뒤 공백·대소문자만 정리한 뒤 정확히 같을 때만. 날짜는 `YYYY-MM-DD`로 통일. 설비·일자·증상이 같은 행은 지우지 않고 '중복 의심' 표시.
- 출력은 `out/`에 쓰며 덮어쓰지 않고 이미 있으면 실행 시각을 붙인다. 열 수 없는 파일은 건너뛰고 감사에 보고하되, 전부 실패하면 통합 파일을 만들지 않고 멈춘다.
- 처리 시간 상한(NFR-005)은 보류 중이므로 처리 시간을 설계 기준으로 삼지 않는다.

## 보호 장치 (훅 구현·등록 완료)

`.claude/settings.json`의 deny(저장소 밖 실제 폴더 3곳, 다운로드·바탕화면)와 PreToolUse 훅 `protect_files.py`(git 추적 파일 차단, 입력·git 상태를 모르면 차단, `realpath`로 경로 해석). 첫 커밋 전에는 모든 파일이 미추적이라 훅이 막지 못하므로, 가짜 데이터·정답·비교 테스트를 만든 직후 커밋해 보호를 켜고, 사람이 보호 파일의 SHA-256 목록을 저장소 밖에 보관해 Phase마다 대조한다. 네이티브 Windows에는 샌드박스가 없어 운영체제 권한(NTFS 권한 또는 별도 계정·WSL)을 병행하고, 그래도 남는 우회 길은 README의 '남은 위험'에 적는다. 근거와 선택 기록은 `docs/security-review-proposal.md`.
