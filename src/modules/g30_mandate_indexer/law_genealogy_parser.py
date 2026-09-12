#!/usr/bin/env python3
"""
Law Genealogy Extraction Parser for G30 Mandate Indexer (g30_mandate_indexer)
Parses law_db / law_cli texts to extract organization genealogy events with rating taxonomy.
"""
import os
import sys
import json
import re
import sqlite3
from datetime import datetime

# Path to master_agencies.sqlite & GDS OID reference CSV
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/master_agencies.sqlite"))
OID_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../data/open-data/downloads/政府機關唯一識別代碼(OID)_1.csv"))

# Built-in OID Lookup Dictionary loaded from OID_CSV_PATH
OID_LOOKUP_MAP = {}

def load_oid_lookup_map():
    """Load canonical OID lookup map from GDS.csv if available."""
    global OID_LOOKUP_MAP
    if not OID_LOOKUP_MAP and os.path.exists(OID_CSV_PATH):
        try:
            import csv
            with open(OID_CSV_PATH, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("OrgName", "").strip()
                    oid = row.get("OID", "").strip()
                    if name and oid:
                        OID_LOOKUP_MAP[name] = oid
        except Exception:
            pass

def parse_law_text_for_genealogy(law_title: str, article_title: str, text: str, pcode: str = "") -> dict:
    """
    LawGenealogyParser Algorithm:
    Extracts predecessor/successor names, event types, effective dates, and calculates confidence rating.
    """
    load_oid_lookup_map()
    
    event_type = "UPGRADE"
    predecessor_name = ""
    successor_name = ""
    effective_date = ""
    
    # Rule 1: Pattern matching for Repeal / Expiration (廢止失效)
    # e.g. "本條例於行政院組織法暨農業部組織法通過生效後失效"
    match_repeal = re.search(r"(?P<old>[\u4e00-\u9fa5]+?(?:委員會|局|署|部|院)組織條例)於.*?(?P<new>[\u4e00-\u9fa5]+?(?:部|署|局|委員會)組織法).*?通過生效後(?:失效|廢止)", text)
    if match_repeal:
        old_law = match_repeal.group("old")
        new_law = match_repeal.group("new")
        predecessor_name = old_law.replace("組織條例", "").replace("行政院", "").strip()
        successor_name = new_law.replace("組織法", "").strip()
        event_type = "UPGRADE"

    # Rule 2: Pattern matching for Reorganization / Rename (改制升格)
    # e.g. "行政院農業委員會於中華民國112年8月1日正式升格為農業部"
    match_upgrade = re.search(r"(?P<old>[\u4e00-\u9fa5]{2,15}?(?:委員會|局|署|部|院|處|會|所|中心|學校|館))(?:於|自)?(?:中華民國)?(?P<date>\d+年\d+月\d+日)?(?:正式)?(?:升格|改制|改編|改稱|劃歸|改組|成立|設立)為(?P<new>[\u4e00-\u9fa5]{2,15}?(?:部|署|局|委員會|處|會|所|中心|學校|館))", text)
    if match_upgrade and not predecessor_name:
        predecessor_name = match_upgrade.group("old").strip()
        successor_name = match_upgrade.group("new").strip()
        effective_date = match_upgrade.group("date") if match_upgrade.group("date") else ""
        event_type = "UPGRADE"

    # Rule 3: Pattern matching for Transition / Transfer (隨同移轉/改制)
    match_transition = re.search(r"(?P<old>[\u4e00-\u9fa5]{2,15}?(?:委員會|局|署|部|院|處|會|所|中心)).*?(?:機關改制|改組|移轉).*?(?:隨同移轉|撥歸)(?P<new>[\u4e00-\u9fa5]{2,15}?(?:部|署|局|委員會|處|會|所|中心))", text)
    if match_transition and not predecessor_name:
        predecessor_name = match_transition.group("old").strip()
        successor_name = match_transition.group("new").strip()
        event_type = "TRANSITION"

    if not predecessor_name and not successor_name:
        return None

    # OID Alignment & Rating Taxonomy
    pred_oid = OID_LOOKUP_MAP.get(predecessor_name, None)
    succ_oid = OID_LOOKUP_MAP.get(successor_name, None)

    completeness_level = "TEXT_ONLY"
    confidence_score = 0.7
    review_status = "NEEDS_PATCH"

    if pred_oid and succ_oid:
        completeness_level = "FULL_MATCH"
        confidence_score = 1.0
        review_status = "VERIFIED"
    elif pred_oid or succ_oid:
        completeness_level = "PARTIAL_MATCH"
        confidence_score = 0.85
        review_status = "PENDING_REVIEW"

    return {
        "predecessor_name": predecessor_name,
        "predecessor_oid": pred_oid,
        "successor_name": successor_name,
        "successor_oid": succ_oid,
        "event_type": event_type,
        "effective_date": effective_date,
        "law_name": law_title,
        "law_article": article_title,
        "pcode": pcode,
        "source_text": text.strip(),
        "completeness_level": completeness_level,
        "confidence_score": confidence_score,
        "review_status": review_status
    }

def fetch_laws_and_orders_from_law_cli() -> tuple:
    """Fetch potential genealogy law texts & abolished orders directly from law_cli UNIX CLI interface."""
    law_cli_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../scripts/law_db/law_cli.py"))
    
    article_corpus = []
    abolished_records = []
    load_oid_lookup_map()
    
    try:
        import subprocess
        cmd = [sys.executable, law_cli_path, "genealogy", "-n", "500", "-j"]
        env = os.environ.copy()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=encoding_utf8_compat(), env=env, check=True)
        items = json.loads(result.stdout)
        
        for item in items:
            src = item.get("source")
            if src == "article":
                article_corpus.append({
                    "law_title": item.get("law_title", ""),
                    "article_title": item.get("article_title", ""),
                    "pcode": item.get("pcode", ""),
                    "text": item.get("text", "")
                })
            elif src == "order_abolish":
                law_name = item.get("law_title", "")
                pcode = item.get("pcode", "")
                hist = item.get("text", "")
                
                pred_name = law_name.replace('組織條例', '').replace('暫行組織規程', '').replace('處務規程', '').replace('設置條例', '').strip()
                dates = re.findall(r'中華民國(?P<year>[一二三四五六七八九十百\d]+)年(?P<month>\d+)月(?P<day>\d+)日.*?公布廢止', hist)
                eff_date = f"中華民國{dates[-1][0]}年{dates[-1][1]}月{dates[-1][2]}日" if dates else ""
                
                pred_oid = OID_LOOKUP_MAP.get(pred_name, None)
                completeness = "PARTIAL_MATCH" if pred_oid else "TEXT_ONLY"
                conf_score = 0.85 if pred_oid else 0.7
                status = "PENDING_REVIEW" if pred_oid else "NEEDS_PATCH"
                
                abolished_records.append({
                    "predecessor_name": pred_name,
                    "predecessor_oid": pred_oid,
                    "successor_name": f"{pred_name}（廢止/待確認繼承）",
                    "successor_oid": None,
                    "event_type": "ABOLISH",
                    "effective_date": eff_date,
                    "law_name": law_name,
                    "law_article": "全文",
                    "pcode": pcode,
                    "source_text": hist[:200].strip(),
                    "completeness_level": completeness,
                    "confidence_score": conf_score,
                    "review_status": status
                })
    except Exception as e:
        sys.stderr.write(f"⚠️ Warning: Could not fetch from law_cli ({e}).\n")
        
    return article_corpus, abolished_records

def encoding_utf8_compat():
    return "utf-8"

def run_law_parser_pipeline(save_to_db: bool = True) -> list:
    """Run LawGenealogyParser dual-engine pipeline over law texts & history orders via law_cli."""
    law_corpus, abolished_records = fetch_laws_and_orders_from_law_cli()
    
    extracted_records = []
    seen_keys = set()
    
    if law_corpus:
        for item in law_corpus:
            res = parse_law_text_for_genealogy(item["law_title"], item["article_title"], item["text"], item["pcode"])
            if res:
                dedup_key = (res["predecessor_name"], res["successor_name"], res["law_name"])
                if dedup_key not in seen_keys:
                    seen_keys.add(dedup_key)
                    extracted_records.append(res)

    for ab in abolished_records:
        dedup_key = (ab["predecessor_name"], ab["successor_name"], ab["law_name"])
        if dedup_key not in seen_keys:
            seen_keys.add(dedup_key)
            extracted_records.append(ab)

    if save_to_db and os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for rec in extracted_records:
            cursor.execute("""
            INSERT INTO agency_genealogy 
            (predecessor_name, predecessor_oid, successor_name, successor_oid, event_type, effective_date, law_name, law_article, pcode, source_text, completeness_level, confidence_score, review_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                rec["predecessor_name"], rec["predecessor_oid"],
                rec["successor_name"], rec["successor_oid"],
                rec["event_type"], rec["effective_date"],
                rec["law_name"], rec["law_article"], rec["pcode"],
                rec["source_text"], rec["completeness_level"], rec["confidence_score"],
                rec["review_status"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        conn.commit()
        conn.close()

    return extracted_records

if __name__ == "__main__":
    records = run_law_parser_pipeline(save_to_db=True)
    print(f"✅ [LawGenealogyParser Engine] Processed & Extracted {len(records)} Law Genealogy Events:")
    print(json.dumps(records, ensure_ascii=False, indent=2))
