@echo off
chcp 65001 >nul
setlocal
rem ================================================================
rem  3. 서버 실행 (FR-029, FR-030): 지금 설정으로 통합하고 게시판을 연다.
rem  엑셀이 늘어나면 이것만 다시 실행하면 된다(켜진 서버는 끄고 다시 켠다).
rem  아래 네 줄만 고친다(네 실행 파일 모두 같게). 실제 데이터 폴더는 저장소 밖에 두고 실행은 사람이 한다.
rem ================================================================
set "INPUT=C:\mywork\data\sample"
set "CONFIG=C:\mywork\out\sample_cfg"
set "OUT=C:\mywork\out"
set "PORT=3456"
rem ================================================================

cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
set "CTL=powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\server_ctl.ps1""

if not exist "%INPUT%" goto no_input
if not exist "%CONFIG%\column_map.csv" goto no_config

%CTL% -Action stop -Port %PORT%
if errorlevel 1 goto done

echo 통합하고 서버를 켭니다. 파일이 많으면 몇 분 걸립니다(작은 창으로 따로 뜹니다).
start "트러블슈팅 서버" /min python -u -m trouble_merge.server --input "%INPUT%" --config "%CONFIG%" --out "%OUT%" --port %PORT% --merge
%CTL% -Action wait -Port %PORT% -Seconds 900
if errorlevel 1 goto no_server

start "" "http://127.0.0.1:%PORT%/"
echo 게시판: http://127.0.0.1:%PORT%/
echo 결과 폴더: %OUT%\run_*  (가장 최근 폴더의 감사 결과 audit_*.txt)
goto done

:no_input
echo 입력 폴더가 없습니다: %INPUT%
echo 맨 위의 INPUT 줄을 고치세요.
goto done

:no_config
echo 설정이 없습니다: %CONFIG%\column_map.csv
echo 먼저 2_설정.bat으로 설정을 저장하세요.
goto done

:no_server
echo 서버가 열리지 않았습니다. '트러블슈팅 서버' 창의 메시지를 확인하세요.

:done
echo.
pause
