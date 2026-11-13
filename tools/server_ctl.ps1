# 실행 파일(2_설정, 3_서버실행, 4_서버종료)이 쓰는 서버 도우미(FR-030). 사람이 bat으로 실행한다.
#   -Action running : 그 포트를 듣는 프로그램이 있으면 종료 코드 0, 없으면 1
#   -Action stop    : 그 포트를 듣는 python만 끈다(다른 프로그램이면 끄지 않는다)
#   -Action wait    : 서버가 열릴 때까지 기다린다(-Seconds초). 열리면 0, 아니면 1
param(
  [ValidateSet("running", "stop", "wait")][string]$Action,
  [int]$Port = 3456,
  [int]$Seconds = 900
)
$ErrorActionPreference = "SilentlyContinue"

function Listening {
  return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

if ($Action -eq "running") {
  if ((Listening).Count -gt 0) { exit 0 } else { exit 1 }
}

if ($Action -eq "stop") {
  $conns = Listening
  if ($conns.Count -eq 0) { Write-Host "켜져 있는 서버가 없습니다."; exit 0 }
  foreach ($c in $conns) {
    $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -like "python*") {
      Stop-Process -Id $p.Id -Force
      Write-Host "서버를 껐습니다."
    } else {
      Write-Host "$Port 포트를 python이 아닌 프로그램이 쓰고 있어 끄지 않았습니다."
      exit 1
    }
  }
  exit 0
}

if ($Action -eq "wait") {
  $deadline = (Get-Date).AddSeconds($Seconds)
  while ((Get-Date) -lt $deadline) {
    if ((Listening).Count -gt 0) { exit 0 }
    Start-Sleep -Milliseconds 500
  }
  exit 1
}
