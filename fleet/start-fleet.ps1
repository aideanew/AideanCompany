# AideanAgentFleet 一键启动 v3（8人舰队 + Manager + 控制台 + 贪吃蛇演示服务）
# 用法：右键"使用 PowerShell 运行"
# 端口：5000控制台 9900Manager 9901/9908前端 9902/9909/9910后端 9903测试 9907产品 9911审查
#      5410贪吃蛇API 5411贪吃蛇页面（按需可注释掉）

$env:HERMES_ACCEPT_HOOKS = "1"
$py = "C:\Program Files\Python313\python.exe"
$fleet = "E:\Code\AideanCompany\fleet"

# —— 控制台 ——
Start-Process powershell -ArgumentList '-NoExit','-Command', "& '$py' '$fleet\console\console.py'"

# —— Manager 网关 ——
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes gateway run'

# —— 7 人舰队（产品/前端x2/后端x3/测试）+ 审查员 ——
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p pm-1 gateway run'
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p worker-a gateway run'
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p fe-2 gateway run'
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p worker-b gateway run'
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p be-2 gateway run'
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p be-3 gateway run'
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p worker-c gateway run'
Start-Process powershell -ArgumentList '-NoExit','-Command','hermes -p reviewer-1 gateway run'

# —— 贪吃蛇演示（不需要时注释掉下面两行）——
Start-Process powershell -ArgumentList '-NoExit','-Command','node E:\Demo\Test0912\backend\server.js'
Start-Process powershell -ArgumentList '-NoExit','-Command','& "C:\Program Files\Python313\python.exe" -m http.server 5411 --directory E:\Demo\Test0912\frontend'

Write-Host ""
Write-Host "舰队启动中（11 进程）："
Write-Host "  控制台    http://127.0.0.1:5000"
Write-Host "  Manager   9900 | pm-1 9907 | worker-a 9901 | fe-2 9908"
Write-Host "  worker-b  9902 | be-2 9909 | be-3 9910 | worker-c 9903 | reviewer-1 9911"
Write-Host "  贪吃蛇    http://127.0.0.1:5411 (API 5410)"
Write-Host "自检：curl.exe http://127.0.0.1:9900/.well-known/agent-card.json"
