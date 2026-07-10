# -*- coding: utf-8 -*-
"""
===================================
全A股自选名单生成器
===================================

从 akshare 拉取全 A 股代码列表，过滤 ST/退市/北交所，
按市值或代码前缀均衡抽样 500 只，输出逗号分隔的名单。

使用方法：
    python scripts/generate_watchlist.py
    python scripts/generate_watchlist.py --max 500
    python scripts/generate_watchlist.py --max 300 --shuffle
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

import argparse
import logging
import random
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("generate_watchlist")

_BLACKLIST_NAME_RE = re.compile(r"退市|退|ST|\*ST|S\*?ST|PT", re.IGNORECASE)
_A_SHARE_CODE_RE = re.compile(r"^(00[023]\d{3}|30[01]\d{3}|60[013]\d{3}|688\d{3})$")
_BEIJING_RE = re.compile(r"^8\d{5}$")


def _is_valid_a_share(code: str, name: str) -> bool:
    if _BEIJING_RE.match(code):
        return False
    if _BLACKLIST_NAME_RE.search(name):
        return False
    return bool(_A_SHARE_CODE_RE.match(code))


def main():
    parser = argparse.ArgumentParser(
        description="全A股自选名单生成器"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=int(os.getenv("WATCHLIST_MAX_STOCKS", "500")),
        help="最多返回几只股票 (默认: 500)",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        default=os.getenv("WATCHLIST_SHUFFLE", "").lower() in ("1", "true", "yes"),
        help="随机打乱后抽样（否则按代码排序取前N）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子 (默认: 42)",
    )
    args = parser.parse_args()
    max_stocks = args.max

    logger.info("========================================")
    logger.info("全A股名单生成开始")
    logger.info("上限: %d 只", max_stocks)
    logger.info("抽样方式: %s", "随机打乱" if args.shuffle else "按代码排序")
    logger.info("========================================")

    import akshare as ak

    logger.info("[获取] 调用 ak.stock_info_a_code_name()...")
    try:
        df = ak.stock_info_a_code_name()
    except Exception as e:
        logger.error("[获取] 全A股名单获取失败: %s", e)
        sys.exit(1)

    if df is None or df.empty:
        logger.error("[获取] 返回空数据")
        sys.exit(1)

    logger.info("[获取] 共 %d 只股票", len(df))

    code_col = "code" if "code" in df.columns else df.columns[0]
    name_col = "name" if "name" in df.columns else df.columns[1]

    valid: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        code = str(row.get(code_col, "")).strip()
        name = str(row.get(name_col, "")).strip()
        if _is_valid_a_share(code, name):
            valid.append({"code": code, "name": name})

    logger.info("[过滤] 有效A股: %d 只 (已排除 ST/退市/北交所)", len(valid))

    if args.shuffle:
        rng = random.Random(args.seed)
        rng.shuffle(valid)

    selected = valid[:max_stocks]
    codes = [s["code"] for s in selected]
    code_list_str = ",".join(codes)

    logger.info("[抽样] 选中 %d 只", len(selected))

    for i, s in enumerate(selected[:10]):
        logger.info("  %d. %s %s", i + 1, s["code"], s["name"])
    if len(selected) > 10:
        logger.info("  ... 还有 %d 只", len(selected) - 10)

    logger.info("========================================")
    logger.info("生成完成: %d 只", len(selected))
    print(code_list_str)


if __name__ == "__main__":
    main()
