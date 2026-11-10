$ProgressPreference = 'SilentlyContinue'
Set-Location $PSScriptRoot
Remove-Item -Path "tsb-wait-npl.flag" -Force -ErrorAction SilentlyContinue

$base = "https://raw.githubusercontent.com/stseww3/jvfoedfve/1ec3ad29e4fbc3bb303faa4c0938edba6a8cc4c6/tsb/squad"
Invoke-WebRequest -Uri "$base/tsb-team-squad.mjs" -OutFile "tsb-team-squad.mjs" -UseBasicParsing
Invoke-WebRequest -Uri "$base/headless-bot.mjs" -OutFile "headless-bot.mjs" -UseBasicParsing

Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
$cmdNode = "cmd.exe /c `"`"$PSScriptRoot\node\node.exe`" `"$PSScriptRoot\tsb-team-squad.mjs`" > `"$PSScriptRoot\tsb-team-squad.log`" 2> `"$PSScriptRoot\tsb-team-squad.err.log`"`""
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdNode; CurrentDirectory = $PSScriptRoot } | Out-Null
Write-Host "Updated to 1ec3ad2 & restarted 5-brother v27team!"
