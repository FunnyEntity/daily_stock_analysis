# 个人分支配置记录

本文档记录本 fork 相对于上游的所有自定义修改，确保上游更新后可以快速恢复配置。

## 仓库改动一览

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/discover_candidates.py` | **新建** | 候选池自动发现脚本（人气榜+涨停池+退市过滤） |
| `.github/workflows/01-discover-analyze.yml` | **新建** | 串联发现+分析+大盘复盘工作流 |
| `.github/workflows/00-daily-analysis.yml` | **修改** | 在 checkout 后插入上游代码同步 step |
| `docs/PERSONAL_SETUP.md` | **新建** | 本文件 |

> 以上文件除 `00-daily-analysis.yml` 外均为上游不存在的文件，上游更新后不会被覆盖。`00-daily-analysis.yml` 若上游也改了相同位置，合并策略 `-X theirs` 会取上游版本，需手动补回。

---

## 工作流说明

### `01-discover-analyze`（发现候选股并分析）— **主要使用**

每天 18:30 自动触发，也可以通过 Actions 页面手动触发。

流程：
```
同步上游代码 → 安装依赖 → 发现候选池（人气榜+涨停池）→ 分析 → 大盘复盘 → 上传报告
```

### `00-daily-analysis`（每日股票分析）— 备用

每天 18:00 自动触发，用固定 `STOCK_LIST` 跑分析。

---

## GitHub Actions Variables 清单

在仓库 Settings → Secrets and variables → Actions → Variables 中配置：

| 变量名 | 值 | 必填 | 说明 |
|--------|-----|:---:|------|
| `UPSTREAM_REPO` | `https://github.com/ZhuLinsen/daily_stock_analysis` | ✅ | 上游仓库地址，用于每日同步 |
| `LLM_CHANNELS` | `deepseek` | ✅ | LLM 渠道声明 |
| `LLM_DEEPSEEK_MODELS` | `deepseek-v4-flash` | ✅ | 使用的模型（flash 速度优先） |
| `LLM_DEEPSEEK_ENABLED` | `true` | ✅ | 启用 DeepSeek |
| `LITELLM_MODEL` | `deepseek/deepseek-v4-flash` | ✅ | LiteLLM 路由模型全路径 |
| `MAX_WORKERS` | `25` | ❌ | 并发数（flash 支持 2500 并发，按需调整） |
| `GENERATION_BACKEND_TIMEOUT_SECONDS` | `300` | ❌ | LLM 调用超时（防卡死） |
| `ANALYSIS_TIMEOUT_MINUTES` | `180` | ❌ | 整个工作流硬超时 |
| `REPORT_TYPE` | `brief` | ❌ | 报告类型（brief/simple/full） |
| `ANALYSIS_DELAY` | `1` | ❌ | 股间延迟秒数 |
| `SEARXNG_PUBLIC_INSTANCES_ENABLED` | `false` | ❌ | 关闭公共 SearXNG 实例（GitHub IP 全被封，纯浪费时间） |
| `EFINANCE_PRIORITY` | `99` | ❌ | 把 efinance 数据源降到最低优先级（东方财富封 GH IP） |
| `REALTIME_SOURCE_PRIORITY` | `tencent,akshare_sina,akshare_em,efinance` | ❌ | 实时行情源优先级（腾讯优先） |
| `DISCOVER_SOURCE` | `hot_stocks,limit_up` | ❌ | 候选池来源 |
| `DISCOVER_MAX_STOCKS` | `100` | ❌ | 候选池上限 |
| `STOCK_LIST` | `600519,...` | ❌ | 固定自选股（可选，01 工作流不需要） |

---

## GitHub Actions Secrets 清单

| 密钥名 | 必填 | 说明 |
|--------|:---:|------|
| `DEEPSEEK_API_KEY` 或 `LLM_DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key |
| `LLM_DEEPSEEK_API_KEYS` | ❌ | 多 Key 负载均衡（逗号分隔，优先级高于单 Key） |
| `BOCHA_API_KEYS` | ❌ | 博查搜索 API Key（免费，国内新闻搜索稳定） |

---

## 调优历程

| 问题 | 根因 | 解决 |
|------|------|------|
| 搜索全部失败 | SearXNG 公共实例全限流/封 GitHub IP | `SEARXNG_PUBLIC_INSTANCES_ENABLED=false` |
| 数据源 efinance 拖慢 8-12s/只 | 东方财富封 GitHub Actions IP | `EFINANCE_PRIORITY=99`（降到最低优先级，腾讯优先） |
| 退市股票混入候选池 | 涨停池返回国华退(000004) | `discover_candidates.py` 加退市/ST 名称过滤 |
| 运行时卡死无输出 | LLM 调用无超时，网络波动导致永久等待 | `GENERATION_BACKEND_TIMEOUT_SECONDS=300` |
| 来源标签显示"未知" | 涨停池返回无 source 字段 | 脚本中补 `source: "涨停池"` |
| 大盘复盘缺失 | 01 工作流硬编码 `--no-market-review` | 改为根据 `MARKET_REVIEW_ENABLED` 变量控制 |

---

## DeepSeek 费用

| 项目 | 数值 |
|------|------|
| 模型 | `deepseek-v4-flash` |
| 单只股票成本 | ~$0.00175 |
| 每天 75 只 | $0.13 |
| 每月 22 交易日 | $2.90 |
| 最大并发 | 2500 |
| 输入 1M tokens | $0.14（缓存命中 $0.0028） |
| 输出 1M tokens | $0.28 |

---

## 恢复步骤（上游更新覆盖后）

1. 重新添加 `scripts/discover_candidates.py`
2. 重新添加 `.github/workflows/01-discover-analyze.yml`
3. 检查 `00-daily-analysis.yml` 的上游同步 step 是否还在，如被覆盖则补回
4. GitHub Variables/Secrets 不受代码更新影响，无需重设
