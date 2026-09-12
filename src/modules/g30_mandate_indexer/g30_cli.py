#!/usr/bin/env python3
r"""
[metadata]
name: g30_cli.py
title: G30 全政府跨部會法規處務規程與虛擬圖譜 CLI 工具
description: G30 全政府跨部會法規處務規程與虛擬圖譜 CLI 工具，支援組科職掌自動配對、law_cli PCode 直連、JIT 輕量動態組織變異推導、歷史演進圖譜審核與隨時修補。
category: gov_meta
spec: events-2026Q3/gov-db-in/tw-gov-db/docs/specs/SPECIFICATION_g30.md
manual: scripts/manuals/g30_cli.md
dependencies: sqlite3, json, sys, os, re
cgs_version: 2.4
compat: posix
pipe_recipes:
  - cat: 歷史機關清洗 ➔ 現行機關對位
    cmd: opendata_cli agencies "河川" -j | jq -r '.[].機關名稱' | g30_cli resolve-org --stdin -j
  - cat: 業務關鍵字 ➔ 職掌法條直連
    cmd: echo "農水路工程改善" | g30_cli match-mandate --stdin -j | jq -r '.[0] | "\(.pcode) \(.law_article)"' | xargs law_cli get
  - cat: 待修補組織審查 ➔ 批次檢視
    cmd: g30_cli genealogy --status NEEDS_PATCH -j | jq -r '.[].predecessor_name' | head -n 10
"""
import sys
import os
import argparse
import json
import sqlite3
import re
from datetime import datetime

__cli_spec_version__ = "2.4"

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/master_agencies.sqlite"))
OID_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../data/open-data/downloads/政府機關唯一識別代碼(OID)_1.csv"))

_CANONICAL_OID_MAP = None

def get_canonical_oid(org_name: str) -> str:
    """Lookup current official canonical OID from OID CSV dictionary."""
    global _CANONICAL_OID_MAP
    if _CANONICAL_OID_MAP is None:
        _CANONICAL_OID_MAP = {}
        if os.path.exists(OID_CSV_PATH):
            try:
                import csv
                with open(OID_CSV_PATH, "r", encoding="utf-8-sig", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        name = r.get("OrgName", "").strip()
                        oid = r.get("OID", "").strip()
                        if name and oid:
                            _CANONICAL_OID_MAP[name] = oid
            except Exception:
                pass

    if not org_name:
        return None
    # 1. 精準對位
    if org_name in _CANONICAL_OID_MAP:
        return _CANONICAL_OID_MAP[org_name]
    # 2. 去除全形半形空白
    cleaned = org_name.replace(" ", "").replace("　", "")
    if cleaned in _CANONICAL_OID_MAP:
        return _CANONICAL_OID_MAP[cleaned]
    # 3. 嘗試以結尾名稱匹配 (例如 "第二河川分署" 匹配 "經濟部水利署第二河川分署")
    for full_name, oid in _CANONICAL_OID_MAP.items():
        if full_name.endswith(org_name) or org_name.endswith(full_name):
            return oid
    # 4. 高公局等養護工程分局關鍵字彈性對合
    if "高速公路局" in org_name:
        for full_name, oid in _CANONICAL_OID_MAP.items():
            if "高速公路局" in full_name and "養護工程分局" in full_name:
                m = re.search(r"([北中南東]區)", org_name)
                if m and m.group(1) in full_name:
                    return oid
    return None

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

def cmd_match_mandate(args):
    """Match keywords/dataset titles to internal agency units, mandates, and law_cli PCode."""
    raw_query = resolve_input_stream(args.query)
    if not raw_query:
        sys.stderr.write("⚠️  Warning: No input query provided via stdin or argument.\n")
        print(json.dumps({"results": []}, ensure_ascii=False))
        return

    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT mandate_id, agency_oid, unit_name, law_name, law_article, pcode, mandate_text, keywords_json FROM agency_mandates")
    rows = cursor.fetchall()
    conn.close()

    matched = []
    for r in rows:
        m_id, oid, unit, law_name, law_article, pcode, text, kw_json = r
        kws = json.loads(kw_json) if kw_json else []
        hit_count = sum(1 for kw in kws if kw in raw_query or kw in text)
        if hit_count > 0 or raw_query in unit or raw_query in text:
            confidence = min(1.0, 0.5 + hit_count * 0.2)
            quality = "🟢 HIGH" if confidence >= 0.85 else ("🟡 MEDIUM" if confidence >= 0.6 else "🔴 LOW")
            matched.append({
                "mandate_id": m_id,
                "agency_oid": oid,
                "unit_name": unit,
                "law_name": law_name,
                "law_article": law_article,
                "pcode": pcode,
                "mandate_text": text,
                "confidence_score": round(confidence, 2),
                "mcs_quality_score": quality
            })

    matched.sort(key=lambda x: x["confidence_score"], reverse=True)

    if args.json:
        print(json.dumps({"query": raw_query, "count": len(matched), "results": matched}, ensure_ascii=False, indent=2))
    else:
        for item in matched:
            print(f"[{item['mcs_quality_score']}] {item['unit_name']} ({item['law_article']}, PCode: {item['pcode']}) - Score: {item['confidence_score']}")

def cmd_parse_laws(args):
    """Run LawGenealogyParser engine to parse law texts into genealogy entries."""
    from law_genealogy_parser import run_law_parser_pipeline
    results = run_law_parser_pipeline(save_to_db=args.save)
    if args.json:
        print(json.dumps({"count": len(results), "saved_to_db": args.save, "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"⚙️ [LawGenealogyParser Engine] Parsed {len(results)} entries (Save to DB: {args.save}):")
        for r in results:
            print(f"  • [{r['completeness_level']} / Conf: {r['confidence_score']}] {r['predecessor_name']} ➔ {r['successor_name']} ({r['event_type']} on {r['effective_date']}) -> Status: {r['review_status']}")

def cmd_patch_oid(args):
    """Patch predecessor or successor OID for a TEXT_ONLY entry."""
    if not args.id or not args.oid:
        sys.stderr.write("❌ Error: Target genealogy ID and --oid value are required.\n")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    target_col = "successor_oid" if args.target == "successor" else "predecessor_oid"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
    UPDATE agency_genealogy 
    SET {target_col} = ?, 
        completeness_level = CASE 
            WHEN (predecessor_oid IS NOT NULL AND ? IS NOT NULL) OR (successor_oid IS NOT NULL AND ? IS NOT NULL) THEN 'FULL_MATCH'
            ELSE 'PARTIAL_MATCH'
        END,
        confidence_score = CASE 
            WHEN (predecessor_oid IS NOT NULL AND ? IS NOT NULL) OR (successor_oid IS NOT NULL AND ? IS NOT NULL) THEN 1.0
            ELSE 0.85
        END,
        review_status = CASE 
            WHEN (predecessor_oid IS NOT NULL AND ? IS NOT NULL) OR (successor_oid IS NOT NULL AND ? IS NOT NULL) THEN 'VERIFIED'
            ELSE 'PENDING_REVIEW'
        END
    WHERE genealogy_id = ?
    """, (args.oid, args.oid, args.oid, args.oid, args.oid, args.oid, args.oid, args.id))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    res = {"id": args.id, "patched_col": target_col, "new_oid": args.oid, "status": "SUCCESS" if affected > 0 else "NOT_FOUND"}
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"✅ Patched entry {args.id}: set {target_col} = {args.oid}")

def cmd_genealogy(args):
    """Query organization genealogy graph and review statuses."""
    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT genealogy_id, predecessor_name, predecessor_oid, successor_name, successor_oid, event_type, effective_date, law_name, completeness_level, confidence_score, review_status FROM agency_genealogy WHERE 1=1"
    params = []
    if args.status:
        query += " AND review_status = ?"
        params.append(args.status)
    elif args.pending:
        query += " AND review_status = 'PENDING_REVIEW'"
    elif args.verified:
        query += " AND review_status = 'VERIFIED'"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = [
        {
            "genealogy_id": r[0],
            "predecessor": r[1],
            "predecessor_oid": r[2],
            "successor": r[3],
            "successor_oid": r[4],
            "event_type": r[5],
            "effective_date": r[6],
            "law_name": r[7],
            "completeness_level": r[8],
            "confidence_score": r[9],
            "review_status": r[10]
        }
        for r in rows
    ]

    if args.json:
        print(json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{r['review_status']}] [{r['completeness_level']} / {r['confidence_score']}] (ID: {r['genealogy_id']}) {r['predecessor']} ➔ {r['successor']} ({r['event_type']} on {r['effective_date']})")

def cmd_verify(args):
    """Verify or reject a pending genealogy entry."""
    if not args.id:
        sys.stderr.write("❌ Error: Target genealogy ID is required.\n")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    new_status = "REJECTED" if args.reject else "VERIFIED"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE agency_genealogy 
    SET review_status = ?, reviewed_by = 'admin_cli', reviewed_at = ?
    WHERE genealogy_id = ?
    """, (new_status, now_str, args.id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        msg = {"id": args.id, "status": new_status, "msg": f"Genealogy entry {args.id} successfully updated to {new_status}."}
    else:
        msg = {"id": args.id, "status": "NOT_FOUND", "msg": f"Genealogy ID {args.id} not found."}

    if args.json:
        print(json.dumps(msg, ensure_ascii=False, indent=2))
    else:
        print(f"✅ {msg['msg']}")

def cmd_backfill_oid(args):
    """Batch backfill official canonical OIDs into agency_genealogy table using official OID dictionary."""
    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT genealogy_id, successor_name, successor_oid FROM agency_genealogy;")
    rows = cursor.fetchall()

    updated_count = 0
    updates = []
    for gid, succ_name, current_oid in rows:
        if not succ_name:
            continue
        clean_name = succ_name.split("（")[0].strip()
        canonical_oid = get_canonical_oid(clean_name)
        if canonical_oid and canonical_oid != current_oid:
            updates.append((canonical_oid, gid))
            updated_count += 1

    if updates:
        cursor.executemany("""
        UPDATE agency_genealogy 
        SET successor_oid = ?,
            completeness_level = CASE WHEN predecessor_oid IS NOT NULL THEN 'FULL_MATCH' ELSE 'PARTIAL_MATCH' END,
            confidence_score = CASE WHEN predecessor_oid IS NOT NULL THEN 1.0 ELSE 0.85 END,
            review_status = CASE WHEN predecessor_oid IS NOT NULL THEN 'VERIFIED' ELSE 'PENDING_REVIEW' END
        WHERE genealogy_id = ?;
        """, updates)
        conn.commit()

    conn.close()
    res = {
        "total_records": len(rows),
        "updated_count": updated_count,
        "msg": f"Backfilled canonical OID for {updated_count} / {len(rows)} records in agency_genealogy."
    }
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"✅ {res['msg']}")

def cmd_patch(args):
    """Patch/Insert or Update an organizational change manually."""
    raw_input = resolve_input_stream(args.input)
    if not raw_input:
        sys.stderr.write("❌ Error: Input JSON for patch is required.\n")
        sys.exit(1)

    try:
        data = json.loads(raw_input)
    except Exception as e:
        sys.stderr.write(f"❌ Error: Failed to parse input JSON: {e}\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    target_id = getattr(args, "id", None) or data.get("genealogy_id")
    if target_id:
        # 更新既有條目
        fields = []
        vals = []
        for col in ["predecessor_name", "predecessor_oid", "successor_name", "successor_oid", "event_type", "effective_date", "legal_basis", "source_text", "review_status"]:
            if col in data:
                fields.append(f"{col} = ?")
                vals.append(data[col])
        if fields:
            vals.append(target_id)
            cursor.execute(f"UPDATE agency_genealogy SET {', '.join(fields)} WHERE genealogy_id = ?;", vals)
            conn.commit()
        conn.close()
        res = {"patch_id": target_id, "status": "UPDATED", "msg": f"Successfully updated patch entry ID {target_id}"}
    else:
        # 新增條目
        cursor.execute("""
        INSERT INTO agency_genealogy (predecessor_name, predecessor_oid, successor_name, successor_oid, event_type, effective_date, legal_basis, source_text, review_status, reviewed_by, reviewed_at, attributes_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            data.get("predecessor_name", ""),
            data.get("predecessor_oid", ""),
            data.get("successor_name", ""),
            data.get("successor_oid", ""),
            data.get("event_type", "UPGRADE"),
            data.get("effective_date", datetime.now().strftime("%Y-%m-%d")),
            data.get("legal_basis", "手動修補補釘"),
            data.get("source_text", "由 g30_cli.py patch 手動新增"),
            "VERIFIED",
            "patch_cli",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps({"source": "manual_patch"}, ensure_ascii=False)
        ))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        res = {"patch_id": new_id, "status": "VERIFIED", "msg": f"Successfully inserted patch entry ID {new_id}"}

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"✅ {res['msg']}")

def cmd_alias(args):
    """Align raw publisher alias to canonical agency OID."""
    raw_query = resolve_input_stream(args.query)
    if not raw_query:
        sys.stderr.write("⚠️  Warning: No publisher query provided.\n")
        print(json.dumps({"results": []}, ensure_ascii=False))
        return

    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT raw_publisher_name, mapped_agency_oid, confidence_score, attributes_json 
    FROM publisher_aliases 
    WHERE raw_publisher_name LIKE ? OR mapped_agency_oid LIKE ?
    """, (f"%{raw_query}%", f"%{raw_query}%"))
    rows = cursor.fetchall()
    conn.close()

    results = [
        {
            "raw_publisher": r[0],
            "mapped_agency_oid": r[1],
            "confidence_score": r[2],
            "attributes": json.loads(r[3]) if r[3] else {}
        }
        for r in rows
    ]

    if args.json:
        print(json.dumps({"query": raw_query, "count": len(results), "results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{r['confidence_score']}] {r['raw_publisher']} ➔ OID: {r['mapped_agency_oid']}")

def cmd_status(args):
    """Report G30 submodule status and pending review statistics."""
    mandate_count = 0
    total_genealogy = 0
    pending_count = 0

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM agency_mandates")
            mandate_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agency_genealogy")
            total_genealogy = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agency_genealogy WHERE review_status = 'PENDING_REVIEW'")
            pending_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

    status_data = {
        "submodule": "g30_mandate_indexer",
        "spec_version": __cli_spec_version__,
        "db_path": DB_PATH,
        "db_exists": os.path.exists(DB_PATH),
        "mandates_records": mandate_count,
        "total_genealogy_records": total_genealogy,
        "pending_review_count": pending_count,
        "status": "HEALTHY" if os.path.exists(DB_PATH) else "UNINITIALIZED"
    }

    if args.json:
        print(json.dumps(status_data, ensure_ascii=False, indent=2))
    else:
        print(f"🌐 [G30 Mandate Indexer] Status: {status_data['status']}")
        print(f"  • Spec Version: {status_data['spec_version']}")
        print(f"  • Mandates: {mandate_count} | Genealogy: {total_genealogy} (🟡 Pending: {pending_count})")

def resolve_single_org(query: str, cursor) -> dict:
    """Core function to resolve a single agency query via exact match or JIT macro derivation."""
    query = query.strip()
    if not query:
        return None

    # 1. 精準/模糊實體比對
    cursor.execute("SELECT predecessor_name, successor_name, event_type, effective_date, law_name, source_text FROM agency_genealogy WHERE predecessor_name = ? OR successor_name = ?;", (query, query))
    direct_hits = cursor.fetchall()
    
    if direct_hits:
        r = direct_hits[0]
        successor_val = r[1]
        succ_oid = get_canonical_oid(successor_val)
        return {
            "query": query,
            "match_type": "EXACT",
            "predecessor": r[0],
            "successor": successor_val,
            "successor_oid": succ_oid,
            "event_type": r[2],
            "effective_date": r[3],
            "law_name": r[4],
            "description": r[5]
        }

    # 2. 通用範疇範本動態 JIT 推導 (Universal Macro Derivation Engine)
    # 支援全政府跨部會形如「[主管機關]各[分支單位]」➔「[新主管機關]各[新分支單位]」之動態匹配
    cursor.execute("SELECT predecessor_name, successor_name, event_type, effective_date, law_name, source_text FROM agency_genealogy WHERE predecessor_name LIKE '%各%';")
    macro_rules = cursor.fetchall()
    for rule in macro_rules:
        pred_rule = rule[0]
        succ_rule = rule[1]
        
        # 拆解前身規則中的父機關與分支關鍵字 (例如: "經濟部水利署各河川局" -> parent="經濟部水利署", unit="河川局")
        parts = pred_rule.split('各', 1)
        parent_prefix = parts[0]
        unit_suffix = parts[1] if len(parts) > 1 else ""

        # 動態建立通用匹配正規表示式：可選的父機關前綴 + 分支名稱捕獲 + 單位特徵
        # 例如: (?:經濟部水利署)?(?P<branch>[\u4e00-\u9fa5]+?)河川局$
        escaped_parent = re.escape(parent_prefix)
        escaped_unit = re.escape(unit_suffix)
        p_pattern = rf"^(?:{escaped_parent})?(?P<branch>[\u4e00-\u9fa5]+?){escaped_unit}$"
        
        m = re.search(p_pattern, query)
        if m:
            branch_name = m.group('branch')
            # 若規則中的單位帶有「區」（如各區分署），而輸入分支亦帶有「區」（如南區），進行邊界防重疊平滑
            clean_branch = branch_name
            target_succ = succ_rule
            if target_succ.find('各區') != -1 and clean_branch.endswith('區'):
                target_succ = target_succ.replace('各區', '各')
            
            derived_successor = target_succ.replace('各', clean_branch)
            succ_oid = get_canonical_oid(derived_successor)
            return {
                "query": query,
                "match_type": "JIT_MACRO_DERIVED",
                "predecessor": query,
                "successor": derived_successor,
                "successor_oid": succ_oid,
                "event_type": rule[2],
                "effective_date": rule[3],
                "law_name": rule[4],
                "macro_rule": f"{pred_rule} ➔ {succ_rule}",
                "description": rule[5]
            }

    return {
        "query": query,
        "match_type": "NONE",
        "message": "未命中組織變異規則"
    }

def cmd_resolve_org(args):
    """JIT Genealogy Resolver: Resolve single or batch organization names from argument or stdin pipe."""
    raw_input = resolve_input_stream(args.query if not getattr(args, "stdin", False) else None)
    if not raw_input and getattr(args, "stdin", False):
        raw_input = sys.stdin.read().strip()
    if not raw_input and args.query:
        raw_input = args.query.strip()

    if not raw_input:
        sys.stderr.write("❌ Error: Target organization name or pipe stdin input is required.\n")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"❌ Error: Database not found at {DB_PATH}\n")
        sys.exit(1)

    # 判斷是否為批次輸入 (JSON 陣列或多行字串)
    queries = []
    if raw_input.startswith("[") and raw_input.endswith("]"):
        try:
            parsed = json.loads(raw_input)
            if isinstance(parsed, list):
                queries = [str(x) for x in parsed]
        except Exception:
            pass
    if not queries:
        queries = [line.strip() for line in raw_input.splitlines() if line.strip()]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    results = []
    for q in queries:
        res = resolve_single_org(q, cursor)
        if res:
            results.append(res)

    conn.close()

    if args.json:
        if len(results) == 1 and not getattr(args, "stdin", False) and not (raw_input.startswith("[") and raw_input.endswith("]")):
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for resolved in results:
            if resolved and resolved.get("match_type") != "NONE":
                print(f"🟢 [JIT 組織對向解析成功 ({resolved['match_type']})]")
                print(f"   • 查詢標的: {resolved['query']}")
                print(f"   • 現行/繼承對應機關: 【{resolved['successor']}】")
                if resolved.get("successor_oid"):
                    print(f"   • 正式 OID: {resolved['successor_oid']}")
                print(f"   • 改制生效日期: {resolved['effective_date']}")
                print(f"   • 沿革說明: {resolved['description']}")
                print(f"   • 依據法規: {resolved['law_name']}")
            else:
                print(f"🔴 [JIT 提示] 查無歷史變異紀錄: {resolved['query']}")

def cmd_schema(args):
    """CGS v2.4 Schema Protocol: Output canonical JSON schema for g30_cli."""
    schema_dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "G30MandateIndexerSchema",
        "description": "Schema definition for g30_cli.py (CGS v2.4)",
        "version": "2.4",
        "subcommands": {
            "resolve-org": {
                "description": "JIT runtime agency genealogy resolver (exact match and macro rule derivation)",
                "arguments": ["query", "--stdin", "-j/--json", "-q/--quiet"]
            },
            "match-mandate": {
                "description": "Match task/dataset keywords to internal agency unit mandates and law_cli PCode",
                "arguments": ["query", "--stdin", "-j/--json", "-q/--quiet"]
            },
            "genealogy": {
                "description": "Query agency genealogy records and review statuses",
                "arguments": ["--status", "--pending", "--verified", "-j/--json"]
            },
            "alias": {
                "description": "Align messy publisher name to canonical OID",
                "arguments": ["query", "-j/--json"]
            },
            "parse-laws": {
                "description": "Run dual-engine law parser across law_cli stream",
                "arguments": ["--save", "-j/--json"]
            },
            "patch-oid": {
                "description": "Patch OID code for TEXT_ONLY records",
                "arguments": ["id", "--oid", "--target"]
            },
            "backfill-oid": {
                "description": "Batch backfill official canonical OIDs into agency_genealogy table",
                "arguments": ["-j/--json"]
            },
            "status": {
                "description": "Report G30 database and spec status",
                "arguments": ["-j/--json"]
            }
        }
    }
    print(json.dumps(schema_dict, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description="G30 全政府跨部會法規處務規程與虛擬圖譜 CLI 工具 (CGS v2.4)")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-j", "--json", action="store_true", help="Output results in JSON format")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential warnings/logs")
    parent_parser.add_argument("-i", "--stdin", action="store_true", help="Read input from standard input stream (UNIX Pipe)")

    # resolve-org
    p_res = subparsers.add_parser("resolve-org", parents=[parent_parser], help="JIT resolve raw/old org name to current successor org at runtime")
    p_res.add_argument("query", nargs="?", default=None, help="Organization name to resolve (e.g. 第二河川局, 農委會)")
    p_res.set_defaults(func=cmd_resolve_org)

    # schema
    p_sch = subparsers.add_parser("schema", parents=[parent_parser], help="Output CGS v2.4 self-describing JSON schema")
    p_sch.set_defaults(func=cmd_schema)

    # alias
    p_alias = subparsers.add_parser("alias", parents=[parent_parser], help="Align raw publisher name to canonical agency OID")
    p_alias.add_argument("query", nargs="?", default=None, help="Publisher name or OID to query")
    p_alias.set_defaults(func=cmd_alias)

    # match-mandate
    p_match = subparsers.add_parser("match-mandate", parents=[parent_parser], help="Match keywords to agency mandates")
    p_match.add_argument("query", nargs="?", default=None, help="Query keyword, dataset title, or - for stdin")
    p_match.set_defaults(func=cmd_match_mandate)

    # parse-laws
    p_par = subparsers.add_parser("parse-laws", parents=[parent_parser], help="Run LawGenealogyParser engine to parse law texts")
    p_par.add_argument("--save", action="store_true", help="Save extracted entries directly to SQLite database")
    p_par.set_defaults(func=cmd_parse_laws)

    # patch-oid
    p_poid = subparsers.add_parser("patch-oid", parents=[parent_parser], help="Patch predecessor or successor OID for a TEXT_ONLY entry")
    p_poid.add_argument("id", type=int, help="Target genealogy ID")
    p_poid.add_argument("--oid", required=True, help="Canonical OID to patch")
    p_poid.add_argument("--target", choices=["predecessor", "successor"], default="successor", help="Which OID to patch (default: successor)")
    p_poid.set_defaults(func=cmd_patch_oid)

    # genealogy
    p_gen = subparsers.add_parser("genealogy", parents=[parent_parser], help="Query genealogy graph and review status")
    p_gen.add_argument("--pending", action="store_true", help="Filter pending review entries only")
    p_gen.add_argument("--verified", action="store_true", help="Filter verified entries only")
    p_gen.add_argument("--status", choices=["PENDING_REVIEW", "VERIFIED", "NEEDS_PATCH", "REJECTED"], help="Filter by exact review status")
    p_gen.set_defaults(func=cmd_genealogy)

    # verify
    p_ver = subparsers.add_parser("verify", parents=[parent_parser], help="Verify or reject a pending genealogy entry")
    p_ver.add_argument("id", type=int, help="Target genealogy ID to verify")
    p_ver.add_argument("--reject", action="store_true", help="Reject the entry instead of verifying")
    p_ver.set_defaults(func=cmd_verify)

    # backfill-oid
    p_boid = subparsers.add_parser("backfill-oid", parents=[parent_parser], help="Batch backfill official canonical OIDs into agency_genealogy table")
    p_boid.set_defaults(func=cmd_backfill_oid)

    # patch
    p_patch = subparsers.add_parser("patch", parents=[parent_parser], help="Patch/Insert or update an organizational change manually")
    p_patch.add_argument("--id", type=int, default=None, help="Target genealogy ID to update")
    p_patch.add_argument("input", nargs="?", default=None, help="Patch JSON string, file path, or - for stdin")
    p_patch.set_defaults(func=cmd_patch)

    # status
    p_status = subparsers.add_parser("status", parents=[parent_parser], help="Report G30 submodule status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)

if __name__ == "__main__":
    main()
