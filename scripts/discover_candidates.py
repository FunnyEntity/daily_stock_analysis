# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - 候选池自动发现
===================================

从多个来源自动发现当日值得分析的股票，输出逗号分隔的代码列表。

来源：
- hot_stocks: 东方财富人气榜/飙升榜/雪球关注榜
- limit_up: 涨停池（按连板数排序）

使用方法：
    python scripts/discover_candidates.py
    python scripts/discover_candidates.py --max 100
    python scripts/discover_candidates.py --source hot_stocks,limit_up

环境变量：
    DISCOVER_SOURCE: 发现来源 (逗号分隔，默认: hot_stocks,limit_up)
    DISCOVER_MAX_STOCKS: 最多返回几只 (默认: 100)
    DISCOVER_MARKETS: 市场过滤 (默认: cn)
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# Proxy config - GitHub Actions skip
if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("discover_candidates")

A_SHARE_CODE_RE = re.compile(r"^(000|001|002|003|300|301|600|601|603|605|688)\d{3}$")


def _is_a_share(code: str) -> bool:
    return bool(A_SHARE_CODE_RE.match(code))


def _deduplicate_by_code(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    result: List[Dict[str, Any]] = []
    for s in stocks:
        code = s.get("code", "").strip()
        if code and code not in seen:
            seen.add(code)
            result.append(s)
    return result


def _filter_a_shares(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [s for s in stocks if _is_a_share(s.get("code", ""))]


def main():
    parser = argparse.ArgumentParser(
        description="A股候选池自动发现 - 输出逗号分隔股票代码列表"
    )
    parser.add_argument(
        "--source",
        default=os.getenv("DISCOVER_SOURCE", "hot_stocks,limit_up"),
        help="发现来源 (逗号分隔: hot_stocks,limit_up,all)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=int(os.getenv("DISCOVER_MAX_STOCKS", "100")),
        help="最多返回几只股票",
    )
    parser.add_argument(
        "--markets",
        default=os.getenv("DISCOVER_MARKETS", "cn"),
        help="市场过滤 (cn/hk/us, 默认 cn)",
    )
    parser.add_argument(
        "--output",
        choices=("list", "env", "both"),
        default="list",
        help='输出格式: list(代码列表), env(STOCK_LIST=xxx), both',
    )
    args = parser.parse_args()
    source = args.source.strip().lower()
    max_stocks = args.max
    markets = args.markets.strip().lower()

    if source == "all":
        sources = {"hot_stocks", "limit_up"}
    else:
        sources = {s.strip() for s in source.split(",") if s.strip()}

    logger.info("========================================")
    logger.info("候选池发现开始")
    logger.info("来源: %s", ",".join(sorted(sources)))
    logger.info("上限: %d 只", max_stocks)
    logger.info("市场: %s", markets)
    logger.info("========================================")

    all_candidates: List[Dict[str, Any]] = []

    from data_provider.base import DataFetcherManager

    manager = DataFetcherManager()
    per_source_limit = max(max_stocks, 50)

    if "hot_stocks" in sources:
        logger.info("[发现] 获取人气股榜 (最多 %d 只)...", per_source_limit)
        try:
            hot = manager.get_hot_stocks(n=per_source_limit)
            logger.info("[发现] 人气股获取 %d 只", len(hot))
            all_candidates.extend(hot)
        except Exception as e:
            logger.warning("[发现] 获取人气股失败: %s", e)

    if "limit_up" in sources:
        logger.info("[发现] 获取涨停池 (最多 %d 只)...", per_source_limit)
        try:
            limit_up = manager.get_limit_up_pool(n=per_source_limit)
            logger.info("[发现] 涨停池获取 %d 只", len(limit_up))
            all_candidates.extend(limit_up)
        except Exception as e:
            logger.warning("[发现] 获取涨停池失败: %s", e)

    logger.info("[发现] 合并前候选总数: %d", len(all_candidates))

    if "cn" in markets:
        all_candidates = _filter_a_shares(all_candidates)
        logger.info("[发现] 过滤A股后: %d", len(all_candidates))

    all_candidates = _deduplicate_by_code(all_candidates)
    logger.info("[发现] 去重后: %d", len(all_candidates))

    final = all_candidates[:max_stocks]
    codes = [s.get("code", "").strip() for s in final if s.get("code", "").strip()]
    code_list_str = ",".join(codes)

    logger.info("========================================")
    logger.info("发现完成: %d 只候选股票", len(codes))

    for i, s in enumerate(final[:10]):
        logger.info(
            "  %d. %s %s (来源: %s)",
            i + 1,
            s.get("code", ""),
            s.get("name", ""),
            s.get("source", "未知"),
        )
    if len(final) > 10:
        logger.info("  ... 还有 %d 只", len(final) - 10)

    if output_format in ("list", "both"):
        print(code_list_str)

    if output_format in ("env", "both"):
        print(f"STOCK_LIST={code_list_str}")

    logger.info("输出完成")


if __name__ == "__main__":
    main()
