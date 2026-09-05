#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: govdb_cli.py
title: 政府機關底座 DB 存取與對齊 CLI 工具 (GOV-DB CLI)
description: 提供查詢 master_agencies.sqlite 機關主檔、發布者別名對齊、組織樹導航與部會子專案部署狀態的 CGS v2.0 標準 CLI/API 工具。
category: database
dependencies: sqlite3
cgs_version: 2.0
"""

import os
import sys
import json
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 顯式宣告 CGS 規格版號
__cli_spec_version__ = "2.0"

DB_PATH = Path(__file__).resolve().parents[1] / "ontology" / "master_agencies.sqlite"
_log_file_handle = None


# --- CGS v2.0 觀察性與日誌工具區塊 ---
def init_log_file(log_file_path: Optional[str] = None) -> None:
    """初始化 --log-file 目錄與檔案 File Handle"""
    global _log_file_handle
    if not log_file_path:
        return

    if log_file_path == "AUTO":
        log_dir = os.path.join(os.getcwd(), "tmp", "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = os.path.join(log_dir, f"govdb_cli_{timestamp}.log")
    else:
        log_dir = os.path.dirname(os.path.abspath(log_file_path))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    try:
        _log_file_handle = open(log_file_path, "a", encoding="utf-8")
        print(f"ℹ️ [INFO] Log 已自動同步記錄至: {log_file_path}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ [WARN] 無法開啟 Log 檔案 ({log_file_path}): {e}", file=sys.stderr)


def log_msg(level: str, message: str, verbose: bool = False, json_mode: bool = False) -> None:
    """CGS v2.0 統一結構化 Log 輸出函式 (100% 輸出至 sys.stderr)"""
    if level.upper() == "DEBUG" and not verbose:
        return

    if json_mode:
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "level": level.upper(),
            "script": "govdb_cli.py",
            "message": message
        }
        formatted_str = json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
    else:
        prefix_map = {
            "INFO": "ℹ️ [INFO] ",
            "WARN": "⚠️ [WARN] ",
            "ERROR": "❌ [ERROR] ",
            "DEBUG": "🔍 [DEBUG] "
        }
        prefix = prefix_map.get(level.upper(), "")
        formatted_str = f"{prefix}{message}"

    print(formatted_str, file=sys.stderr)
    if _log_file_handle:
        _log_file_handle.write(formatted_str + "\n")
        _log_file_handle.flush()


def get_schema() -> Dict[str, Any]:
    """回傳 AI 與主控 pa_cli.py 可讀之輸入/輸出 JSON Schema 與路由地圖"""
    return {
        "domain": "govdb",
        "cgs_spec": __cli_spec_version__,
        "title": "govdb_cli",
        "description": "政府機關底座 DB 存取與別名對齊 CLI 工具",
        "commands": {
            "search": {"description": "搜尋機關主檔 (關鍵字/OID/機關代號)", "aliases": ["find"], "params": ["query"]},
            "tree": {"description": "顯示指定機關組織樹 (含父與子機關)", "aliases": ["hierarchy"], "params": ["target"]},
            "alias": {"description": "查詢開放資料發布單位別名對齊與 OID 映射", "aliases": ["align"], "params": ["publisher"]},
            "domains": {"description": "檢視已實體化展開之部會子專案", "aliases": ["list-domains"]},
            "stat": {"description": "顯示 DB 資料筆數與健康度指標統計", "aliases": ["metrics"]},
            "status": {"description": "掃描並顯示所有資料庫之 Table/View 筆數統計", "aliases": ["tables", "views"]},
            "schema": {"description": "輸出 JSON Schema 與路由地圖"},
            "version": {"description": "顯示版本與 CGS 規範資訊"}
        },
        "flags": {
            "-j, --json": "單行緊湊 JSON 輸出 (Token-Saving)",
            "-q, --quiet": "極簡輸出 (僅印主要結果 ID/名稱)",
            "-v, --verbose": "詳細 Debug 日誌 (至 stderr)",
            "-n, --limit": "最多限制筆數",
            "--log-file": "指定 Log 日誌輸出路徑"
        }
    }


# --- 核心業務邏輯 API 區塊 (CGS v2.0 規定: 零 sys.exit(), 拋出 Exception) ---
def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """取得 sqlite3 資料庫連線"""
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

    cursor.execute("SELECT * FROM master_agencies WHERE agency_name = ? OR agency_oid = ?", (target, target))
    node = cursor.fetchone()
    if not node:
        conn.close()
        raise ValueError(f"找不到指定機關: {target}")

    result = dict(node)
    
    if node["parent_oid"]:
        cursor.execute("SELECT agency_oid, agency_name FROM master_agencies WHERE agency_oid = ?", (node["parent_oid"],))
        parent = cursor.fetchone()
        result["parent"] = dict(parent) if parent else None
    else:
        result["parent"] = None

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


def get_db_status(db_dir: Optional[Path] = None) -> Dict[str, Any]:
    """動態掃描所有資料庫 (master_agencies, universal_keys) 內之所有 TABLE 與 VIEW 筆數"""
    if db_dir is None:
        db_dir = DB_PATH.parent

    target_dbs = ["master_agencies.sqlite", "universal_keys.sqlite"]
    db_results = {}

    for db_name in target_dbs:
        db_file = db_dir / db_name
        if not db_file.exists():
            db_results[db_name] = {"status": "NOT_FOUND", "objects": []}
            continue

        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name")
        objects = []
        for obj_type, obj_name in cursor.fetchall():
            try:
                cursor.execute(f"SELECT COUNT(*) FROM \"{obj_name}\"")
                cnt = cursor.fetchone()[0]
            except Exception:
                cnt = -1
            objects.append({
                "type": obj_type.upper(),
                "name": obj_name,
                "count": cnt
            })
        conn.close()
        db_results[db_name] = {
            "status": "OK",
            "db_path": str(db_file),
            "objects": objects
        }

    return db_results


# --- CGS v2.0 CLI 進入點區塊 (只在此處呼叫 sys.exit) ---
def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-j", "--json", action="store_true", help="單行緊湊 JSON 輸出 (Token-Saving)")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="極簡輸出 (僅印主要結果 ID/名稱)")
    parent_parser.add_argument("-v", "--verbose", action="store_true", help="詳細 Debug 日誌 (至 stderr)")
    parent_parser.add_argument("--log-file", type=str, help="指定 Log 日誌輸出路徑")

    parser = argparse.ArgumentParser(
        description="政府機關底座 DB 存取與對齊 CLI 工具 (GOV-DB CLI v2.0)",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令 (search, tree, alias, domains, stat, schema, version)")

    # 1. search / find
    search_parser = subparsers.add_parser("search", aliases=["find"], parents=[parent_parser], help="搜尋機關主檔")
    search_parser.add_argument("query", help="搜尋關鍵字 (名稱/OID/機關代號)")
    search_parser.add_argument("-n", "--limit", type=int, default=20, help="最多顯示筆數")

    # 2. tree / hierarchy
    tree_parser = subparsers.add_parser("tree", aliases=["hierarchy"], parents=[parent_parser], help="顯示機關組織樹")
    tree_parser.add_argument("target", help="目標機關名稱或 OID")

    # 3. alias / align
    alias_parser = subparsers.add_parser("alias", aliases=["align"], parents=[parent_parser], help="查詢發布單位別名映射")
    alias_parser.add_argument("publisher", help="發布單位名稱關鍵字")

    # 4. domains / list-domains
    subparsers.add_parser("domains", aliases=["list-domains"], parents=[parent_parser], help="檢視已實體化展開之部會子專案")

    # 5. stat / metrics
    subparsers.add_parser("stat", aliases=["metrics"], parents=[parent_parser], help="顯示 DB 統計與指標")

    # 6. status / tables / views
    subparsers.add_parser("status", aliases=["tables", "views"], parents=[parent_parser], help="掃描並顯示所有資料庫之 Table/View 筆數統計")

    # 8. g10 / miner / report_miner
    subparsers.add_parser("g10", aliases=["miner", "report_miner"], parents=[parent_parser], help="G10 報告探勘與典藏庫狀態")

    # 9. schema
    subparsers.add_parser("schema", parents=[parent_parser], help="輸出 JSON Schema 與路由地圖")

    # 8. version
    subparsers.add_parser("version", parents=[parent_parser], help="顯示版本與 CGS 規範資訊")

    args = parser.parse_args()

    if args.log_file:
        init_log_file(args.log_file)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    cmd = args.command

    try:
        log_msg("DEBUG", f"發動子命令: {cmd}, 參數: {vars(args)}", verbose=args.verbose, json_mode=args.json)

        if cmd in ["version"]:
            ver_info = {
                "script": "govdb_cli.py",
                "version": "0.2.1",
                "cgs_spec": __cli_spec_version__,
                "db_path": str(DB_PATH)
            }
            if args.json:
                print(json.dumps(ver_info, ensure_ascii=False, separators=(',', ':')))
            else:
                print(f"🏛️ govdb_cli.py v0.2.1 (CGS Spec v{__cli_spec_version__})")

        elif cmd in ["schema"]:
            schema_data = get_schema()
            if args.json:
                print(json.dumps(schema_data, ensure_ascii=False, separators=(',', ':')))
            else:
                print(json.dumps(schema_data, ensure_ascii=False, indent=2))

        elif cmd in ["status", "tables", "views"]:
            status_data = get_db_status()
            if args.json:
                print(json.dumps(status_data, ensure_ascii=False, separators=(',', ':')))
            elif args.quiet:
                for db_name, res in status_data.items():
                    for obj in res.get("objects", []):
                        print(f"{db_name}:{obj['type']}:{obj['name']}:{obj['count']}")
            else:
                print("📊 tw-gov-db 全資料庫 Table & View 物件與筆數統計:")
                for db_name, res in status_data.items():
                    if res["status"] != "OK":
                        print(f"\n 📁 [{db_name}] ❌ 檔案不存在")
                        continue
                    print(f"\n 📁 [{db_name}] ({len(res['objects'])} 個物件):")
                    for obj in res["objects"]:
                        badge = "📋 [TABLE]" if obj["type"] == "TABLE" else "👁️ [VIEW]"
                        print(f"   └── {badge} {obj['name']}: {obj['count']:,} 筆")

        elif cmd in ["search", "find"]:
            data = search_agencies(args.query, limit=args.limit)
            if args.json:
                print(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
            elif args.quiet:
                for item in data:
                    print(item['agency_oid'])
            else:
                print(f"🔍 搜尋 '{args.query}' 結果 ({len(data)} 筆):")
                for item in data:
                    print(f" • [{item['org_code'] or '無代碼'}] {item['agency_name']} (OID: {item['agency_oid']})")

        elif cmd in ["g10", "miner", "report_miner"]:
            gov_src = str(Path(__file__).resolve().parents[1] / "src")
            if gov_src not in sys.path:
                sys.path.insert(0, gov_src)
            from modules.g10_report_miner.g10_core import get_db_summary
            summary = get_db_summary()
            if args.json:
                print(json.dumps(summary, ensure_ascii=False, separators=(',', ':')))
            else:
                print(f"📊 G10 gov-report-miner 狀態摘要: 報告索引 {summary['total_reports']} 筆, 已快取 {summary['cached_reports']} 筆, 暫存 {summary['staged_reports']} 筆")

        elif cmd in ["tree", "hierarchy"]:
            tree = get_agency_tree(args.target)
            if args.json:
                print(json.dumps(tree, ensure_ascii=False, separators=(',', ':')))
            elif args.quiet:
                print(f"{tree['agency_name']}:{tree['agency_oid']}")
            else:
                print(f"🌳 組織樹: {tree['agency_name']} (OID: {tree['agency_oid']})")
                if tree['parent']:
                    print(f" ⬆️ 上級機關: {tree['parent']['agency_name']} ({tree['parent']['agency_oid']})")
                print(f" ⬇️ 下屬機關 ({len(tree['children'])} 個):")
                for child in tree['children'][:15]:
                    print(f"   └── [{child['org_code'] or 'N/A'}] {child['agency_name']} ({child['agency_oid']})")
                if len(tree['children']) > 15:
                    print(f"   ... (其餘 {len(tree['children']) - 15} 個省略)")

        elif cmd in ["alias", "align"]:
            aliases = search_publisher_alias(args.publisher)
            if args.json:
                print(json.dumps(aliases, ensure_ascii=False, separators=(',', ':')))
            elif args.quiet:
                for a in aliases:
                    print(f"{a['raw_publisher_name']}:{a['mapped_agency_oid']}")
            else:
                print(f"🏷️ 發布單位別名對齊 '{args.publisher}' ({len(aliases)} 筆):")
                for a in aliases:
                    print(f" • '{a['raw_publisher_name']}' ➔ {a['agency_name']} (OID: {a['mapped_agency_oid']}) [信心分數: {a['confidence_score']}]")

        elif cmd in ["domains", "list-domains"]:
            domains = get_domain_deployments()
            if args.json:
                print(json.dumps(domains, ensure_ascii=False, separators=(',', ':')))
            elif args.quiet:
                for d in domains:
                    print(d['domain_id'])
            else:
                print(f"🌐 已實體化展開之部會專案 ({len(domains)} 個):")
                for d in domains:
                    print(f" • [{d['domain_id']}] {d['domain_name']} ➔ 根機關: {d['root_agency_name']} (OID: {d['root_agency_oid']}) [路徑: {d['repo_path']}]")

        elif cmd in ["stat", "metrics"]:
            stats = get_db_stats()
            if args.json:
                print(json.dumps(stats, ensure_ascii=False, separators=(',', ':')))
            elif args.quiet:
                print(json.dumps(stats, ensure_ascii=False, separators=(',', ':')))
            else:
                print("📊 master_agencies.sqlite 資料庫指標統計:")
                print(f" • 權威機關主檔 (master_agencies): {stats['master_agencies']} 筆")
                print(f" • 具備父階層綁定 (agencies_with_parent): {stats['agencies_with_parent']} 筆")
                print(f" • 開放資料發布單位別名 (publisher_aliases): {stats['publisher_aliases']} 筆")
                print(f" • 已實體展開部會專案 (domain_deployments): {stats.get('domain_deployments', 0)} 個")
                print(f" • 法規職掌條文 (agency_mandates): {stats['agency_mandates']} 筆")

        sys.exit(0)

    except Exception as e:
        log_msg("ERROR", f"執行失敗: {e}", verbose=True, json_mode=args.json)
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
