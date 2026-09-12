#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 全政府法人、企業與農漁會維度器 CLI (G60)
description: 提供 8 碼統一編號新舊制雙軌校驗、長文本統編萃取濾網、全台農漁會拓樸消歧義與 Pass-Through 快取查詢控制台。
category: cli
dependencies: sqlite3, select, sys, json
spec: scripts/specs/g60_cli.spec.md
manual: scripts/manuals/g60_cli.md
compat: posix_windows
"""

__cli_spec_version__ = "2.4"
__version__ = "1.0.0"

import os
import sys
import json
import select
import sqlite3
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# 導入同目錄核心演算法模組
MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from ban_validator import BanValidator
from npo_resolver import NpoResolver

DEFAULT_DB_PATH = MODULE_DIR.parents[2] / "data" / "universal_keys.sqlite"


def probe_stdin(timeout: float = 0.3) -> Optional[str]:
    """
    CGS v2.4 規範：非阻塞 Stdin 探針 (Non-blocking Stdin Probe)
    快速探測是否具有管線輸入，給予 0.3 秒緩衝以相容上游行程啟動，避免行程掛死 (Hang)
    """
    if sys.stdin.isatty():
        return None
    try:
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        if r:
            return sys.stdin.read()
    except Exception:
        try:
            return sys.stdin.read()
        except Exception:
            return None
    return None


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------------------
# 核心業務函式 (與 CLI 解耦)
# -------------------------------------------------------------

def execute_check(tax_ids: List[str], mode: str = "both") -> List[Dict[str, Any]]:
    """批次驗證統一編號"""
    results = []
    for tid in tax_ids:
        tid_clean = tid.strip()
        if not tid_clean:
            continue
        results.append(BanValidator.validate(tid_clean, mode=mode))
    return results


def execute_lookup(queries: List[str], db_path: Optional[str] = None, no_remote: bool = False) -> List[Dict[str, Any]]:
    """查詢法人主檔 (本機快取優先)"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    results = []

    for q in queries:
        q_clean = q.strip()
        if not q_clean:
            continue

        # 先以統編查詢
        cursor.execute("SELECT * FROM corporate_registry WHERE tax_id = ?", (q_clean,))
        row = cursor.fetchone()

        if not row:
            # 再以公司名稱模糊查詢
            cursor.execute("SELECT * FROM corporate_registry WHERE company_name LIKE ? LIMIT 1", (f"%{q_clean}%",))
            row = cursor.fetchone()

        if row:
            results.append({
                "tax_id": row["tax_id"],
                "company_name": row["company_name"],
                "registered_address": row["registered_address"],
                "admin_code": row["admin_code"],
                "status": row["status"],
                "source": row["source"],
                "cache_hit": True
            })
        else:
            # 檢驗是否為合法統編
            val_res = BanValidator.validate(q_clean)
            results.append({
                "tax_id": q_clean,
                "company_name": None,
                "registered_address": None,
                "admin_code": None,
                "status": "UNKNOWN",
                "source": "NOT_FOUND",
                "cache_hit": False,
                "is_valid_tax_id": val_res["is_valid"]
            })

    conn.close()
    return results


def execute_resolve(names: List[str], db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """農漁會與非營利法人消歧義"""
    resolver = NpoResolver(db_path=db_path)
    results = []
    for n in names:
        n_clean = n.strip()
        if not n_clean:
            continue
        results.append(resolver.resolve(n_clean))
    return results


def execute_pipe_extract(text: str) -> List[Dict[str, Any]]:
    """從文本串流自動萃取合法統編"""
    return BanValidator.extract_from_text(text)


def execute_status(db_path: Optional[str] = None) -> Dict[str, Any]:
    """模組狀態與資料庫統計"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    corp_count = 0
    npo_count = 0
    try:
        cursor.execute("SELECT count(*) FROM corporate_registry;")
        corp_count = cursor.fetchone()[0]
    except Exception:
        pass

    try:
        cursor.execute("SELECT count(*) FROM npo_registry;")
        npo_count = cursor.fetchone()[0]
    except Exception:
        pass

    conn.close()

    return {
        "module": "g60_corporate_indexer",
        "cgs_version": __cli_spec_version__,
        "version": __version__,
        "database_path": str(DEFAULT_DB_PATH if not db_path else db_path),
        "corporate_cache_count": corp_count,
        "npo_registry_count": npo_count,
        "algorithms": {
            "ban_validation": ["legacy_mod_10", "rule_7_special", "2023_mod_5_10"],
            "npo_disambiguation": ["suffix_strip", "alias_lookup", "exact_match", "fuzzy_containment"]
        },
        "status": "READY"
    }


# -------------------------------------------------------------
# CLI 介面解析器
# -------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    # 建立通用共用選項父解析器
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-j", "--json", action="store_true", help="以單行緊湊 JSON 格式輸出")
    common_parser.add_argument("-q", "--quiet", action="store_true", help="極簡輸出模式 (僅輸出關鍵結果或ID)")
    common_parser.add_argument("-v", "--verbose", action="store_true", help="輸出除錯日誌至 stderr")
    common_parser.add_argument("--db", type=str, default=None, help="自訂 universal_keys.sqlite 資料庫路徑")

    parser = argparse.ArgumentParser(
        prog="g60_cli.py",
        parents=[common_parser],
        description="G60 全政府法人、企業與農漁會維度器控制台 (CGS v2.4 Pipeline-Native)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--version", action="store_true", help="顯示版本與 CGS 規範資訊")
    parser.add_argument("--schema", action="store_true", help="輸出自我描述 JSON Schema")

    subparsers = parser.add_subparsers(dest="subcommand", help="子命令")

    # 1. check
    p_check = subparsers.add_parser("check", parents=[common_parser], help="檢核 8 碼統一編號是否合法 (支援 stdin 管線)")
    p_check.add_argument("tax_ids", nargs="*", help="統一編號 (無引數時自動從 stdin 讀取)")
    p_check.add_argument("--strict", action="store_true", help="僅採用舊制除 10 驗證")
    p_check.add_argument("--new-only", action="store_true", help="僅採用 2023 財政部除 5 新制驗證")

    # 2. lookup
    p_lookup = subparsers.add_parser("lookup", parents=[common_parser], help="查詢法人與企業主檔 (支援 stdin 管線)")
    p_lookup.add_argument("queries", nargs="*", help="統一編號或公司名稱 (支援 stdin)")
    p_lookup.add_argument("--tsv", action="store_true", help="以 TSV 格式輸出")
    p_lookup.add_argument("--no-remote", action="store_true", help="僅查本機快取，不連線遠端")

    # 3. resolve
    p_resolve = subparsers.add_parser("resolve", parents=[common_parser], help="農漁會與 NPO 名稱消歧義 (支援 stdin 管線)")
    p_resolve.add_argument("names", nargs="*", help="不規範名稱 (如板農、新埔農會)")

    # 4. pipe
    p_pipe = subparsers.add_parser("pipe", parents=[common_parser], help="UNIX 串流文字濾網 (自動自長文本萃取合法統編)")
    p_pipe.add_argument("--extract-tax-id", action="store_true", default=True, help="萃取文本中所有合法 8 碼統編")

    # 5. status
    subparsers.add_parser("status", parents=[common_parser], help="顯示 G60 模組與快取庫狀態看板")

    # 6. manual
    subparsers.add_parser("manual", parents=[common_parser], help="顯示或透過 man 分頁器瀏覽手冊")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 處理 --version
    if args.version:
        if args.json:
            print(json.dumps({"module": "g60_corporate_indexer", "version": __version__, "cgs_version": __cli_spec_version__}, ensure_ascii=False))
        else:
            print(f"g60_cli.py v{__version__} (CGS v{__cli_spec_version__})")
        sys.exit(0)

    # 處理 --schema
    if args.schema:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "G60CorporateIndexerSchema",
            "type": "object",
            "subcommands": ["check", "lookup", "resolve", "pipe", "status", "manual"],
            "features": ["ban_validator_legacy_and_2023", "npo_disambiguation", "pass_through_cache"]
        }
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        sys.exit(0)

    if not args.subcommand or args.subcommand == "manual":
        # 顯示說明
        manual_path = MODULE_DIR.parents[3] / "scripts" / "manuals" / "g60_cli.md"
        if manual_path.exists():
            with open(manual_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            parser.print_help()
        sys.exit(0)

    # 探測 stdin
    stdin_content = probe_stdin()

    # -------------------------------------------------------------
    # 執行各子命令
    # -------------------------------------------------------------
    if args.subcommand == "check":
        tax_ids = list(args.tax_ids)
        if not tax_ids and stdin_content:
            tax_ids = [line.strip() for line in stdin_content.splitlines() if line.strip()]

        if not tax_ids:
            sys.stderr.write("錯誤: 未提供統一編號引數或 stdin 串流\n")
            sys.exit(1)

        mode = "both"
        if args.strict:
            mode = "strict"
        elif args.new_only:
            mode = "current"

        res = execute_check(tax_ids, mode=mode)
        if args.quiet:
            for r in res:
                if r["is_valid"]:
                    print(r["tax_id"])
        elif args.json or len(res) > 1:
            print(json.dumps(res, ensure_ascii=False))
        else:
            item = res[0]
            status_str = "合法" if item["is_valid"] else "無效"
            print(f"統編: {item['tax_id']} -> [{status_str}] ({item['explanation']})")

    elif args.subcommand == "lookup":
        queries = list(args.queries)
        if not queries and stdin_content:
            queries = [line.strip() for line in stdin_content.splitlines() if line.strip()]

        if not queries:
            sys.stderr.write("錯誤: 未提供查詢字串或 stdin 串流\n")
            sys.exit(1)

        res = execute_lookup(queries, db_path=args.db, no_remote=args.no_remote)
        if args.tsv:
            for r in res:
                print(f"{r['tax_id']}\t{r['company_name'] or 'N/A'}\t{r['registered_address'] or 'N/A'}\t{r['admin_code'] or 'N/A'}")
        elif args.quiet:
            for r in res:
                print(f"{r['tax_id']} {r['company_name'] or ''}".strip())
        elif args.json or len(res) > 1:
            print(json.dumps(res, ensure_ascii=False))
        else:
            item = res[0]
            print(f"統編: {item['tax_id']} | 名稱: {item['company_name']} | 地址: {item['registered_address']}")

    elif args.subcommand == "resolve":
        names = list(args.names)
        if not names and stdin_content:
            names = [line.strip() for line in stdin_content.splitlines() if line.strip()]

        if not names:
            sys.stderr.write("錯誤: 未提供組織名稱或 stdin 串流\n")
            sys.exit(1)

        res = execute_resolve(names, db_path=args.db)
        if args.quiet:
            for r in res:
                print(r["canonical_name"] or r["input_name"])
        elif args.json or len(res) > 1:
            print(json.dumps(res, ensure_ascii=False))
        else:
            item = res[0]
            if item["is_resolved"]:
                print(f"輸入: {item['input_name']} -> 標準全名: {item['canonical_name']} (代碼: {item['npo_id']})")
            else:
                print(f"輸入: {item['input_name']} -> 無法精確消歧義")

    elif args.subcommand == "pipe":
        content = stdin_content if stdin_content else " ".join(sys.argv[2:])
        if not content:
            sys.stderr.write("錯誤: pipe 子命令需要標準輸入 (stdin)\n")
            sys.exit(1)

        extracted = execute_pipe_extract(content)
        if args.quiet:
            for r in extracted:
                print(r["tax_id"])
        else:
            print(json.dumps(extracted, ensure_ascii=False))

    elif args.subcommand == "status":
        st = execute_status(db_path=args.db)
        if args.json:
            print(json.dumps(st, ensure_ascii=False))
        else:
            print(f"=== {st['module']} (CGS v{st['cgs_version']}) 狀態看板 ===")
            print(f"模組版本: v{st['version']}")
            print(f"法人快取筆數 (corporate_registry): {st['corporate_cache_count']}")
            print(f"農漁會登記筆數 (npo_registry): {st['npo_registry_count']}")
            print(f"狀態: {st['status']}")


if __name__ == "__main__":
    main()
