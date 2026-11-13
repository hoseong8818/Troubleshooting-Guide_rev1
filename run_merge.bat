@echo off
chcp 65001 >nul
setlocal
rem ================================================================
rem  트러블슈팅 통합 + 게시판 (T067, T091)
rem  아래 세 줄(입력, 설정, 출력 폴더)만 고친 뒤 더블클릭한다. 넷째 줄 GUI=1이면 컬럼 설정 창을 쓸 수 있고, 0이면 창 없이 통합한다.
rem  실제 데이터 폴더는 저장소 밖에 두고, 실행은 사람이 직접 한다(헌법 원칙 1).
rem ================================================================
set "INPUT=C:\mywork\data\sample"
set "CONFIG=C:\mywork\out\sample_cfg"
set "OUT=C:\mywork\out"
set "GUI=1"
rem ================================================================

cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"

if not exist "%INPUT%" goto no_input
if "%GUI%"=="0" goto check_config
if not exist "%CONFIG%\column_map.csv" goto open_gui
echo 1  기존 설정으로 실행
echo 2  설정 창 열기
choice /c 12 /n /m "번호를 고르세요: "
if errorlevel 2 goto open_gui
goto merge

:open_gui
echo 컬럼 설정 창을 엽니다. 창에서 저장하면 계속합니다.
python -m trouble_merge.setup_gui --input "%INPUT%" --config "%CONFIG%"
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" goto merge
if "%RC%"=="3" goto saved_only
if "%RC%"=="4" goto gui_cancel
echo 설정 창에서 오류가 났습니다. 종료 코드 %RC%.
goto done

:check_config
if not exist "%CONFIG%\column_map.csv" goto no_config

:merge

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "RUN=%OUT%\run_%STAMP%"

echo [1/2] 통합: %INPUT%
python -m trouble_merge --input "%INPUT%" --config "%CONFIG%" --out "%RUN%"
set "RC=%ERRORLEVEL%"
if %RC% GEQ 2 goto merge_failed

echo [2/2] 게시판 만들기
python -m trouble_merge.board --merged "%RUN%\merged.xlsx" --out "%RUN%"
if errorlevel 1 goto board_failed

start "" "%RUN%\board.html"
echo.
echo 완료. 결과 폴더: %RUN%
if "%RC%"=="1" echo 일부 파일이나 시트를 읽지 못했습니다. 감사 결과 audit_*.txt와 확인 필요 목록 check_list_*.csv를 확인하세요.
goto done

:no_input
echo 입력 폴더가 없습니다: %INPUT%
echo run_merge.bat 맨 위의 INPUT 줄을 고치세요.
set "RC=2"
goto done

:no_config
echo 설정 파일이 없습니다: %CONFIG%\column_map.csv
echo run_merge.bat 맨 위의 CONFIG 줄을 고치거나 GUI=1로 두고 설정 창에서 만드세요.
set "RC=2"
goto done

:saved_only
echo 설정을 저장했습니다. 통합은 하지 않았습니다: %CONFIG%
set "RC=0"
goto done

:gui_cancel
echo 설정 창을 닫았습니다. 아무것도 바꾸지 않았습니다.
set "RC=0"
goto done

:merge_failed
echo 통합에 실패했습니다. 종료 코드 %RC%. 결과 폴더의 감사 결과를 확인하세요: %RUN%
goto done

:board_failed
echo 게시판을 만들지 못했습니다. 결과 폴더: %RUN%
set "RC=2"
goto done

:done
echo.
pause
exit /b %RC%
