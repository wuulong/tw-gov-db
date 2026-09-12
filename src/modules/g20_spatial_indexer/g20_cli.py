#!/usr/bin/env python3
"""
[metadata]
spec: events-2026Q3/gov-db-in/tw-gov-db/docs/specs/g20_spatial_indexer.spec.md
manual: scripts/manuals/g20_cli.md
description: G20 空間地籍與地址基石 CLI 工具，支援門牌地址串流正規化、地籍號查詢與郵遞區號反查。
compat: posix
"""
import sys
import os
import argparse
import json
import re
import sqlite3

__cli_spec_version__ = "2.4"

# Global database connection path
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/universal_keys.sqlite"))

def resolve_input_stream(args_input: str = None) -> str:
    """CGS v2.4 Helper: Resolve input string from argument, stdin pipe, or file."""
    if args_input and args_input != "-":
        if os.path.exists(args_input):
            with open(args_input, "r", encoding="utf-8") as f:
                return f.read().strip()
        return args_input.strip()
    elif not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""

# Old County/Town Upgrade Mapping Dictionary (舊制升格對照字典)
HISTORICAL_UPGRADE_MAP = {
    "桃園縣": "桃園市", "台中縣": "臺中市", "台南縣": "臺南市",
    "高雄縣": "高雄市", "台北縣": "新北市", "臺北縣": "新北市"
}

def parse_address_string(address_raw: str) -> dict:
    """Address Normalizer: Parse Taiwan address string to canonical components & AIS Score."""
    if not address_raw:
        return {"error": "Empty input address"}

    # Precise Non-greedy Pattern matching county, town, street
    pattern = r"^(?P<county>[\u4e00-\u9fa5]{2,3}[縣市])?(?P<town>[\u4e00-\u9fa5]{1,3}?(?:鄉|鎮|市|區))(?P<rest>.*)$"
    match = re.match(pattern, address_raw.strip())
    
    county = match.group("county") if match and match.group("county") else ""
    town = match.group("town") if match and match.group("town") else ""
    rest = match.group("rest") if match and match.group("rest") else address_raw.strip()

    # Historical Disambiguation: Check old county upgrade
    is_historical = False
    original_county = county
    if county in HISTORICAL_UPGRADE_MAP:
        county = HISTORICAL_UPGRADE_MAP[county]
        is_historical = True
        if town.endswith("市"):
            town = town[:-1] + "區"

    # Lookup Zipcode & Admin Code
    zipcode = ""
    admin_code = ""

    if os.path.exists(DB_PATH) and (county or town):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            query = "SELECT zipcode, admin_code, county_name, town_name FROM zipcode_registry WHERE 1=1"
            params = []
            if county:
                query += " AND county_name LIKE ?"
                params.append(f"%{county[0:2]}%")
            if town:
                query += " AND town_name LIKE ?"
                params.append(f"%{town}%")
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                zipcode, admin_code, canonical_county, canonical_town = row
                county = canonical_county
                town = canonical_town
            conn.close()
        except Exception:
            pass

    # Compute AIS (Address Integrity Score) Quality Indicator
    ais_score = "🔴 LOW"
    if county and town and rest and zipcode:
        ais_score = "🟢 HIGH"
    elif county and town:
        ais_score = "🟡 MEDIUM"

    return {
        "raw_address": address_raw,
        "zipcode": zipcode,
        "admin_code": admin_code,
        "county": county,
        "town": town,
        "rest": rest,
        "canonical_address": f"{county}{town}{rest}",
        "historical_upgraded": is_historical,
        "ais_quality_score": ais_score
    }

def cmd_align_address(args):
    """Align and normalize Taiwan address stream."""
    raw_text = resolve_input_stream(args.input)
    if not raw_text:
        sys.stderr.write("⚠️  Warning: No input address provided via stdin or argument.\n")
        print(json.dumps({"results": []}, ensure_ascii=False, indent=2 if not args.quiet else None))
        return

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    results = [parse_address_string(line) for line in lines]

    if args.json:
        print(json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(f"[{item.get('zipcode', 'N/A')}] {item.get('canonical_address', item.get('raw_address'))} (Code: {item.get('admin_code', 'N/A')})")

def cmd_lookup_cadastral(args):
    """Lookup and normalize Cadastral section / land IDs."""
    raw_query = resolve_input_stream(args.query)
    if not raw_query:
        sys.stderr.write("⚠️  Warning: No cadastral query provided.\n")
        print(json.dumps({"results": []}, ensure_ascii=False))
        return

    # Normalize cadastral land number format (e.g. 100號 -> 00100)
    match = re.search(r"(\d+)號?", raw_query)
    land_num = match.group(1) if match else "0"
    cadastral_id = f"10004010-{int(land_num):05d}"

    result = {
        "query": raw_query,
        "cadastral_id": cadastral_id,
        "section_name": "標準地籍段",
        "land_number": land_num
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"地籍號: {cadastral_id} | 查詢: {raw_query}")

def cmd_search_zipcode(args):
    """Search Zipcodes and Admin Codes."""
    raw_query = resolve_input_stream(args.query)
    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT zipcode, county_name, town_name, admin_code FROM zipcode_registry
    WHERE zipcode LIKE ? OR county_name LIKE ? OR town_name LIKE ?
    """, (f"%{raw_query}%", f"%{raw_query}%", f"%{raw_query}%"))
    rows = cursor.fetchall()
    conn.close()

    results = [
        {"zipcode": r[0], "county": r[1], "town": r[2], "admin_code": r[3]}
        for r in rows
    ]

    if args.json:
        print(json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{r['zipcode']}] {r['county']}{r['town']} (AdminCode: {r['admin_code']})")

def cmd_status(args):
    """Report G20 submodule status and database records."""
    record_count = 0
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM zipcode_registry")
            record_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

    status_data = {
        "submodule": "g20_spatial_indexer",
        "spec_version": __cli_spec_version__,
        "db_path": DB_PATH,
        "db_exists": os.path.exists(DB_PATH),
        "zipcode_records": record_count,
        "status": "HEALTHY" if os.path.exists(DB_PATH) and record_count > 0 else "UNINITIALIZED"
    }

    if args.json:
        print(json.dumps(status_data, ensure_ascii=False, indent=2))
    else:
        print(f"🌐 [G20 Spatial Indexer] Status: {status_data['status']}")
        print(f"  • Spec Version: {status_data['spec_version']}")
        print(f"  • DB Exists: {status_data['db_exists']} ({record_count} zipcode records)")

def main():
    parser = argparse.ArgumentParser(description="G20 空間地籍與地址基石 CLI 工具 (CGS v2.4)")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Common options for subcommands
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-j", "--json", action="store_true", help="Output results in JSON format")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential warnings/logs")

    # align-address
    p_align = subparsers.add_parser("align-address", parents=[parent_parser], help="Align and normalize Taiwan address stream")
    p_align.add_argument("input", nargs="?", default=None, help="Input address text, file path, or - for stdin")
    p_align.set_defaults(func=cmd_align_address)

    # lookup-cadastral
    p_cadastral = subparsers.add_parser("lookup-cadastral", parents=[parent_parser], help="Lookup and normalize Cadastral section/land IDs")
    p_cadastral.add_argument("query", nargs="?", default=None, help="Cadastral text query or - for stdin")
    p_cadastral.set_defaults(func=cmd_lookup_cadastral)

    # search-zipcode
    p_zip = subparsers.add_parser("search-zipcode", parents=[parent_parser], help="Search Zipcodes and Admin Codes")
    p_zip.add_argument("query", nargs="?", default="", help="Zipcode or county/town query")
    p_zip.set_defaults(func=cmd_search_zipcode)

    # status
    p_status = subparsers.add_parser("status", parents=[parent_parser], help="Report G20 submodule status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)

if __name__ == "__main__":
    main()
