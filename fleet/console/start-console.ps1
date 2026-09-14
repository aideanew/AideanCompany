# AideanAgentFleet 控制台一键启动
# 网页地址: http://127.0.0.1:5000 （仅本机可访问）
$env:PYTHONIOENCODING = "utf-8"
Start-Process powershell -ArgumentList '-NoExit','-Command',
  '& "C:\Program Files\Python313\python.exe" "E:\Code\AideanCompany\fleet\console\console.py"'
Write-Host "控制台启动中 → http://127.0.0.1:5000"
Write-Host "舰队网关请用控制台首页的 [启动舰队] 按钮（现在是脱离进程组模式，控制台重启不影响舰队）"
