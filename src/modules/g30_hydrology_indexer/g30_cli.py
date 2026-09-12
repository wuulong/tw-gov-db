#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 全政府水系流域與水情測站維度器 CLI (G50)
description: 提供全台 1,397+ 筆 WRA-Civ 水文拓樸微秒級追溯、上下游親緣展開、水情測站關聯、版本同步與 CGS v2.4 串流管道控制台。
category: cli
dependencies: sqlite3, select, sys, json
spec: scripts/specs/g30_cli.spec.md
manual: scripts/manuals/g30_cli.md
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

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from river_topology import RiverTopologyEngine

DEFAULT_DB_PATH = MODULE_DIR.parents[2] / "data" / "universal_keys.sqlite"


def probe_stdin(timeout: float = 0.3) -> Optional[str]:
    """CGS v2.4 規範：非阻塞 Stdin 探針 (0.3 秒緩衝以相容多進程管道)"""
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


def build_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-j", "--json", action="store_true", help="以單行緊湊 JSON 格式輸出")
    common_parser.add_argument("-q", "--quiet", action="store_true", help="極簡輸出模式 (僅輸出代碼或名稱)")
    common_parser.add_argument("-v", "--verbose", action="store_true", help="輸出除錯日誌至 stderr")
    common_parser.add_argument("--db", type=str, default=None, help="自訂 universal_keys.sqlite 資料庫路徑")
    common_parser.add_argument("--no-wra", action="store_true", help="強制停用外部 WRA-Civ 探測，僅使用本機基石模式")

    parser = argparse.ArgumentParser(
        prog="g30_cli.py",
        parents=[common_parser],
        description="G50 全政府水系流域與水情測站維度器控制台 (CGS v2.4 Pipeline-Native)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--version", action="store_true", help="顯示版本與 CGS 規範資訊")
    parser.add_argument("--schema", action="store_true", help="輸出自我描述 JSON Schema")

    subparsers = parser.add_subparsers(dest="subcommand", help="子命令")

    # 1. search
    p_search = subparsers.add_parser("search", parents=[common_parser], help="多維度檢索水脈 (支援關鍵字、流域、縣市)")
    p_search.add_argument("keyword", nargs="?", default=None, help="河流名稱或代碼關鍵字")
    p_search.add_argument("-b", "--basin", type=str, default=None, help="限定大流域幹流名稱")
    p_search.add_argument("-c", "--county", type=str, default=None, help="限定縣市名稱")
    p_search.add_argument("--official-only", action="store_true", help="僅限水利署官方公告 122 幹流")
    p_search.add_argument("-l", "--limit", type=int, default=20, help="返回筆數上限 (預設 20)")

    # 2. trace
    p_trace = subparsers.add_parser("trace", parents=[common_parser], help="上下游拓樸親緣追溯 (支援 stdin 管線)")
    p_trace.add_argument("river", nargs="?", default=None, help="河流代碼或名稱 (支援 stdin)")
    p_trace.add_argument("-i", "--input", type=str, default=None, help="輸入來源 ('-' 表示 stdin)")
    p_trace.add_argument("--upstream", action="store_true", help="向上游發源地展開支流子樹")
    p_trace.add_argument("--downstream", action="store_true", default=True, help="向下游追溯至大主流出海口")

    # 3. stations
    p_stations = subparsers.add_parser("stations", parents=[common_parser], help="查詢指定水脈沿線關聯之水情/雨量測站")
    p_stations.add_argument("river", nargs="?", default=None, help="河流代碼或名稱 (支援 stdin)")
    p_stations.add_argument("-i", "--input", type=str, default=None, help="輸入來源 ('-' 表示 stdin)")

    # 4. hydrate
    p_hydrate = subparsers.add_parser("hydrate", parents=[common_parser], help="WRA-Civ 串流基石注水器 (透過 stdin 注入 plugins.gov_db)")
    p_hydrate.add_argument("-i", "--input", type=str, default="-", help="輸入來源 (預設 '-')")

    # 5. sync-rivers
    p_sync = subparsers.add_parser("sync-rivers", parents=[common_parser], help="同步 WRA-Civ 上游水脈數據至本地庫")
    p_sync.add_argument("--check", action="store_true", help="僅檢查是否有新版本，不執行寫入")
    p_sync.add_argument("--force", action="store_true", help="強制重新同步覆蓋")
    p_sync.add_argument("--source", type=str, default=None, help="指定外部 JSONL 資料源路徑")

    # 6. status
    subparsers.add_parser("status", parents=[common_parser], help="顯示 G50 模組、水脈庫與測站狀態看板")

    # 7. manual
    subparsers.add_parser("manual", parents=[common_parser], help="顯示或透過 man 分頁器瀏覽手冊")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        if args.json:
            print(json.dumps({"module": "g30_hydrology_indexer", "version": __version__, "cgs_version": __cli_spec_version__}, ensure_ascii=False))
        else:
            print(f"g30_cli.py v{__version__} (CGS v{__cli_spec_version__})")
        sys.exit(0)

    if args.schema:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "G50HydrologyIndexerSchema",
            "type": "object",
            "subcommands": ["search", "trace", "stations", "hydrate", "sync-rivers", "status", "manual"],
            "features": ["wra_civ_topology_tree", "upstream_downstream_trace", "station_anchoring", "plugin_hydration"]
        }
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        sys.exit(0)

    if not args.subcommand or args.subcommand == "manual":
        manual_path = MODULE_DIR.parents[3] / "scripts" / "manuals" / "g30_cli.md"
        if manual_path.exists():
            with open(manual_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            parser.print_help()
        sys.exit(0)

    stdin_content = probe_stdin()
    db_target = Path(args.db) if args.db else DEFAULT_DB_PATH
    engine = RiverTopologyEngine(db_path=db_target)

    # -------------------------------------------------------------
    # 執行各子命令
    # -------------------------------------------------------------
    if args.subcommand == "search":
        kw = args.keyword
        if not kw and stdin_content:
            kw = stdin_content.strip()

        results = engine.search_rivers(
            keyword=kw,
            basin=args.basin,
            county=args.county,
            official_only=args.official_only,
            limit=args.limit
        )

        if args.quiet:
            for r in results:
                print(f"{r['river_code']} {r['river_name']}")
        elif args.json or len(results) > 1 or kw is None:
            print(json.dumps(results, ensure_ascii=False))
        elif len(results) == 1:
            item = results[0]
            print(f"水脈: {item['river_name']} (代碼: {item['river_code']}) | 流域: {item['basin_name']} | 縣市: {item['primary_county']} (階層: {item['stream_order']})")
        else:
            print("查無相符水脈資料。")

    elif args.subcommand == "trace":
        river_target = args.river
        if not river_target and (args.input == "-" or stdin_content):
            river_target = stdin_content.strip() if stdin_content else None

        if not river_target:
            sys.stderr.write("錯誤: 未提供河流代碼或名稱\n")
            sys.exit(1)

        # 向上游展開子樹 vs 向下游追溯祖先
        if args.upstream:
            res = engine.get_descendants(river_target)
        else:
            res = engine.get_ancestors(river_target)

        if args.quiet:
            for r in res:
                print(r["river_code"])
        elif args.json:
            print(json.dumps(res, ensure_ascii=False))
        else:
            chain_str = " -> ".join([f"{r['river_name']}({r['river_code']})" for r in res])
            mode_str = "發源支流子樹 (Upstream)" if args.upstream else "主流出海口鏈 (Downstream)"
            print(f"[{mode_str}] {chain_str}")

    elif args.subcommand == "stations":
        river_target = args.river
        if not river_target and (args.input == "-" or stdin_content):
            river_target = stdin_content.strip() if stdin_content else None

        if not river_target:
            sys.stderr.write("錯誤: 未提供河流代碼或名稱\n")
            sys.exit(1)

        stations = engine.get_stations_for_river(river_target)
        if args.quiet:
            for s in stations:
                print(s["station_id"])
        elif args.json or len(stations) > 1:
            print(json.dumps(stations, ensure_ascii=False))
        elif len(stations) == 1:
            s = stations[0]
            print(f"測站: {s['station_name']} ({s['station_id']}) | 類型: {s['station_type']} | 機關: {s['agency_name']}")
        else:
            print("該水脈沿線暫無直接關聯之測站。")

    elif args.subcommand == "hydrate":
        content = stdin_content
        if not content and args.input and args.input != "-":
            p = Path(args.input)
            if p.exists():
                content = p.read_text(encoding="utf-8")

        if not content:
            sys.stderr.write("錯誤: hydrate 子命令需要標準輸入 (stdin) JSONL 串流\n")
            sys.exit(1)

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                r_code = record.get("river_code")
                # 注入 plugins.gov_db
                if "plugins" not in record:
                    record["plugins"] = {}
                
                stations = engine.get_stations_for_river(r_code) if r_code else []
                r_info = engine.get_river(r_code) if r_code else None

                record["plugins"]["gov_db"] = {
                    "river_office": r_info.get("river_office") if r_info else None,
                    "primary_county": r_info.get("primary_county") if r_info else None,
                    "stream_order": r_info.get("stream_order") if r_info else None,
                    "associated_stations_count": len(stations),
                    "associated_stations": [s["station_name"] for s in stations]
                }
                print(json.dumps(record, ensure_ascii=False))
            except Exception as e:
                sys.stderr.write(f"警告: 解析 JSONL 行失敗: {e}\n")

    elif args.subcommand == "sync-rivers":
        from sync_wra_civ_rivers import sync_wra_civ_rivers
        src_path = Path(args.source) if args.source else None
        res = sync_wra_civ_rivers(db_path=db_target, jsonl_path=src_path, force=args.force)
        if args.json:
            print(json.dumps(res, ensure_ascii=False))

    elif args.subcommand == "status":
        conn = get_db_connection(args.db)
        cursor = conn.cursor()
        r_total = 0
        r_official = 0
        r_civ = 0
        s_count = 0
        last_sync = "NEVER"
        try:
            r_total = cursor.execute("SELECT count(*) FROM river_registry;").fetchone()[0]
            r_official = cursor.execute("SELECT count(*) FROM river_registry WHERE is_civilian = 0;").fetchone()[0]
            r_civ = cursor.execute("SELECT count(*) FROM river_registry WHERE is_civilian = 1;").fetchone()[0]
            s_count = cursor.execute("SELECT count(*) FROM station_registry;").fetchone()[0]
            h_row = cursor.execute("SELECT synced_at FROM sync_history ORDER BY id DESC LIMIT 1;").fetchone()
            if h_row:
                last_sync = h_row[0]
        except Exception:
            pass
        conn.close()

        status_data = {
            "module": "g30_hydrology_indexer",
            "cgs_version": __cli_spec_version__,
            "version": __version__,
            "database_path": str(db_target),
            "total_rivers": r_total,
            "official_rivers": r_official,
            "civilian_rivers": r_civ,
            "stations_count": s_count,
            "last_wra_civ_sync": last_sync,
            "wra_civ_mode": "STANDALONE_FALLBACK" if args.no_wra else "ENHANCED_CONNECTED",
            "status": "HEALTHY"
        }
        if args.json:
            print(json.dumps(status_data, ensure_ascii=False))
        else:
            print(f"=== {status_data['module']} (CGS v{status_data['cgs_version']}) 狀態看板 ===")
            print(f"收錄水脈總數: {r_total} 筆 (官方: {r_official} 筆 | 民間拓樸: {r_civ} 筆)")
            print(f"水文/雨量測站: {s_count} 站")
            print(f"上次 WRA-Civ 同步: {last_sync}")
            print(f"運行模式: {status_data['wra_civ_mode']}")
            print(f"狀態: {status_data['status']}")


if __name__ == "__main__":
    main()
