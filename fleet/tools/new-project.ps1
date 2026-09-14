# AideanAgentFleet · 新项目一键脚手架
# 用法：
#   .\new-project.ps1 -Name "我的新项目" -Dir "E:\Demo\my-app"
# 效果：建目录结构 + 需求契约模板 + git 仓库 + 注册进控制台项目看板
# 之后：打开 hermes chat 对 Manager 说目标即可（见方案文档 §4 六步流程）
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][string]$Dir
)
$ErrorActionPreference = "Stop"

# 0) 白名单校验（与控制台 ALLOWED_ROOTS 对齐）
$allowed = @("E:\Demo\", "E:\Code\AideanCompany\fleet\projects\")
$ok = $false
foreach ($a in $allowed) { if ($Dir.StartsWith($a, [StringComparison]::OrdinalIgnoreCase)) { $ok = $true; break } }
if (-not $ok) { throw "目录必须在白名单内（二选一）：E:\Demo\ 或 E:\Code\AideanCompany\fleet\projects\（控制台派工会拒收白名单外目录）" }

# 1) 目录结构（与契约铁律对齐：src\frontend + src\backend 预建，避免前后端各自发明目录）
New-Item -ItemType Directory -Force -Path "$Dir\docs", "$Dir\src\frontend", "$Dir\src\backend" | Out-Null

# 2) 需求契约模板（Manager 拆解与验收全靠它，务必填写）
if (-not (Test-Path "$Dir\README.md")) {
@"
# $Name

## 目标
（一句话说清要做什么）

## 目录与分工约束（铁律）
- src\frontend\ 只允许前端角色改动；src\backend\ 只允许后端角色改动；严禁改动任务范围外文件
- 端口约定：（填写本项目专用端口，先 netstat 确认空闲，严禁他用；贪吃蛇已占 5410/5411）

## 接口/页面契约（前后端唯一对接点）
- （方法 路径 → 请求/响应结构；示例见启动说明或旧项目 README）

## 验收命令（Manager 逐条机器执行，这是判定完成的唯一标准）
1.（如：node --check src/backend/server.js）
2.（如：curl.exe http://127.0.0.1:PORT/api/... 返回 JSON 数组）
3.（推荐 grep 模式：grep:src/frontend/index.html:关键词1,关键词2 —— 机器门直读 UTF-8，最稳）

## 明确不做
-（边界，防止范围膨胀）
"@ | Out-File "$Dir\README.md" -Encoding utf8
}

# 3) git 仓库（M3 分支隔离的基础）
if (-not (Test-Path "$Dir\.git")) {
  $ErrorActionPreference = "Continue"
  git -C $Dir init 2>&1 | Out-Null
  git -C $Dir add -A 2>&1 | Out-Null
  git -C $Dir commit -m "init: project scaffold" 2>&1 | Out-Null
  $ErrorActionPreference = "Stop"
}

# 4) 注册进控制台项目看板（网页立即可见，可向其派任务）
$py = "C:\Program Files\Python313\python.exe"
$code = @"
import json, pathlib, datetime, sys
name, ws = sys.argv[1], sys.argv[2]
p = pathlib.Path('E:/Code/AideanCompany/fleet/console/state/projects.json')
d = json.loads(p.read_text(encoding='utf-8'))
if not any(x['name'] == name for x in d['projects']):
    pid = 'P-%03d' % d['next_id']
    d['projects'].append({'pid': pid, 'name': name, 'workspace': ws,
                          'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    d['next_id'] += 1
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('registered', pid, name)
else:
    print('already registered', name)
"@
$code | & $py - $Name $Dir

Write-Host ""
Write-Host "✅ 项目脚手架完成：" 
Write-Host "   目录: $Dir（docs\ src\ README.md 契约模板 .git）"
Write-Host "   控制台: http://127.0.0.1:5000 → 项目页可见"
Write-Host "下一步："
Write-Host "  1. 填写 $Dir\README.md 的目标/契约/验收命令"
Write-Host "  2. hermes --yolo chat 对 Manager 说目标（或控制台任务页派工）"
Write-Host "  3. 验收命令建议用 grep:相对路径:令牌 模式（机器门直读 UTF-8，无编码坑）"
