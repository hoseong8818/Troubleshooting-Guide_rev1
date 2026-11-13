@echo off
chcp 65001 >nul
setlocal
rem ================================================================
rem  1. 검사 (FR-025, FR-030): 엑셀의 헤더 행만 읽어 모양(양식)이 몇 종인지, 새 모양이 있는지 보고서로 연다.
rem  아래 네 줄만 고친다(네 실행 파일 모두 같게). 실제 데이터 폴더는 저장소 밖에 두고 실행은 사람이 한다.
rem ================================================================
set "INPUT=C:\mywork\data\sample"
set "CONFIG=C:\mywork\out\sample_cfg"
set "OUT=C:\mywork\out"
set "PORT=3456"
rem ================================================================

cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"

if not exist "%INPUT%" goto no_input

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "RUN=%OUT%\survey_%STAMP%"

echo 검사: %INPUT%
python -m trouble_merge.survey --input "%INPUT%" --config "%CONFIG%" --out "%RUN%"
set "RC=%ERRORLEVEL%"
for %%f in ("%RUN%\survey_*.txt") do start "" notepad "%%f"
echo.
echo 보고서 폴더: %RUN%
echo 위 '새 양식'이 0개가 아니면 2_설정.bat으로 설정하세요. 0개면 바로 3_서버실행.bat을 실행하면 됩니다.
if "%RC%"=="1" echo 일부 파일을 건너뛰었습니다. 보고서의 '건너뛴 파일' 줄을 확인하세요.
if %RC% GEQ 2 echo 읽은 파일이 없거나 설정 오류입니다. 종료 코드 %RC%.
goto done

:no_input
echo 입력 폴더가 없습니다: %INPUT%
echo 맨 위의 INPUT 줄을 고치세요.
set "RC=2"

:done
echo.
pause
exit /b %RC%
