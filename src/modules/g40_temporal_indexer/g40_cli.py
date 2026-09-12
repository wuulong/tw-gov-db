#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
[metadata]
name: g40_cli.py
title: G40 全政府時間、辦公日曆與時序維度器 CLI 工具
description: G40 全政府時間、辦公日曆與時序維度器 CLI 工具，支援全政府民國年/西元年極速清洗、行政院核定辦公日曆與營業日判定、會計年度時序分桶與天災假時空碰撞。
category: gov_meta
spec: events-2026Q3/gov-db-in/tw-gov-db/docs/specs/SPECIFICATION_g40.md
manual: scripts/manuals/g40_cli.md
dependencies: sqlite3, json, sys, os, re, datetime
cgs_version: 2.4
compat: posix
pipe_recipes:
  - cat: 開放資料異質民國年清洗 ➔ 現行機關對位 ➔ 空間正規化
    cmd: echo "112/08/15" | g40_cli clean-date --stdin -j
  - cat: 農業災損申報日 ➔ 辦公日曆與天災假檢驗
    cmd: echo "2024-10-31" | g40_cli check --stdin -j
  - cat: 政府採購標案 ➔ 履約法定工作日數計算
    cmd: g40_cli range 2024-01-01 2024-01-31 --working-days-only -j
"""
import sys
import os
import argparse
import json
import sqlite3
import re
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

# 匯入同模組之純 Python 農曆與二十四節氣引擎
try:
    from .lunar_engine import solar_to_lunar, lunar_to_solar, get_solar_terms_for_year
except (ImportError, ValueError):
    from lunar_engine import solar_to_lunar, lunar_to_solar, get_solar_terms_for_year

__cli_spec_version__ = "2.4"

# 定錨 universal_keys.sqlite 路徑
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "../../../data/universal_keys.sqlite"))
CALENDAR_CSV_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "../../../../../../data/open-data/downloads/taipei_calendar_full.csv"))
if not os.path.exists(CALENDAR_CSV_PATH):
    CALENDAR_CSV_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "../../../../../../data/open-data/downloads/ntpc_calendar_2018_2027.csv"))


def resolve_input_stream(args_input: str = None) -> str:
    """CGS v2.4 Helper: Resolve input string from argument, stdin pipe, or file."""
    if args_input and args_input != "-":
        if os.path.exists(args_input):
            with open(args_input, "r", encoding="utf-8") as f:
                return f.read().strip()
        return args_input.strip()
    if not sys.stdin.isatty():
        try:
            return sys.stdin.read().strip()
        except Exception:
            return ""
    return ""


def clean_date_string(raw_date: str) -> Optional[Dict[str, Any]]:
    """
    Core normalization algorithm for all Taiwan heterogeneous date strings:
    Supports:
      - 113/08/22, 113-08-22, 113.08.22, 1130822
      - 2024/08/22, 2024-08-22, 2024.08.22, 20240822
      - 民國113年8月22日, 113年8月22日, 2024年8月22日
      - 113Q3, 2024Q3, 113-Q3, 2024-Q3
      - 113上 / 113下 (半年度)
    """
    if not raw_date:
        return None
    d_str = str(raw_date).strip()

    # 1. 季別模式: 113Q3, 2024Q3, 113-Q3, 2024-Q3
    q_match = re.match(r"^(?:民國)?(?P<year>\d{2,4})[-\s]?[Qq](?P<quarter>[1-4])$", d_str)
    if q_match:
        y_val = int(q_match.group("year"))
        year = y_val + 1911 if y_val < 1900 else y_val
        minguo_year = year - 1911
        quarter = int(q_match.group("quarter"))
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        # 計算季底日期
        if end_month in [3, 12]:
            end_day = 31
        elif end_month == 6:
            end_day = 30
        else:
            end_day = 30
        return {
            "raw_input": d_str,
            "type": "QUARTER",
            "year": year,
            "minguo_year": minguo_year,
            "quarter": quarter,
            "start_date": f"{year:04d}-{start_month:02d}-01",
            "end_date": f"{year:04d}-{end_month:02d}-{end_day:02d}",
            "iso_format": f"{year:04d}-Q{quarter}"
        }

    # 1.1 農曆中文日期格式: 農曆(民國)?113年五月初五 / 陰曆2024年正月初一 / 農曆113年5月5日
    lunar_match = re.match(r"^(?:農曆|陰曆)(?:中華民國|民國)?(?P<year>\d{2,4})年(?P<leap>閏)?(?P<month>\d{1,2}|[正二三四五六七八九十冬臘])月(?:(?P<day>\d{1,2}|初[一二三四五六七八九十]|十[一二三四五六七八九]|[廿念][一二三四五六七八九]|三十))日?$", d_str)
    if lunar_match:
        y_val = int(lunar_match.group("year"))
        year = y_val + 1911 if y_val < 1900 else y_val
        m_raw = lunar_match.group("month")
        cn_m_map = {"正": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "冬": 11, "臘": 12}
        month = cn_m_map.get(m_raw, int(m_raw) if m_raw.isdigit() else 1)
        
        d_raw = lunar_match.group("day")
        cn_d_map = {
            "初一": 1, "初二": 2, "初三": 3, "初四": 4, "初五": 5, "初六": 6, "初七": 7, "初八": 8, "初九": 9, "初十": 10,
            "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15, "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
            "廿一": 21, "廿二": 22, "廿三": 23, "廿四": 24, "廿五": 25, "廿六": 26, "廿七": 27, "廿八": 28, "廿九": 29, "三十": 30,
            "念一": 21, "念二": 22, "念三": 23, "念四": 24, "念五": 25, "念六": 26, "念七": 27, "念八": 28, "念九": 29
        }
        day = cn_d_map.get(d_raw, int(d_raw) if d_raw and d_raw.isdigit() else 1)
        is_leap = bool(lunar_match.group("leap"))
        try:
            solar_info = lunar_to_solar(year, month, day, is_leap=is_leap)
            dt_obj = datetime.strptime(solar_info["solar_date"], "%Y-%m-%d").date()
            return {
                "raw_input": d_str,
                "type": "LUNAR_DATE",
                "year": dt_obj.year,
                "minguo_year": dt_obj.year - 1911,
                "month": dt_obj.month,
                "day": dt_obj.day,
                "date_str": solar_info["solar_date"],
                "iso_format": f"{solar_info['solar_date']}T00:00:00+08:00",
                "lunar": solar_info
            }
        except Exception as e:
            return {
                "raw_input": d_str,
                "type": "LUNAR_DATE",
                "error": f"農曆日期無效或超出計算範圍: {e}"
            }

    # 2. 中文年月日格式: (民國)?113年8月22日 / 2024年8月22日
    cn_match = re.match(r"^(?:中華民國|民國)?(?P<year>\d{2,4})年(?P<month>\d{1,2})月(?:(?P<day>\d{1,2})日)?", d_str)
    if cn_match:
        y_val = int(cn_match.group("year"))
        year = y_val + 1911 if y_val < 1900 else y_val
        month = int(cn_match.group("month"))
        day = int(cn_match.group("day")) if cn_match.group("day") else 1
        try:
            dt_obj = date(year, month, day)
            return {
                "raw_input": d_str,
                "type": "DATE" if cn_match.group("day") else "MONTH",
                "year": year,
                "minguo_year": year - 1911,
                "month": month,
                "day": day,
                "date_str": dt_obj.strftime("%Y-%m-%d"),
                "iso_format": f"{dt_obj.strftime('%Y-%m-%d')}T00:00:00+08:00"
            }
        except ValueError:
            pass

    # 3. 數值與分隔符號格式 (西元年或民國年): 113/08/22, 2024-08-22, 1130822, 20240822
    # 緊湊無分隔 8 碼 (西元) 或 7 碼 (民國)
    if re.match(r"^\d{8}$", d_str):
        year = int(d_str[:4])
        month = int(d_str[4:6])
        day = int(d_str[6:8])
        try:
            dt_obj = date(year, month, day)
            return {
                "raw_input": d_str,
                "type": "DATE",
                "year": year,
                "minguo_year": year - 1911,
                "month": month,
                "day": day,
                "date_str": dt_obj.strftime("%Y-%m-%d"),
                "iso_format": f"{dt_obj.strftime('%Y-%m-%d')}T00:00:00+08:00"
            }
        except ValueError:
            pass

    if re.match(r"^\d{7}$", d_str):
        y_val = int(d_str[:3])
        year = y_val + 1911
        month = int(d_str[3:5])
        day = int(d_str[5:7])
        try:
            dt_obj = date(year, month, day)
            return {
                "raw_input": d_str,
                "type": "DATE",
                "year": year,
                "minguo_year": y_val,
                "month": month,
                "day": day,
                "date_str": dt_obj.strftime("%Y-%m-%d"),
                "iso_format": f"{dt_obj.strftime('%Y-%m-%d')}T00:00:00+08:00"
            }
        except ValueError:
            pass

    # 帶有斜線、連字號、句號分隔
    sep_match = re.match(r"^(?P<year>\d{2,4})[/\-\.](?P<month>\d{1,2})[/\-\.](?P<day>\d{1,2})$", d_str)
    if sep_match:
        y_val = int(sep_match.group("year"))
        year = y_val + 1911 if y_val < 1900 else y_val
        month = int(sep_match.group("month"))
        day = int(sep_match.group("day"))
        try:
            dt_obj = date(year, month, day)
            return {
                "raw_input": d_str,
                "type": "DATE",
                "year": year,
                "minguo_year": year - 1911,
                "month": month,
                "day": day,
                "date_str": dt_obj.strftime("%Y-%m-%d"),
                "iso_format": f"{dt_obj.strftime('%Y-%m-%d')}T00:00:00+08:00"
            }
        except ValueError:
            pass

    # 4. 年月格式: 113/08, 2024-08
    ym_match = re.match(r"^(?P<year>\d{2,4})[/\-\.](?P<month>\d{1,2})$", d_str)
    if ym_match:
        y_val = int(ym_match.group("year"))
        year = y_val + 1911 if y_val < 1900 else y_val
        month = int(ym_match.group("month"))
        if 1 <= month <= 12:
            return {
                "raw_input": d_str,
                "type": "MONTH",
                "year": year,
                "minguo_year": year - 1911,
                "month": month,
                "date_str": f"{year:04d}-{month:02d}",
                "iso_format": f"{year:04d}-{month:02d}-01T00:00:00+08:00"
            }

    # 5. 年度格式: 113年度, 113年, 2024年度, 2024年, 或純年份 113 / 2024
    yr_match = re.match(r"^(?:中華民國|民國)?(?P<year>\d{2,4})(?:年度|年)?$", d_str)
    if yr_match:
        y_val = int(yr_match.group("year"))
        year = y_val + 1911 if y_val < 1900 else y_val
        return {
            "raw_input": d_str,
            "type": "YEAR",
            "year": year,
            "minguo_year": year - 1911,
            "start_date": f"{year:04d}-01-01",
            "end_date": f"{year:04d}-12-31",
            "iso_format": f"{year:04d}"
        }

    return {
        "raw_input": d_str,
        "type": "UNKNOWN",
        "error": "無法辨識之日期或年度格式"
    }


def ensure_calendar_table(conn: sqlite3.Connection):
    """Ensure calendar_registry table and indexes exist."""
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendar_registry (
        date_str VARCHAR(10) PRIMARY KEY,
        year INTEGER NOT NULL,
        minguo_year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        is_holiday BOOLEAN NOT NULL,
        is_working_day BOOLEAN NOT NULL,
        holiday_category VARCHAR(64),
        description VARCHAR(256),
        attributes_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_year ON calendar_registry(year);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_minguo ON calendar_registry(minguo_year);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_working ON calendar_registry(is_working_day);")
    conn.commit()


def init_calendar_from_csv(conn: sqlite3.Connection, csv_path: str = CALENDAR_CSV_PATH) -> int:
    """Import and populate calendar_registry table from Taipei or NTPC calendar CSV."""
    if not os.path.exists(csv_path):
        return 0
    ensure_calendar_table(conn)
    cursor = conn.cursor()

    import csv
    inserted_count = 0
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            raw_d = row.get("Date") or row.get("date") or ""
            raw_d = raw_d.strip()
            if not raw_d:
                continue

            # 正規化為 YYYY-MM-DD
            if len(raw_d) == 8 and raw_d.isdigit():
                y = int(raw_d[:4])
                m = int(raw_d[4:6])
                d = int(raw_d[6:8])
                date_str = f"{y:04d}-{m:02d}-{d:02d}"
            elif "-" in raw_d:
                date_str = raw_d
                pts = date_str.split("-")
                y, m, d = int(pts[0]), int(pts[1]), int(pts[2])
            else:
                continue

            try:
                dt_obj = date(y, m, d)
            except Exception:
                continue

            day_of_week = dt_obj.isoweekday() # 1=Mon ... 7=Sun
            is_hol_str = row.get("isHoliday") or row.get("isholiday") or ""
            is_holiday = is_hol_str.strip() in ["是", "Y", "1", True]
            
            category = (row.get("holidayCategory") or row.get("holidaycategory") or "").strip()
            desc = (row.get("description") or row.get("name") or "").strip()
            
            # 判斷是否為工作日 (補班日雖然是星期六，但 is_holiday 為 否)
            is_working_day = (not is_holiday)

            batch.append((
                date_str, y, y - 1911, m, d, day_of_week,
                1 if is_holiday else 0,
                1 if is_working_day else 0,
                category, desc, "{}"
            ))

        if batch:
            cursor.executemany("""
            INSERT OR REPLACE INTO calendar_registry 
            (date_str, year, minguo_year, month, day, day_of_week, is_holiday, is_working_day, holiday_category, description, attributes_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, batch)
            conn.commit()
            inserted_count = len(batch)

    return inserted_count


# --- 子命令實作 ---

def cmd_clean_date(args):
    """Clean heterogeneous date strings from argument or stdin pipe to standard ISO-8601."""
    raw_input = resolve_input_stream(args.query if not getattr(args, "stdin", False) else None)
    if not raw_input and getattr(args, "stdin", False):
        raw_input = sys.stdin.read().strip()
    if not raw_input and args.query:
        raw_input = args.query.strip()

    if not raw_input:
        sys.stderr.write("❌ Error: Target date query or pipe stdin input is required.\n")
        sys.exit(1)

    # 批次判斷 (JSON 陣列或多行字串)
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

    results = [clean_date_string(q) for q in queries]

    if args.json:
        if len(results) == 1 and not getattr(args, "stdin", False) and not (raw_input.startswith("[") and raw_input.endswith("]")):
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r and "error" not in r:
                print(f"📅 [{r['type']}] 原始輸入: {r['raw_input']} ➔ 標準日期: {r.get('date_str', r.get('iso_format'))} (民國 {r['minguo_year']} 年)")
            else:
                print(f"🔴 解析失敗: {r.get('raw_input') if r else '空值'}")


def cmd_check(args):
    """Check working day status, holiday category and description from calendar_registry."""
    raw_input = resolve_input_stream(args.query if not getattr(args, "stdin", False) else None)
    if not raw_input and getattr(args, "stdin", False):
        raw_input = sys.stdin.read().strip()
    if not raw_input and args.query:
        raw_input = args.query.strip()

    if not raw_input:
        sys.stderr.write("❌ Error: Target date query or pipe stdin input is required.\n")
        sys.exit(1)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_calendar_table(conn)

    # 若表為空，自動先自 CSV 載入
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM calendar_registry;")
    if cursor.fetchone()[0] == 0:
        init_calendar_from_csv(conn)

    queries = [line.strip() for line in raw_input.splitlines() if line.strip()]
    results = []

    for q in queries:
        cleaned = clean_date_string(q)
        target_date = cleaned.get("date_str") if cleaned and "date_str" in cleaned else q
        
        cursor.execute("""
        SELECT date_str, year, minguo_year, day_of_week, is_holiday, is_working_day, holiday_category, description 
        FROM calendar_registry WHERE date_str = ?;
        """, (target_date,))
        row = cursor.fetchone()

        lunar_info = None
        try:
            dt_parse = datetime.strptime(target_date, "%Y-%m-%d").date()
            lunar_info = solar_to_lunar(dt_parse)
        except Exception:
            pass

        if row:
            day_names = ["", "週一", "週二", "週三", "週四", "週五", "週六", "週日"]
            dow = row[3]
            res_item = {
                "query": q,
                "date_str": row[0],
                "year": row[1],
                "minguo_year": row[2],
                "day_of_week": dow,
                "day_of_week_name": day_names[dow] if 1 <= dow <= 7 else "",
                "is_holiday": bool(row[4]),
                "is_working_day": bool(row[5]),
                "holiday_category": row[6],
                "description": row[7]
            }
            if lunar_info:
                res_item["lunar_text"] = lunar_info["lunar_text"]
                res_item["lunar_festival"] = lunar_info["festival"]
                res_item["solar_term"] = lunar_info["solar_term"]
                res_item["sheng_xiao"] = lunar_info["sheng_xiao"]
            results.append(res_item)
        else:
            # 資料庫無記錄時根據星期幾推算預設
            try:
                dt_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
                dow = dt_obj.isoweekday()
                is_weekend = (dow >= 6)
                day_names = ["", "週一", "週二", "週三", "週四", "週五", "週六", "週日"]
                res_item = {
                    "query": q,
                    "date_str": target_date,
                    "year": dt_obj.year,
                    "minguo_year": dt_obj.year - 1911,
                    "day_of_week": dow,
                    "day_of_week_name": day_names[dow],
                    "is_holiday": is_weekend,
                    "is_working_day": not is_weekend,
                    "holiday_category": "星期六、星期日" if is_weekend else "一般平日",
                    "description": "非官方日曆表收錄日 (以週一至週五平日預設推估)"
                }
                if lunar_info:
                    res_item["lunar_text"] = lunar_info["lunar_text"]
                    res_item["lunar_festival"] = lunar_info["festival"]
                    res_item["solar_term"] = lunar_info["solar_term"]
                    res_item["sheng_xiao"] = lunar_info["sheng_xiao"]
                results.append(res_item)
            except Exception:
                results.append({
                    "query": q,
                    "error": f"無法識別之日期: {q}"
                })

    conn.close()

    if args.json:
        if len(results) == 1 and not getattr(args, "stdin", False):
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            if "error" in item:
                print(f"🔴 {item['error']}")
                continue
            status_tag = "💼 [上班日/營業日]" if item["is_working_day"] else "🏖️ [放假/非營業日]"
            desc = f"({item['description']})" if item['description'] else ""
            print(f"📅 {item['date_str']} ({item['day_of_week_name']}) ➔ {status_tag} 類別: {item['holiday_category']} {desc}")


def cmd_range(args):
    """Expand date sequence and calculate total working days within range."""
    start_info = clean_date_string(args.start_date)
    end_info = clean_date_string(args.end_date)

    if not start_info or "date_str" not in start_info:
        sys.stderr.write(f"❌ Error: Invalid start_date: {args.start_date}\n")
        sys.exit(1)
    if not end_info or "date_str" not in end_info:
        sys.stderr.write(f"❌ Error: Invalid end_date: {args.end_date}\n")
        sys.exit(1)

    s_dt = datetime.strptime(start_info["date_str"], "%Y-%m-%d").date()
    e_dt = datetime.strptime(end_info["date_str"], "%Y-%m-%d").date()

    if s_dt > e_dt:
        sys.stderr.write("❌ Error: start_date cannot be greater than end_date.\n")
        sys.exit(1)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_calendar_table(conn)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT date_str, is_working_day, is_holiday, holiday_category, description 
    FROM calendar_registry 
    WHERE date_str >= ? AND date_str <= ?
    ORDER BY date_str ASC;
    """, (start_info["date_str"], end_info["date_str"]))
    db_rows = {r[0]: r for r in cursor.fetchall()}
    conn.close()

    curr = s_dt
    days_list = []
    working_days_count = 0
    holidays_count = 0

    while curr <= e_dt:
        ds = curr.strftime("%Y-%m-%d")
        if ds in db_rows:
            r = db_rows[ds]
            is_work = bool(r[1])
            is_hol = bool(r[2])
            cat = r[3]
            desc = r[4]
        else:
            dow = curr.isoweekday()
            is_work = (dow < 6)
            is_hol = (dow >= 6)
            cat = "星期六、星期日" if is_hol else "一般平日"
            desc = ""

        if is_work:
            working_days_count += 1
        else:
            holidays_count += 1

        if not args.working_days_only or is_work:
            days_list.append({
                "date": ds,
                "is_working_day": is_work,
                "holiday_category": cat,
                "description": desc
            })
        curr += timedelta(days=1)

    total_days = (e_dt - s_dt).days + 1
    res = {
        "start_date": start_info["date_str"],
        "end_date": end_info["date_str"],
        "total_calendar_days": total_days,
        "total_working_days": working_days_count,
        "total_holidays": holidays_count,
        "days": days_list
    }

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"📊 [時序區間統計: {res['start_date']} ➔ {res['end_date']}]")
        print(f"  • 總日曆天數: {res['total_calendar_days']} 天")
        print(f"  • 法定工作日: {res['total_working_days']} 天")
        print(f"  • 放假/例假日: {res['total_holidays']} 天")


def cmd_bucket(args):
    """Expand fiscal year (e.g. 113) or quarter (e.g. 2024Q3) into structured temporal bucket."""
    cleaned = clean_date_string(args.bucket)
    if not cleaned or cleaned.get("type") not in ["QUARTER", "YEAR"]:
        # 嘗試解析為民國年或西元年
        b_str = args.bucket.replace("年度", "").replace("年", "").strip()
        if b_str.isdigit():
            y_val = int(b_str)
            year = y_val + 1911 if y_val < 1900 else y_val
            cleaned = {
                "type": "YEAR",
                "year": year,
                "minguo_year": year - 1911,
                "start_date": f"{year:04d}-01-01",
                "end_date": f"{year:04d}-12-31",
                "iso_format": f"{year:04d}"
            }

    if not cleaned or "start_date" not in cleaned:
        sys.stderr.write(f"❌ Error: Cannot parse temporal bucket '{args.bucket}'. Example: '113', '113年度', '2024Q3'\n")
        sys.exit(1)

    # 轉寄調用 range
    args.start_date = cleaned["start_date"]
    args.end_date = cleaned["end_date"]
    args.working_days_only = False
    cmd_range(args)


def cmd_lunar(args):
    """Convert between Solar and Lunar calendar, or query 24 Solar Terms."""
    # 1. 查詢 24 節氣
    if getattr(args, "solar_terms", False) or args.terms:
        target_year = args.year or datetime.now().year
        terms_map = get_solar_terms_for_year(target_year)
        res = {
            "year": target_year,
            "minguo_year": target_year - 1911,
            "solar_terms": terms_map
        }
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"🌾 [{target_year} 年 (民國 {res['minguo_year']} 年) 二十四節氣公曆對照表]")
            for t_name, t_date in terms_map.items():
                print(f"  • {t_name:4s}: {t_date}")
        return

    # 2. 農曆轉西曆 (反向)
    if args.to_solar:
        # 格式預期為: 113-05-05 或 2024-05-05 或 2024/05/05
        raw = args.to_solar.strip()
        pts = re.split(r"[/\-\.]", raw)
        if len(pts) >= 3:
            y = int(pts[0])
            y = y + 1911 if y < 1900 else y
            m = int(pts[1])
            d = int(pts[2])
            is_leap = getattr(args, "leap", False)
            res = lunar_to_solar(y, m, d, is_leap=is_leap)
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                fest = f"【{res['festival']}】" if res['festival'] else ""
                print(f"🌙 農曆 {y} 年 ({res['month_name']}{res['day_name']}) ➔ ☀️ 公曆: {res['solar_date']} {fest}")
            return
        else:
            sys.stderr.write("❌ Error: --to-solar format should be YYYY-MM-DD or MINGUO-MM-DD (e.g. 113-01-01)\n")
            sys.exit(1)

    # 3. 西曆轉農曆 (預設)
    raw_input = resolve_input_stream(args.query if not getattr(args, "stdin", False) else None)
    if not raw_input and getattr(args, "stdin", False):
        raw_input = sys.stdin.read().strip()
    if not raw_input and args.query:
        raw_input = args.query.strip()
    if not raw_input:
        raw_input = datetime.now().strftime("%Y-%m-%d")

    queries = [line.strip() for line in raw_input.splitlines() if line.strip()]
    results = []

    for q in queries:
        cleaned = clean_date_string(q)
        target_date = cleaned.get("date_str") if cleaned and "date_str" in cleaned else q
        try:
            dt_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
            res_lunar = solar_to_lunar(dt_obj)
            res_lunar["query"] = q
            results.append(res_lunar)
        except Exception as e:
            results.append({
                "query": q,
                "error": f"計算失敗: {e}"
            })

    if args.json:
        if len(results) == 1 and not getattr(args, "stdin", False):
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if "error" in r:
                print(f"🔴 {r['error']}")
            else:
                fest = f"🎉 節慶: {r['festival']}" if r['festival'] else ""
                term = f"🌾 節氣: {r['solar_term']}" if r['solar_term'] else ""
                extra = " | ".join(filter(None, [fest, term]))
                print(f"☀️ 公曆 {r['solar_date']} ➔ 🌙 農曆: {r['lunar_text']} (生肖: {r['sheng_xiao']}) {(' | ' + extra) if extra else ''}")


def cmd_init_calendar(args):
    """Import and initialize official calendar table from open-data CSV."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    count = init_calendar_from_csv(conn, CALENDAR_CSV_PATH)
    conn.close()

    res = {
        "status": "SUCCESS",
        "csv_path": CALENDAR_CSV_PATH,
        "imported_records": count,
        "db_path": DB_PATH
    }
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"✅ 成功將 {count} 筆政府行政機關辦公日曆資料匯入至: {DB_PATH}")


def cmd_status(args):
    """Report G40 submodule status, calendar coverage and record counts."""
    total_days = 0
    min_date = ""
    max_date = ""
    total_working = 0
    total_holidays = 0
    db_exists = os.path.exists(DB_PATH)

    if db_exists:
        try:
            conn = sqlite3.connect(DB_PATH)
            ensure_calendar_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), MIN(date_str), MAX(date_str) FROM calendar_registry;")
            row = cursor.fetchone()
            total_days = row[0]
            min_date = row[1] or ""
            max_date = row[2] or ""

            cursor.execute("SELECT COUNT(*) FROM calendar_registry WHERE is_working_day = 1;")
            total_working = cursor.fetchone()[0]
            total_holidays = total_days - total_working
            conn.close()
        except Exception:
            pass

    status_data = {
        "submodule": "g40_temporal_indexer",
        "spec_version": __cli_spec_version__,
        "db_path": DB_PATH,
        "db_exists": db_exists,
        "total_calendar_records": total_days,
        "coverage_start": min_date,
        "coverage_end": max_date,
        "working_days_count": total_working,
        "holidays_count": total_holidays,
        "csv_source": CALENDAR_CSV_PATH,
        "csv_source_exists": os.path.exists(CALENDAR_CSV_PATH),
        "status": "HEALTHY" if total_days > 0 else "UNINITIALIZED"
    }

    if args.json:
        print(json.dumps(status_data, ensure_ascii=False, indent=2))
    else:
        print(f"🕒 [G40 Temporal Indexer] Status: {status_data['status']}")
        print(f"  • Spec Version: {status_data['spec_version']}")
        print(f"  • 日曆表總筆數: {total_days} (涵蓋: {min_date} ~ {max_date})")
        print(f"  • 工作日: {total_working} 天 | 放假/例假日: {total_holidays} 天")


def cmd_schema(args):
    """Output canonical JSON schema for g40_cli (CGS v2.4)."""
    schema_dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "G40TemporalIndexerSchema",
        "description": "Schema definition for g40_cli.py (CGS v2.4)",
        "version": "2.4",
        "subcommands": {
            "clean-date": {
                "description": "Normalize heterogeneous Taiwan/Minguo date strings to standard ISO-8601",
                "arguments": ["query", "--stdin", "-j/--json", "-q/--quiet"]
            },
            "check": {
                "description": "Check whether date is working day or holiday according to government calendar",
                "arguments": ["query", "--stdin", "-j/--json", "-q/--quiet"]
            },
            "range": {
                "description": "Expand date range and count working days vs holidays",
                "arguments": ["start_date", "end_date", "--working-days-only", "-j/--json"]
            },
            "bucket": {
                "description": "Expand fiscal year or quarter into temporal bucket",
                "arguments": ["bucket", "-j/--json"]
            },
            "lunar": {
                "description": "Convert between Solar and Lunar calendar, or query 24 Solar Terms",
                "arguments": ["query", "--to-solar", "--leap", "--solar-terms", "--year", "--stdin", "-j/--json", "-q/--quiet"]
            },
            "init-calendar": {
                "description": "Initialize and populate calendar_registry table from open data CSV",
                "arguments": ["-j/--json"]
            },
            "status": {
                "description": "Report G40 calendar status and coverage",
                "arguments": ["-j/--json"]
            }
        }
    }
    print(json.dumps(schema_dict, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="G40 全政府時間、辦公日曆與時序維度器 CLI 工具 (CGS v2.4)")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-j", "--json", action="store_true", help="Output results in JSON format")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential warnings/logs")
    parent_parser.add_argument("-i", "--stdin", action="store_true", help="Read input from standard input stream (UNIX Pipe)")

    # clean-date
    p_clean = subparsers.add_parser("clean-date", parents=[parent_parser], help="Normalize heterogeneous date string to ISO-8601")
    p_clean.add_argument("query", nargs="?", default=None, help="Date string to normalize (e.g. 113/08/22, 113Q3, 民國113年8月22日)")
    p_clean.set_defaults(func=cmd_clean_date)

    # check
    p_check = subparsers.add_parser("check", parents=[parent_parser], help="Check working day status and holiday attributes")
    p_check.add_argument("query", nargs="?", default=None, help="Target date to check (YYYY-MM-DD or Minguo format)")
    p_check.set_defaults(func=cmd_check)

    # range
    p_range = subparsers.add_parser("range", parents=[parent_parser], help="Expand date range and count working days")
    p_range.add_argument("start_date", help="Start date (e.g. 2024-01-01 or 113/01/01)")
    p_range.add_argument("end_date", help="End date (e.g. 2024-01-31 or 113/01/31)")
    p_range.add_argument("--working-days-only", action="store_true", help="Filter and output only working days")
    p_range.set_defaults(func=cmd_range)

    # bucket
    p_bucket = subparsers.add_parser("bucket", parents=[parent_parser], help="Expand fiscal year or quarter into temporal bucket")
    p_bucket.add_argument("bucket", help="Fiscal year or quarter (e.g. 113, 113年度, 2024Q3)")
    p_bucket.set_defaults(func=cmd_bucket)

    # lunar
    p_lunar = subparsers.add_parser("lunar", parents=[parent_parser], help="Convert between Solar and Lunar calendar, or query 24 Solar Terms")
    p_lunar.add_argument("query", nargs="?", default=None, help="Solar date (YYYY-MM-DD) to convert to Lunar")
    p_lunar.add_argument("--to-solar", default=None, help="Convert Lunar date to Solar (format: YYYY-MM-DD or MINGUO-MM-DD, e.g. 113-01-01)")
    p_lunar.add_argument("--leap", action="store_true", help="Flag if the lunar month is a leap month (閏月)")
    p_lunar.add_argument("--solar-terms", "--terms", dest="terms", action="store_true", help="List all 24 Solar Terms for specified year")
    p_lunar.add_argument("--year", type=int, default=None, help="Target year for solar terms (default: current year)")
    p_lunar.set_defaults(func=cmd_lunar)

    # init-calendar
    p_init = subparsers.add_parser("init-calendar", parents=[parent_parser], help="Initialize calendar_registry from open data CSV")
    p_init.set_defaults(func=cmd_init_calendar)

    # schema
    p_sch = subparsers.add_parser("schema", parents=[parent_parser], help="Output CGS v2.4 JSON schema")
    p_sch.set_defaults(func=cmd_schema)

    # status
    p_stat = subparsers.add_parser("status", parents=[parent_parser], help="Report G40 calendar status")
    p_stat.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)


if __name__ == "__main__":
    main()
