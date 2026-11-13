@echo off
chcp 65001 >nul
setlocal
rem ================================================================
rem  4. 서버 종료 (FR-030): 그 포트를 쓰는 python 서버만 끈다.
rem  아래 네 줄만 고친다(네 실행 파일 모두 같게). 여기서는 PORT만 쓴다.
rem ================================================================
set "INPUT=C:\mywork\data\sample"
set "CONFIG=C:\mywork\out\sample_cfg"
set "OUT=C:\mywork\out"
set "PORT=3456"
rem ================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\server_ctl.ps1" -Action stop -Port %PORT%
echo.
pause
