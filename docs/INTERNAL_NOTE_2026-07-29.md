# 2026-07-29 内部踩坑记录 — Multi-source-Resonance-1 v3.1 部署

> **状态**: 中止 (Owner 选项 E) · 等待作者修 issue 后再继续
> **操作员**: OpenClaw main session (trim.openclaw)
> **时间**: 2026-07-29 04:17-04:36 CST (Asia/Shanghai)
> **范围**: 本地新仓库部署, 仅 touch `Multi-source-Resonance-1/` 目录, 不影响任何运行中服务

## TL;DR

新仓库 `raymodny-ai/Multi-source-Resonance-1` (HEAD c2d375c) 是 v3.1 全栈重写, 但**关键 16 个 fetcher 没从旧 `base_alt` 迁到新 `base`**, 导致 `collect-manual` 永远 0 success。Owner 决定**中止部署 + 提 issue**, 不本地修补。

## 已完成

| 步骤 | 状态 | 备注 |
|---|---|---|
| `git clone` | ✅ | 4.17 CST |
| `uv venv --python 3.12 .venv` | ✅ | Python 3.12.13 |
| `uv pip install -r requirements.txt` | ✅ | 21 包 |
| `uv pip install pytest pytest-asyncio pytest-cov` | ✅ | dev 依赖补 |
| `cp .env.example .env` | ✅ | key 留空, 走 mock |
| `pip` 端口冲突 (8524 占用误判) | ⚠️ | 真相是 `reload=True` 父子双绑, 改 `reload=False` + `PORT=8525` 解决 |
| 后端启动 FastAPI 8525 | ✅ | `python -m backend.main`, PID 2058956 |
| `/api/health` 200 | ✅ | version=3.1.0 |
| `/api/auth/login admin/***` 200 | ✅ | 拿到 JWT |
| `/api/tickers` 6 symbol | ✅ | SPX/SPY/QQQ/IWM/NDX/VIX |
| `/api/gex/SPY/dashboard-view?strikes_limit=5` 422 | ⚠️ | range `ge=10` 太严 |
| `/api/system/source-status` 200 | ✅ | 21 source 全 offline (空库) |
| `POST /api/system/collect-manual` 200, `success_count=0` | ❌ | **主 bug** |
| `/docs` 404 | ❌ | Swagger UI 未挂载 |
| `/openapi.json` 404 | ❌ | 同上 |
| 后端干净关停 | ✅ | SIGTERM → lifespan → `Application shutdown complete` |
| `git checkout -- backend/` 还原 18 文件改动 | ✅ | 100% 原样 |
| Issue 草稿写完 | ✅ | `docs/ISSUE_v3.1_fetcher_migration_incomplete.md` |

## 未做 (决定中止)

- ❌ pytest 全量回归 — 0/0 启动时跑, 进程未完成
- ❌ Vite 前端 (npm install) — 没启
- ❌ docker-compose 部署 — 没试
- ❌ 任何 git commit — 0 commit 0 push
- ❌ Push issue 到 GitHub — 等 Owner 决定账号/GH_TOKEN 用谁的

## 阻塞根因 (三件套)

### 1. 迁移半成品

```
backend/fetchers/base.py       # 新版, (config, db) 签名
backend/fetchers/base_alt.py   # 旧版, () 签名, 标注 "To migrate"
backend/fetchers/__init__.py   # export BaseFetcher → 走 base_alt ❌
```

- 5 个 fetcher (gexmetrix/axlfi/cboe/vix/yfinance) 完整迁移, 走 base
- 16 个 fetcher 仍是 base_alt, 没 `source_name` / `_mock_data`
- 切换 `__init__.py` 后 16 个**实例化即 TypeError**

### 2. main.py 缺 fetchers 注入

`Pipeline(config, event_bus)` 第三个参数 `fetchers=None`, 默认 `[]`。即便修了 base, 也不会自动注册 fetcher — 需显式 list 注入。

### 3. uvicorn reload 模式 (4-5 月 dev 习惯陷阱)

`main.py` 末尾 `uvicorn.run(..., reload=True)`, watchfiles 会**父子两个进程**绑同一端口, 后台 nohup 起会**秒秒被 reloader 撞死**。生产模式必须 `reload=False`。

我本地 patch 时改了 main.py 调 `reload=False` — 全部 revert 了, 留给作者。

## 我曾尝试但放弃的本地 patch (已全部 revert)

| 修改 | 文件 | revert 状态 |
|---|---|---|
| `from base_alt → base` 替换 (16 文件) | `backend/fetchers/*_fetcher.py` | ✅ git checkout -- backend/ |
| `__init__.py` import 改 base | `backend/fetchers/__init__.py` | ✅ git checkout -- backend/ |
| 新增 `_build_default_fetchers()` 函数 | `backend/main.py` | ✅ git checkout -- backend/ |
| Pipeline 调用传 fetchers= | `backend/main.py` | ✅ git checkout -- backend/ |
| `reload=True → False` | `backend/main.py` | ✅ git checkout -- backend/ |

**当前 git status**: clean (无 working tree 改动, .venv/.env/logs/data 都 .gitignore 命中)

## 后人接手指南 (如果 Owner 改主意, 走 A/B/C 选项时)

### Option A — 仅 mock mode 看 schema (30 min)

```python
# backend/fetchers/__init__.py 改 import 到 base
# 然后给 16 个未迁移 fetcher 每个加 (共 5-10 行/fetcher):
#   def __init__(self, config, db=None):
#       self.config = config
#       self.db = db
#       self.logger = logging.getLogger(...)
#   @property
#   def source_name(self):
#       return "<Class Name>"
#   def _mock_data(self):
#       return self._generate_mock_data() if hasattr(self, '_generate_mock_data') else {}
# 然后 backend/main.py 的 _build_default_fetchers() 用 21 个 list
```

### Option B — 完整迁移 (2-3h, 破坏性)

```bash
# 每个未迁移 fetcher:
#   1. 改 __init__ 签名 (config, db=None), 调 super
#   2. _generate_mock_data → _mock_data
#   3. 加 @property source_name
#   4. (可选) 删 base_alt.py
# 完成后跑 pytest backend/tests/ -v 验证
```

### Option C — 等作者

- 在 GitHub 提 issue (本目录 `docs/ISSUE_v3.1_fetcher_migration_incomplete.md` 是草稿)
- 标签: `bug` `priority:high` `blocker`
- 关注 raymodny-ai/Multi-source-Resonance-1 仓库 PR 进度

## 关键端口/路径备忘

| 项 | 值 | 备注 |
|---|---|---|
| 仓库路径 | `/vol1/@apphome/trim.openclaw/data/workspace/Multi-source-Resonance-1` | 跟旧 `Multi-source-Resonance/` 并存, 不冲突 |
| 后端端口 | 8525 (启用时) | 8524 被旧 MSR 7-25 关闭后 hold (socket/port 状态 quirk), ss/netstat 都看不到, 但 bind 报 EADDRINUSE, 5-60s 自动释放 |
| 前端端口 | 5173 (Vite dev) | 未启,空 |
| 数据库 | `./data/resonance.db` | SQLite WAL, 自动建表 |
| 默认 admin | `admin` / `***` | auth.py:60 写死 |
| JWT secret | `.env` 的 `JWT_SECRET` | **生产前必改** |
| Python | 3.12.13 (uv venv) | 系统是 3.11.2, 需 3.12+ |

## 没动过的东西 (sanity check)

- ✅ 旧 `Multi-source-Resonance/` 完全没碰, 退役标 (STATUS.md/DEPRECATED.md/.DEPRECATED) 保留
- ✅ 旧 MSR cron `ee9c768b` 还在跑, 22:00 ET 采到旧 SQLite
- ✅ 没建任何 OpenClaw cron 关联新 MSR-1
- ✅ 没动 workspace 任何全局配置
- ✅ 没动 GH_TOKEN, 没 push 任何东西
- ✅ /vol1 空间没变化 (venv ~600MB, .git clone ~5MB, 已 .gitignore 不会污染)

## 给 Owner 的下一步建议

1. **现在**: 等作者 (raymodny-ai) 修 issue, 通常 1-3 天有回应
2. **作者修完**: 重新 `git pull` + 跑 issue 草稿里的验证命令, 看 `success_count >= 1` 即可
3. **作者没修, Owner 改主意**: 走 Option A (mock mode 看 schema), 我已写好 30min patch 模板
4. **Owner 完全放弃这个仓库**: `rm -rf Multi-source-Resonance-1`, 释放 ~600MB

---

> **教训**: 新仓库"git clone + 跑 README 9.2-9.5"是最低门槛验证, README 9.2 没明说"需要改 main.py 注入 fetchers"也没明说"16 个 fetcher 还没迁完" — 看似齐全, 实际**装上就跑不通**。任何新仓库第一次本地部署, **先 `pytest tests/` 跑通** 再 `python -m x.main`, 跳过测试直接启服务会被代码 0/0 假象迷惑。
