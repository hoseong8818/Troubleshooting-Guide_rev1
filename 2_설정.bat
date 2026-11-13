@echo off
chcp 65001 >nul
setlocal
rem ================================================================
rem  2. 설정 (FR-029, FR-030): 서버가 꺼져 있으면 켜고 브라우저에 설정 화면을 연다.
rem  화면에서 '저장하고 통합해서 게시판 보기'를 누르면 통합 후 게시판으로 넘어간다.
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

%CTL% -Action running -Port %PORT%
if not errorlevel 1 goto open

echo 서버를 켭니다(작은 창으로 따로 뜹니다. 그 창을 닫으면 서버가 꺼집니다).
start "트러블슈팅 서버" /min python -u -m trouble_merge.server --input "%INPUT%" --config "%CONFIG%" --out "%OUT%" --port %PORT%
%CTL% -Action wait -Port %PORT% -Seconds 60
if errorlevel 1 goto no_server

:open
start "" "http://127.0.0.1:%PORT%/setup"
echo 설정 화면: http://127.0.0.1:%PORT%/setup
goto done

:no_input
echo 입력 폴더가 없습니다: %INPUT%
echo 맨 위의 INPUT 줄을 고치세요.
goto done

:no_server
echo 서버가 열리지 않았습니다. '트러블슈팅 서버' 창의 메시지를 확인하세요.

:done
echo.
pause
