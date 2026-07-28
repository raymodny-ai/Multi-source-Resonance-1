# [v3.1] Fetcher 迁移半成品 — `base_alt` → `base` 未完成,导致 POST /api/system/collect-manual 返回 0 success

## 摘要 (TL;DR)

`Multi-source-Resonance v3.1` 仓库 `c2d375c` 引入新版 `BaseFetcher` (`backend/fetchers/base.py`, 签名 `(config, db)`, 抽象方法 `source_name` + `fetch` + `_mock_data`),并完成对 **5 个 fetcher** 的迁移 (GEXMetrix / AXLFI / CBOE / VIX / YFinance)。但 **剩 16 个 fetcher** 仍继承自旧版 `backend/fetchers/base_alt.py` (签名 `()`, 抽象方法只有 `fetch`)。同时 `backend/fetchers/__init__.py` 的 `BaseFetcher` 导出指向 `base_alt`,与迁移目标相反 — 直接导致 `POST /api/system/collect-manual` 永远返回 `success_count=0, sources=[]`,**v3.1 仓库无法进行真实数据采集**。

## 复现步骤 (Repro)

```bash
# 1. Clone & install
git clone https://github.com/raymodny-ai/Multi-source-Resonance-1.git
cd Multi-source-Resonance-1
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r requirements.txt

# 2. (空 .env 也行) 启动
PORT=8525 python -m backend.main
# → Application startup complete, Uvicorn on :8525

# 3. 健康检查 OK
curl -s http://localhost:8525/api/health
# {"status":"ok","version":"3.1.0","uptime_seconds":...}

# 4. 登录拿 token
curl -s -X POST http://localhost:8525/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"***"}'
# → {"access_token":"...","refresh_token":"..."}

# 5. 触发采集 (BUG)
curl -s -X POST http://localhost:8525/api/system/collect-manual \
  -H "Authorization: Bearer $TOKEN"
# → {"ok":true,"success_count":0,"error_count":0,"sources":[]}
# ❌ 应该返回 21 个 source 状态,实际 0
```

## 根因分析 (Root Cause)

### 文件结构

| 路径 | 角色 | 状态 |
|---|---|---|
| `backend/fetchers/base.py` | **新版** BaseFetcher, 签名 `(config, db=None)`, ABC 含 `source_name` (property) + `fetch` (async) + `_mock_data` | 完整,但只有 5 个 fetcher 真正使用 |
| `backend/fetchers/base_alt.py` | **旧版** BaseFetcher, 签名 `()`, ABC 只含 `fetch` | 文件头注释明示 "Temporary base fetcher class" — 待迁移 |
| `backend/fetchers/__init__.py` | 导出 `BaseFetcher` | **指向 `base_alt`**, 与迁移目标矛盾 (注释写 base, 代码 import base_alt) |
| 5 个 fetcher (gexmetrix/axlfi/cboe/vix/yfinance) | 走 `base.py` 完整版 | 完整迁移 |
| 16 个 fetcher (crypto/coinglass/sentiment/darkpool/flow/llm/macro/put_call/sector/squeezemetrics/finra/ccdata/stockgrid/tradier/dbmf/vix_term) | 走 `base_alt` 旧版 | **未迁移** |
| `backend/main.py` | `Pipeline(config, event_bus)` 调用 | **不传 `fetchers` 参数**, `Pipeline.__init__` 默认为 `[]` |

### 触发链

1. `main.py` 启 `Pipeline(config=settings, event_bus=event_bus)`,`fetchers=[]`
2. `POST /api/system/collect-manual` → `pipeline.run_cycle()` → `self.executor.execute_fetchers(self.fetchers)` (空 list)
3. `ExecutionReport` 收集 0 成功 0 失败 → 返回 `success_count=0`

即便修了 `main.py` 注入 21 个 fetcher 实例,16 个走 `base_alt` 的类会因 `__init__` 签名不匹配 (`settings` 没被消费) + 缺 `source_name`/`_mock_data` 抽象方法而**实例化即抛 TypeError**。

## 期望行为 (Expected)

`POST /api/system/collect-manual` 返回类似:

```json
{
  "ok": true,
  "success_count": 18,
  "error_count": 3,
  "sources": [
    {"name": "GEXMetrix", "ok": true,  "rows": 4, "elapsed_ms": 234},
    {"name": "yfinance",  "ok": true,  "rows": 6, "elapsed_ms": 512},
    ...
  ]
}
```

无 API key 的 source 应走 mock mode 返回合理合成数据。

## 提议修复 (Suggested Fix)

最低限度 (option A — 修 `__init__.py` + 标注,数据空):
```python
# backend/fetchers/__init__.py
from backend.fetchers.base import BaseFetcher  # ← 改成 base
# 同时在 16 个未迁移 fetcher 文件加:
#   @property
#   def source_name(self) -> str:
#       return "Crypto"  # 等
#   def _mock_data(self) -> dict:
#       return self._generate_mock_data()  # 转发到旧方法
#   def __init__(self, config, db=None):
#       self.config = config
#       self.db = db
#       self.logger = logging.getLogger(...)
```

完整迁移 (option B — 改名 + 删 base_alt):
- 把每个未迁移 fetcher 的 `_generate_mock_data` 改名为 `_mock_data`
- 加 `__init__(self, config, db=None)`,调 `super().__init__(config, db)`
- 加 `source_name` property
- `__init__.py` 走 `base`
- 删 `base_alt.py`

建议作者 **统一在 v3.1.1 一次完成 16 个 fetcher 迁移**,option A 不足以让 `collect-manual` 跑通。

## 其他发现 (Other Issues Found)

### Bug 2: `dashboard-view` Query range 过严

`backend/api/routes/gex.py` 的 `gex_dashboard_view`:
```python
strikes_limit: int = Query(200, ge=10, le=600)
```
README 9.5 节示例 `?strikes_limit=10` 跑通,?strikes_limit=5` 直接 422。`ge=10` 太严,建议 `ge=1, le=600`。

### Bug 3: FastAPI `docs` 未挂载

`/docs` + `/openapi.json` 都 404,Swagger UI 不可用。V3.1 主 app 应该 `app = FastAPI(docs_url="/docs", redoc_url="/redoc")` 或确认路由 `include_in_schema` 设置。

### Bug 4: `config.py` 文档不全

`Settings` 字段 `host` / `port` 文档没说支持 `PORT` env var,只有 `pydantic-settings` 默认行为能用。`.env` 写 `BACKEND_PORT=8525` 无效,必须 `PORT=8525`。

### Bug 5: `main.py` 缺 fetchers 注入

`Pipeline(config, event_bus)` 不传 `fetchers`,即使 base 修复后 pipeline 也空跑。建议 `main.py`:
```python
fetchers = [
    GEXMetrixFetcher(settings),
    YFinanceFetcher(settings),
    CryptoFetcher(settings),
    # ... 全部 21 个
]
pipeline = Pipeline(config=settings, event_bus=event_bus, fetchers=fetchers)
```

## 环境信息

- Python 3.12.13
- FastAPI 0.115+ (from requirements.txt)
- SQLite 3 (WAL mode)
- 21 个 fetcher 文件 (从 README 1.3 节 "21 个数据源")
- HEAD: `c2d375c` (v3.1 完整实现)
- 测试时间: 2026-07-29 04:17-04:36 CST (Asia/Shanghai)

## 标签建议

`bug` `priority:high` `blocker` `v3.1.0` `data-collection` `fetcher-migration`

---

> **注**: 本 issue 由社区部署者 (raymodny-ai) 提交,基于纯本地 venv + 空 `.env` 复现,无任何外部 API key 依赖。
