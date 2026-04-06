# Windows计划任务设置脚本
# Setup scheduled tasks for 24/7 operation

$ErrorActionPreference = "Stop"

$scriptDir = "C:\Users\Administrator\.qclaw\workspace\quant-24x7"
$pythonExe = "python"
$taskPrefix = "AStockQuant"

Write-Host "=== A股量化系统 - 任务计划设置 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 早盘选股 (每天9:15)
Write-Host "设置早盘选股任务..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$scriptDir\run_service.py`"" -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -Daily -At "09:15"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "$taskPrefix-Morning" -Action $action -Trigger $trigger -Settings $settings -Description "A股早盘选股" -Force

# 2. 盘中监控 (每30分钟)
Write-Host "设置盘中监控任务..." -ForegroundColor Yellow
$trigger = New-ScheduledTaskTrigger -Once -At "09:30" -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Hours 6)
Register-ScheduledTask -TaskName "$taskPrefix-Monitor" -Action $action -Trigger $trigger -Settings $settings -Description "A股盘中监控" -Force

# 3. 尾盘总结 (每天15:05)
Write-Host "设置尾盘总结任务..." -ForegroundColor Yellow
$trigger = New-ScheduledTaskTrigger -Daily -At "15:05"
Register-ScheduledTask -TaskName "$taskPrefix-Evening" -Action $action -Trigger $trigger -Settings $settings -Description "A股尾盘总结" -Force

# 4. 每周回测 (周日20:00)
Write-Host "设置每周回测任务..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$scriptDir\auto_runner.py`" backtest" -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "20:00"
Register-ScheduledTask -TaskName "$taskPrefix-Backtest" -Action $action -Trigger $trigger -Settings $settings -Description "A股每周回测" -Force

Write-Host ""
Write-Host "=== 任务设置完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "查看任务:" -ForegroundColor Cyan
Get-ScheduledTask -TaskName "$taskPrefix*" | Select-Object TaskName, State, TaskPath | Format-Table

Write-Host ""
Write-Host "立即运行一次:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName `"$taskPrefix-Morning`""
Write-Host ""
Write-Host "查看日志:" -ForegroundColor Cyan
Write-Host "  Get-Content `"$scriptDir\logs\service_*.log`" -Tail 50"
