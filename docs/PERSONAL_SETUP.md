# 个人分支配置记录

本文档记录本 fork 相对于上游的所有自定义修改，确保上游更新后可以快速恢复配置。

## 仓库改动一览

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/discover_candidates.py` | **新建** | 候选池自动发现脚本（人气榜+涨停池+退市过滤） |
| `.github/workflows/01-discover-analyze.yml` | **新建** | 串联发现+分析+大盘复盘工作流 |
| `.github/workflows/00-daily-analysis.yml` | **修改** | 在 checkout 后插入上游代码同步 step；定时改为仅周五 |
| `scripts/generate_watchlist.py` | **新建** | 全A股自选名单生成器（拉取~5000只→过滤→抽样500只） |
| `docs/PERSONAL_SETUP.md` | **新建** | 本文件 |

> 以上文件除 `00-daily-analysis.yml` 外均为上游不存在的文件，上游更新后不会被覆盖。`00-daily-analysis.yml` 若上游也改了相同位置，合并策略 `-X theirs` 会取上游版本，需手动补回。

---

## 工作流说明

### `01-discover-analyze`（发现候选股并分析）— 每日热点追踪

周一至周五 18:30 自动触发（cron: `30 10 * * 1-5`），也可以手动触发。

流程：
```
同步上游代码 → 安装依赖 → 发现候选池（人气榜+涨停池:~90只）→ 分析 → 大盘复盘 → 上传报告
```

### `00-daily-analysis`（每日股票分析）— 周度全市场扫描

仅周五 18:00 自动触发（cron: `0 10 * * 5`），用固定 `STOCK_LIST`（500只自选）做全市场周度扫描。也可以手动触发。

流程：
```
同步上游代码 → 安装依赖 → TickFlow批量K线+实时行情 → 500只分析 → 大盘复盘 → 上传报告
```

### 周度运行全景

```
周一 18:30  →  01 发现 ~90 只 + 分析     ~13 min
周二 18:30  →  01 发现 ~90 只 + 分析     ~13 min
周三 18:30  →  01 发现 ~90 只 + 分析     ~13 min
周四 18:30  →  01 发现 ~90 只 + 分析     ~13 min
周五 18:00  →  00 500 只全市场扫描       ~20 min
周五 18:30  →  01 发现 ~90 只 + 分析     ~13 min
周六 周日   →  不触发                     —
```

| 汇总 | 次数 | 股票量 | 月费用 |
|------|:--:|------|------|
| 01 工作流 | 5×/周，~22×/月 | ~90 只/次 | ~$2.90 |
| 00 工作流 | 1×/周，~4×/月 | 500 只/次 | ~$3.52 |
| **合计** | | | **~$6.42** (≈¥46) |

### 生成自选名单

```bash
python scripts/generate_watchlist.py --shuffle --max 500
```

将输出粘贴到 GitHub Variables `STOCK_LIST` 中。建议每月刷新一次。

---

## GitHub Actions Variables 清单

在仓库 Settings → Secrets and variables → Actions → Variables 中配置：

| 变量名 | 当前值 | 必填 | 说明 |
|--------|-----|:---:|------|
| `UPSTREAM_REPO` | `https://github.com/ZhuLinsen/daily_stock_analysis` | ✅ | 上游仓库地址，用于每日同步 |
| `LLM_CHANNELS` | `deepseek` | ✅ | LLM 渠道声明 |
| `LLM_DEEPSEEK_MODELS` | `deepseek-v4-flash` | ✅ | 使用的模型（flash 速度优先） |
| `LLM_DEEPSEEK_ENABLED` | `true` | ✅ | 启用 DeepSeek |
| `LITELLM_MODEL` | `deepseek/deepseek-v4-flash` | ✅ | LiteLLM 路由模型全路径 |
| `MAX_WORKERS` | `25` | ❌ | 并发数（flash 支持 2500 并发） |
| `GENERATION_BACKEND_TIMEOUT_SECONDS` | `300` | ❌ | LLM 调用超时（防卡死） |
| `ANALYSIS_TIMEOUT_MINUTES` | `180` | ❌ | 整个工作流硬超时 |
| `REPORT_TYPE` | `brief` | ❌ | 报告类型（brief/simple/full） |
| `ANALYSIS_DELAY` | `1` | ❌ | 股间延迟秒数 |
| `SEARXNG_PUBLIC_INSTANCES_ENABLED` | `false` | ❌ | 关闭公共 SearXNG 实例（GH IP 全被封） |
| `EFINANCE_PRIORITY` | `99` | ❌ | efinance 降到最低优先级（东方财富封 GH IP） |
| `REALTIME_SOURCE_PRIORITY` | `tickflow,tencent` | ❌ | TickFlow 批量预取优先，腾讯兜底 |
| `DISCOVER_SOURCE` | `hot_stocks,limit_up` | ❌ | 候选池来源（01 工作流用） |
| `DISCOVER_MAX_STOCKS` | `50` | ❌ | 候选池上限（设大了没意义，市场就 ~90） |
| `STOCK_LIST` | 500 只逗号分隔列表 | ❌ | 固定自选（00 工作流用，`generate_watchlist.py` 生成） |
| `MARKET_REVIEW_ENABLED` | `true`（默认） | ❌ | 设为 `false` 关闭大盘复盘 |

---

## GitHub Actions Secrets 清单

| 密钥名 | 必填 | 说明 |
|--------|:---:|------|
| `LLM_DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key |
| `LLM_DEEPSEEK_API_KEYS` | ❌ | 多 Key 负载均衡（逗号分隔） |
| `TICKFLOW_API_KEY` | ✅ | TickFlow API Key（免费，批量K线/实时行情） |
| `BOCHA_API_KEYS` | ❌ | 博查搜索（不推荐，费用高） |

---

## 调优历程

| 问题 | 根因 | 解决 |
|------|------|------|
| 搜索全部失败 | SearXNG 公共实例全限流/封 GitHub IP | `SEARXNG_PUBLIC_INSTANCES_ENABLED=false` |
| 数据源 efinance 拖慢 K 线 | 东方财富封 GitHub Actions IP | `EFINANCE_PRIORITY=99`（降到最低优先级） |
| 每只股票实时行情串行 5s | 腾讯接口无批量模式，per-fetcher 锁串行 | 注册 TickFlow + `REALTIME_SOURCE_PRIORITY=tickflow,tencent` |
| 退市股票混入候选池 | 涨停池返回国华退(000004)，正则只含"退市"不含"退" | 正则改为 `退` 覆盖两种后缀 |
| `DISCOVER_MAX_STOCKS` 不生效 | env 变量写在了分析 step 里，发现 step 跑在前读不到 | 改为 GitHub Actions 表达式 `${{ vars.DISCOVER_MAX_STOCKS }}` |
| 日志显示 UTC 时间 | GH runner 系统时区默认 UTC | `TZ: Asia/Shanghai` env 变量 |
| 运行时卡死无输出 | LLM 调用无超时，网络波动导致永久等待 | `GENERATION_BACKEND_TIMEOUT_SECONDS=300` |
| 来源标签显示"未知" | 涨停池/人气榜返回无 source 字段 | 脚本中补 `setdefault("source", ...)` |
| 大盘复盘缺失 | 01 工作流硬编码 `--no-market-review` | 改为根据 `MARKET_REVIEW_ENABLED` 变量控制 |

---

## 月度费用

| 项目 | 数值 |
|------|------|
| 模型 | `deepseek-v4-flash` |
| 单只股票成本 | ~$0.00175 |
| 01 工作流（22 天 × 90 只） | ~$3.47 |
| 00 工作流（4 周 × 500 只） | ~$3.50 |
| **月总计** | **~$7.00（≈¥50）** |
| 输入 1M tokens | $0.14（缓存命中 $0.0028） |
| 输出 1M tokens | $0.28 |
| 无搜索服务费用 | $0（已关闭 SearXNG + 未配博查） |

---

## 恢复步骤（上游更新覆盖后）

1. 重新添加 `scripts/discover_candidates.py`
2. 重新添加 `.github/workflows/01-discover-analyze.yml`
3. 检查 `00-daily-analysis.yml` 的上游同步 step 是否还在，如被覆盖则补回
4. GitHub Variables/Secrets 不受代码更新影响，无需重设
