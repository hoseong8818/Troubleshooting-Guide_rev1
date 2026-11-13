# 데모 한 번에 실행: 가짜 데이터와 예시 데이터를 통합하고 게시판을 만든 뒤 예시 데이터 게시판을 연다.
#
# 사용(저장소 루트 어디서든):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_demo.ps1
#
# - 예시 데이터(data\sample, 전부 가상)가 없으면 tools\make_sample_data.py로 만든다(고정 시드라 항상 같은 결과).
# - 예시 데이터용 설정(양식 4종, 설비·분류 목록, 원인 미상 단어)은 out\sample_cfg에 만든다. 저장소의 config\는 건드리지 않는다.
# - 결과는 매번 새 폴더 out\run_<시각>에 만든다. 이전 결과를 덮어쓰지 않는다.
# - 실제 데이터에는 이 스크립트를 쓰지 않는다. 실제 데이터는 1_검사.bat ~ 4_서버종료.bat의 맨 위 네 줄을 고쳐 사람이 직접 실행한다.
# - -Serve를 붙이면 파일로 여는 대신 http://localhost:3456 으로 띄운다(tools\serve_board.ps1).
# - -NoOpen을 붙이면 브라우저도 서버도 띄우지 않고 결과만 만든다(tools\build_site.ps1이 쓴다).
# - -Sample <폴더>로 예시 데이터 위치를 바꿀 수 있다(기본 data\sample).
param([switch]$Serve, [switch]$NoOpen, [string]$Sample = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = Join-Path $root "src"
$sample = if ($Sample) { $Sample } else { Join-Path $root "data\sample" }
$cfg = Join-Path $root "out\sample_cfg"
$run = Join-Path $root ("out\run_" + (Get-Date -Format "yyyyMMdd_HHmmss"))

if (-not (Test-Path $sample)) {
  Write-Host "예시 데이터를 만듭니다: data\sample"
  python tools\make_sample_data.py
  if ($LASTEXITCODE -ne 0) { throw "예시 데이터 생성 실패" }
}

# 예시 데이터용 설정
New-Item -ItemType Directory -Force $cfg | Out-Null
$forms = @(
  @("S_A", "설비코드", "발생일자", "증상", "원인", "조치내용", "부품분류", "트러블이력"),
  @("S_B", "호기", "일시", "현상", "고장원인", "처리내용", "부품구분", "고장기록"),
  @("S_C", "Equipment ID", "Date", "Problem", "Root Cause", "Action Taken", "Part Category", "Trouble_Log"),
  @("S_D", "설비번호", "접수일", "이상내용", "원인분석", "대책", "부품유형", "이력")
)
$std = "설비", "일자", "증상", "원인", "조치", "분류"
$lines = @("양식,원본 컬럼명,표준 컬럼,헤더행,시트")
foreach ($f in $forms) {
  for ($i = 0; $i -lt 6; $i++) {
    $sheet = ""
    if ($i -eq 0) { $sheet = $f[7] }
    $lines += ("{0},{1},{2},,{3}" -f $f[0], $f[$i + 1], $std[$i], $sheet)
  }
}
$bom = New-Object Text.UTF8Encoding $true
[IO.File]::WriteAllText((Join-Path $cfg "column_map.csv"), (($lines -join "`r`n") + "`r`n"), $bom)

$conv = @("종류,원래 값,표준 값")
Import-Csv (Join-Path $sample "설비목록.csv") -Encoding UTF8 | ForEach-Object { $conv += "설비,$($_.설비코드),$($_.설비코드)" }
Import-Csv (Join-Path $sample "에러코드표.csv") -Encoding UTF8 | ForEach-Object { $_.부품분류 } | Sort-Object -Unique |
  ForEach-Object { $conv += "분류,$_,$_" }
foreach ($word in @("알수없음", "원인불명", "미확인", "원인 파악 못함", "부품 교체 후 정상 작동", "모름", "?")) {
  $conv += "원인 미상,$word,"
}
[IO.File]::WriteAllText((Join-Path $cfg "conversion_map.csv"), (($conv -join "`r`n") + "`r`n"), $bom)

# 통합과 게시판(종료 코드 1은 '일부 확인 필요'라 정상 진행)
$ErrorActionPreference = "Continue"
Write-Host "== 가짜 데이터(data\fake) =="
python -m trouble_merge --input data\fake --config config --out (Join-Path $run "fake")
python -m trouble_merge.board --merged (Join-Path $run "fake\merged.xlsx") --out (Join-Path $run "fake")
Write-Host "== 예시 데이터(data\sample) =="
python -m trouble_merge --input $sample --config $cfg --out (Join-Path $run "sample")
python -m trouble_merge.board --merged (Join-Path $run "sample\merged.xlsx") --out (Join-Path $run "sample")

$audit = Get-ChildItem (Join-Path $run "sample") -Filter "audit_*.txt" | Select-Object -First 1
if ($audit) {
  Select-String -Path $audit.FullName -Pattern "^(입력 행 수|출력 행 수|행 수 일치|확인 필요 건수|확인 필요 이유별 건수|중복 의심 건수)" |
    ForEach-Object { $_.Line }
}
Write-Host ("결과 폴더: " + $run)
if ($NoOpen) {
  Write-Host "-NoOpen: 브라우저도 서버도 띄우지 않습니다."
} elseif ($Serve) {
  & (Join-Path $PSScriptRoot "serve_board.ps1") -Dir (Join-Path $run "sample")
} else {
  Start-Process (Join-Path $run "sample\board.html")
}
