$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$baseUrl = "https://raw.githubusercontent.com/stseww3/jvfoedfve/1be4d90b347b312162f909b477263c7ad9417511/tsb/squad"
$files = @(
  "headless-bot.mjs",
  "tsb-team-squad.mjs",
  "spawn-coordinator.mjs",
  "v27-team-live.js",
  "page.js",
  "live_game_js.js",
  "live_dictionary.json"
)

foreach ($f in $files) {
  if (!(Test-Path $f) -or ((Get-Item $f).Length -lt 100)) {
    Write-Host "Downloading $f ..."
    Invoke-WebRequest -Uri "$baseUrl/$f" -OutFile $f -UseBasicParsing
  }
}

Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -match "tun_socks5\.py" -or $_.CommandLine -match "tsb-team-squad\.mjs"
} | ForEach-Object {
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host "Starting GProxy SOCKS5 bridge (tun_socks5.py)..."
Start-Process -FilePath "python" -ArgumentList "tun_socks5.py" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "tun_socks5.log" -RedirectStandardError "tun_socks5.err.log"
Start-Sleep -Seconds 2

$chromePaths = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)
$chromeExe = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

foreach ($cfg in @(@{Port=9225; Socks=10801}, @{Port=9226; Socks=10802})) {
  $p = $cfg.Port
  $s = $cfg.Socks
  $listening = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if (!$listening -and $chromeExe) {
    $profDir = Join-Path $PSScriptRoot "chrome_donor_$p"
    $args = @(
      "--remote-debugging-port=$p",
      "--remote-allow-origins=*",
      "--user-data-dir=`"$profDir`"",
      "--proxy-server=socks5://127.0.0.1:$s",
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-background-timer-throttling",
      "--disable-backgrounding-occluded-windows",
      "--disable-renderer-backgrounding",
      "--window-size=420,360",
      "https://territorial.io/"
    )
    Write-Host "Starting Donor Browser on :$p ..."
    Start-Process -FilePath $chromeExe -ArgumentList ($args -join " ") -WindowStyle Minimized
  }
}

Start-Sleep -Seconds 5

Write-Host "Starting 8-Bot Squad (tsb-team-squad.mjs)..."
Start-Process -FilePath "node" -ArgumentList "tsb-team-squad.mjs" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "tsb-team-squad.log" -RedirectStandardError "tsb-team-squad.err.log"

Start-Sleep -Seconds 6
if (Test-Path "tun_socks5.log") { Get-Content "tun_socks5.log" -Tail 10 }
if (Test-Path "tsb-team-squad.log") { Get-Content "tsb-team-squad.log" -Tail 25 }
if (Test-Path "tsb-team-squad.err.log") { Get-Content "tsb-team-squad.err.log" -Tail 15 }
