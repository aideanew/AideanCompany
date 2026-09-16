# 密钥外置清单

> 状态：已隔离。原值已从设计文档清除，不记录本文件。
> 规则：任何 `.md/.json/.txt/.log/report/transcript` 不得出现明文 Key。Key 只进入 `.env` 或 secret store。
> 动作：原 Key 视为可能泄露，请在各平台后台逐一轮换后再恢复模型调用。

## 模板（只允许这种形状，不要贴真值）

```env
V3_API_KEY=
BAI_API_KEY=
NVIDIA_API_KEY=
SENSNOVA_API_KEY=
AGNES_API_KEY=
AMD_API_KEY=
MODELSCOPE_API_KEY=
```

## 各平台轮换状态

| 平台 | 原出处 | 当前状态 | 下一步 |
|---|---|---|---|
| V3 | `初始设计/核心.md` | 已外置 | 平台后台撤销旧 Key，新 Key 写入 `.env` |
| BAI | `初始设计/核心.md` | 已外置，401 已知 | 更新 Key 或确认代理 |
| Nvidia | `初始设计/核心.md` | 已外置 | 后台撤销并重新生成 |
| Sensenova | `初始设计/核心.md` | 已外置 | 后台撤销并重新生成 |
| agnes | `初始设计/核心.md` | 已外置 | 后台撤销并重新生成 |
| AMD | `初始设计/核心.md` | 已外置 | 后台撤销并重新生成 |
| ModelScope | `初始设计/核心.md` | 已外置 | 后台撤销并重新生成 |

## 校验方式

实施验证阶段执行：

```powershell
python fleet/tools/verify/secret_scan.py
```

期望：`0 findings`。该脚本尚未创建，列为后续阶段交付物。
