#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 政府機關底座 DB 存取 CLI 工具 (Master Agencies CLI)
description: 提供查詢 master_agencies.sqlite 機關主檔、別名對齊與組織樹導航的標準 CLI/API 工具。
category: database
dependencies: sqlite3
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

DB_PATH = Path(__file__).resolve().parents[1] / "ontology" / "master_agencies.sqlite"

def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"底座 DB 檔案不存在: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def search_agencies(query: str, limit: int = 20, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """依據關鍵字 (名稱/OID/OrgCode) 搜尋機關主檔"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    pattern = f"%{query.strip()}%"
    cursor.execute("""
        SELECT agency_oid, org_code, agency_name, parent_oid, level_type, updated_at
        FROM master_agencies
        WHERE agency_name LIKE ? OR agency_oid LIKE ? OR org_code LIKE ?
        LIMIT ?
    """, (pattern, pattern, pattern, limit))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_agency_tree(target: str, max_depth: int = 3, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """獲取指定機關的樹狀階層資訊 (含父機關與子機關)"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 查尋目標機關
    cursor.execute("SELECT * FROM master_agencies WHERE agency_name = ? OR agency_oid = ?", (target, target))
    node = cursor.fetchone()
    if not node:
        conn.close()
        raise ValueError(f"找不到指定機關: {target}")

    result = dict(node)
    
    # 查父機關
    if node["parent_oid"]:
        cursor.execute("SELECT agency_oid, agency_name FROM master_agencies WHERE agency_oid = ?", (node["parent_oid"],))
        parent = cursor.fetchone()
        result["parent"] = dict(parent) if parent else None
    else:
        result["parent"] = None

    # 查子機關
    cursor.execute("SELECT agency_oid, org_code, agency_name FROM master_agencies WHERE parent_oid = ?", (node["agency_oid"],))
    children = [dict(r) for r in cursor.fetchall()]
    result["children"] = children
    conn.close()
    return result

def search_publisher_alias(publisher_name: str, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """從開放資料發布單位別名表中查詢映射之 OID 與權威機關名稱"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    pattern = f"%{publisher_name.strip()}%"
    cursor.execute("""
        SELECT a.alias_id, a.raw_publisher_name, a.mapped_agency_oid, a.confidence_score, m.agency_name
        FROM publisher_aliases a
        JOIN master_agencies m ON a.mapped_agency_oid = m.agency_oid
        WHERE a.raw_publisher_name LIKE ?
    """, (pattern,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_domain_deployments(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """獲取已註冊並實體展開之部會專案 (如 tw-agro-db) 清單"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.domain_id, d.domain_name, d.root_agency_oid, m.agency_name as root_agency_name, d.repo_path, d.deployment_status
        FROM domain_deployments d
        LEFT JOIN master_agencies m ON d.root_agency_oid = m.agency_oid
    """)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_db_stats(db_path: Path = DB_PATH) -> Dict[str, int]:
    """獲取底座 DB 各表格筆數與對齊統計"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    stats = {}
    for table in ["master_agencies", "agency_mandates", "publisher_aliases", "domain_deployments"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats[table] = 0

    cursor.execute("SELECT COUNT(*) FROM master_agencies WHERE parent_oid IS NOT NULL")
    stats["agencies_with_parent"] = cursor.fetchone()[0]
    conn.close()
    return stats

# --- CLI 介面處理區塊 ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="tw-gov-db 底座資料庫 CLI 工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令 (search, tree, alias, stat)")

    # 1. search 命令
    search_parser = subparsers.add_parser("search", help="搜尋機關主檔")
    search_parser.add_argument("query", help="搜尋關鍵字 (名稱/OID/機關代號)")
    search_parser.add_argument("-n", "--limit", type=int, default=20, help="最多顯示筆數")
    search_parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")

    # 2. tree 命令
    tree_parser = subparsers.add_parser("tree", help="顯示機關組織樹")
    tree_parser.add_argument("target", help="目標機關名稱或 OID")
    tree_parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")

    # 3. alias 命令
    alias_parser = subparsers.add_parser("alias", help="查詢發布單位別名映射")
    alias_parser.add_argument("publisher", help="發布單位名稱關鍵字")
    alias_parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")

    # 4. stat 命令
    stat_parser = subparsers.add_parser("stat", help="顯示 DB 統計與指標")
    stat_parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")

    # 5. domains 命令
    domains_parser = subparsers.add_parser("domains", help="檢視已展開實體化之部會子專案")
    domains_parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "search":
            data = search_agencies(args.query, limit=args.limit)
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(f"\033[94m🔍 搜尋 '{args.query}' 結果 ({len(data)} 筆):\033[0m")
                for item in data:
                    print(f" • [{item['org_code'] or '無程式碼'}] {item['agency_name']} (OID: {item['agency_oid']})")

        elif args.command == "tree":
            tree = get_agency_tree(args.target)
            if args.json:
                print(json.dumps(tree, ensure_ascii=False, indent=2))
            else:
                print(f"\033[92m🌳 組織樹: {tree['agency_name']} (OID: {tree['agency_oid']})\033[0m")
                if tree['parent']:
                    print(f" ⬆️ 上級機關: {tree['parent']['agency_name']} ({tree['parent']['agency_oid']})")
                print(f" ⬇️ 下屬機關 ({len(tree['children'])} 個):")
                for child in tree['children'][:15]:
                    print(f"   └── [{child['org_code'] or 'N/A'}] {child['agency_name']} ({child['agency_oid']})")
                if len(tree['children']) > 15:
                    print(f"   ... (其餘 {len(tree['children']) - 15} 個省略)")

        elif args.command == "alias":
            aliases = search_publisher_alias(args.publisher)
            if args.json:
                print(json.dumps(aliases, ensure_ascii=False, indent=2))
            else:
                print(f"\033[93m🏷️ 發布單位別名對齊 '{args.publisher}' ({len(aliases)} 筆):\033[0m")
                for a in aliases:
                    print(f" • '{a['raw_publisher_name']}' ➔ {a['agency_name']} (OID: {a['mapped_agency_oid']}) [信心分數: {a['confidence_score']}]")

        elif args.command == "domains":
            domains = get_domain_deployments()
            if args.json:
                print(json.dumps(domains, ensure_ascii=False, indent=2))
            else:
                print(f"\033[96m🌐 已實體化展開之部會專案 ({len(domains)} 個):\033[0m")
                for d in domains:
                    print(f" • [{d['domain_id']}] {d['domain_name']} ➔ 根機關: {d['root_agency_name']} (OID: {d['root_agency_oid']}) [路徑: {d['repo_path']}]")

        elif args.command == "stat":
            stats = get_db_stats()
            if args.json:
                print(json.dumps(stats, ensure_ascii=False, indent=2))
            else:
                print("\033[95m📊 master_agencies.sqlite 資料庫指標統計:\033[0m")
                print(f" • 權威機關主檔 (master_agencies): {stats['master_agencies']} 筆")
                print(f" • 具備父階層綁定 (agencies_with_parent): {stats['agencies_with_parent']} 筆")
                print(f" • 開放資料發布單位別名 (publisher_aliases): {stats['publisher_aliases']} 筆")
                print(f" • 已實體展開部會專案 (domain_deployments): {stats.get('domain_deployments', 0)} 個")
                print(f" • 法規職掌條文 (agency_mandates): {stats['agency_mandates']} 筆")

    except Exception as e:
        print(f"\033[91m[錯誤] 執行失敗: {e}\033[0m", file=sys.stderr)
        sys.exit(1)
