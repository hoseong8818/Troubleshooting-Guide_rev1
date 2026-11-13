@echo off
chcp 65001 >nul
setlocal
rem ================================================================
rem  트러블슈팅 통합 + 게시판 (T067)
rem  아래 세 줄만 고친 뒤 더블클릭한다.
rem  실제 데이터 폴더는 저장소 밖에 두고, 실행은 사람이 직접 한다(헌법 원칙 1).
rem ================================================================
set "INPUT=C:\mywork\data\sample"
set "CONFIG=C:\mywork\out\sample_cfg"
set "OUT=C:\mywork\out"
rem ================================================================

cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"

if not exist "%INPUT%" goto no_input
if not exist "%CONFIG%\column_map.csv" goto no_config

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
echo run_merge.bat 맨 위의 CONFIG 줄을 고치세요.
set "RC=2"
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
