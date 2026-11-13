@echo off
chcp 65001 >nul
setlocal
rem ================================================================
rem  헤더 조사 보고서 (T077, FR-025)
rem  아래 세 줄만 고친 뒤 더블클릭한다. 엑셀의 헤더 행만 읽고 셀 값은 읽지 않는다.
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
set "RUN=%OUT%\survey_%STAMP%"

echo 헤더 조사: %INPUT%
python -m trouble_merge.survey --input "%INPUT%" --config "%CONFIG%" --out "%RUN%"
set "RC=%ERRORLEVEL%"

for %%f in ("%RUN%\survey_*.txt") do start "" notepad "%%f"
echo.
echo 결과 폴더: %RUN%
if "%RC%"=="1" echo 일부 파일을 건너뛰었습니다. 보고서의 '건너뛴 파일' 줄을 확인하세요.
if %RC% GEQ 2 echo 읽은 파일이 없거나 설정 오류입니다. 종료 코드 %RC%.
goto done

:no_input
echo 입력 폴더가 없습니다: %INPUT%
echo run_survey.bat 맨 위의 INPUT 줄을 고치세요.
set "RC=2"
goto done

:no_config
echo 설정 파일이 없습니다: %CONFIG%\column_map.csv
echo run_survey.bat 맨 위의 CONFIG 줄을 고치세요.
set "RC=2"
goto done

:done
echo.
pause
exit /b %RC%
