#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 經濟部水利署 (WRA) 水位站與雨量站標準化採集、清洗與重建工具
description: 解析水利署開放資料 CSV (河川水位測站站況 ID:22227、雨量站基本資料 ID:32729)，支援別名/同音異字自動校正、三級圳路降級關聯母流域、剔除缺損測試站、TWD97->WGS84 投影轉換，並具備自動自開放資料平台下載最新資料集 (--download-latest) 與全量重建 (--reset)。
category: ingestion
dependencies: sqlite3, pyproj, csv, json, open_data.downloader
"""

import sys
import csv
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import pyproj

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "universal_keys.sqlite"

# 引入專案開放資料模組
for p in [str(WORKSPACE_ROOT), str(WORKSPACE_ROOT / "scripts")]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from open_data.downloader import download_dataset
except ImportError:
    download_dataset = None

# 指名水利署官方開放資料集識別碼 (SSOT Dataset IDs)
DATASET_ID_WATER_LEVEL = "22227"     # 河川水位測站站況
DATASET_ID_RAINFALL_META = "32729"   # 水利署所屬雨量站基本資料

WATER_STATIONS_DIR = WORKSPACE_ROOT / "data" / "open-data" / "wra_water_stations"
RAINFALL_STATIONS_DIR = WORKSPACE_ROOT / "data" / "open-data" / "wra_rainfall_meta"

WATER_STATIONS_CSV = WATER_STATIONS_DIR / "河川水位測站站況_1.csv"
RAINFALL_STATIONS_CSV = RAINFALL_STATIONS_DIR / "水利署所屬雨量站基本資料_1.csv"

# 1. 同音異字與別名精確對照字典 (Alias Map)
RIVER_ALIAS_MAP = {
    "峨嵋溪": "峨眉溪",
    "客雅溪": "客雅溪排水",
    "典寶溪": "典寶溪排水",
    "福興溪": "福興溪排水",
    "鹽港溪": "鹽港溪排水",
    "德盛溪": "德盛溪排水",
    "洋子溪": "洋仔厝溪",
    "宜蘭河(宜蘭溪)": "宜蘭河",
    "湖子內排水(在來排水)": "八掌溪",
    "龍鳳溪": "花蓮溪",
    "生毛樹溪": "濁水溪",
    "五虎寮溪": "八掌溪",
    "鹿滿溪": "朴子溪",
    "到孔山溪": "北港溪",
    "沙山溪": "二林溪",
    "莿仔溪": "濁水溪",
    "古夏溪": "高屏溪",
    "士文溪": "阿士文溪",
    "馬鞍溪": "花蓮溪",
    "哆囉固溪": "大安溪",
    "桂竹林河": "後龍溪"
}


def ensure_latest_datasets():
    """若本機檔案不存在，或使用者要求下載，自動調用 open_data 下載指名資料集"""
    if not download_dataset:
        print("[-] 警告: 無法匯入 open_data.downloader，跳過自動下載")
        return

    WATER_STATIONS_DIR.mkdir(parents=True, exist_ok=True)
    RAINFALL_STATIONS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[*] 正在檢查/下載水利署水位站資料集 (ID: {DATASET_ID_WATER_LEVEL})...")
    download_dataset(DATASET_ID_WATER_LEVEL, output_dir=WATER_STATIONS_DIR)

    print(f"[*] 正在檢查/下載水利署雨量站資料集 (ID: {DATASET_ID_RAINFALL_META})...")
    download_dataset(DATASET_ID_RAINFALL_META, output_dir=RAINFALL_STATIONS_DIR)


def build_river_lookup(conn: sqlite3.Connection) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """建立河川名稱與程式碼的雙向字典"""
    cur = conn.cursor()
    # 優先排序：官方代碼 (is_civilian=0) 後處理，確保覆蓋民間代碼成為權威對齊目標
    cur.execute("SELECT river_code, river_name, basin_name, stream_order, is_civilian FROM river_registry ORDER BY is_civilian DESC;")
    rows = cur.fetchall()
    
    name_to_code = {}
    basin_4to6 = {}
    basin_name_to_code = {}
    
    for code, name, basin, order, is_civ in rows:
        name_to_code[name] = code
        if basin:
            basin_name_to_code[basin] = code[:4] + "00" if len(code) >= 6 else code
        if order == 1:
            basin_4to6[code[:4]] = code
            basin_4to6[code] = code

    # 注入 Alias (含 WRA-Civ 正式整合之三峽河 -> 三峽溪 114011)
    name_to_code["三峽河"] = "114011"
    for alias, standard in RIVER_ALIAS_MAP.items():
        if standard in name_to_code:
            name_to_code[alias] = name_to_code[standard]

    return name_to_code, basin_4to6, basin_name_to_code


def ingest_wra_water_stations(conn: sqlite3.Connection, transformer: pyproj.Transformer, name_to_code: Dict[str, str], basin_4to6: Dict[str, str]) -> Tuple[int, int]:
    """採集、清洗並正規化水利署河川水位測站 (857 站)"""
    if not WATER_STATIONS_CSV.exists():
        print(f"[-] 找不到水位站檔案: {WATER_STATIONS_CSV}，嘗試自動下載...")
        ensure_latest_datasets()

    cur = conn.cursor()
    inserted = 0
    skipped_corrupted = 0

    with open(WATER_STATIONS_CSV, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_id = row.get("observatoryidentifier", "").strip()
            station_id = row.get("basinidentifier", "").strip() or raw_id
            if not station_id:
                continue

            station_name = row.get("observatoryname", "").strip()
            rname = row.get("rivername", "").strip()

            # 2. 嚴格過濾：編碼缺損字元 / 測試站 (例如含有 ? 或 ?? 或 0000 或 站名為空)
            if "?" in station_name or "?" in rname or rname == "0000" or not station_name:
                skipped_corrupted += 1
                continue

            # 座標轉換 (TWD97 TM2 -> WGS84)
            twd97_str = row.get("locationbytwd97_xy", "").strip()
            lon, lat = None, None
            if twd97_str:
                parts = twd97_str.split()
                if len(parts) == 2:
                    try:
                        x, y = float(parts[0]), float(parts[1])
                        lon, lat = transformer.transform(x, y)
                        lon, lat = round(lon, 6), round(lat, 6)
                    except Exception:
                        pass

            # Tier 1 官方文本匹配與 Alias
            river_code = name_to_code.get(rname)
            
            aff_basin = row.get("affiliatedbasin", "").strip()
            basin_code = basin_4to6.get(aff_basin) or (basin_4to6.get(aff_basin[:4]) if len(aff_basin) >= 4 else None)
            
            # 若仍無 basin_code，嘗試由 station_id 前 4 碼推導母流域 (例如 1140H075 -> 114000)
            if not basin_code and len(station_id) >= 4 and station_id[:4].isdigit():
                prefix4 = station_id[:4]
                basin_code = basin_4to6.get(prefix4)

            # 水位站身在何河判定
            if river_code:
                alignment_status = "VERIFIED"
                confidence = 1.0
                reason = None
            elif basin_code and any(k in rname for k in ["圳", "排", "幹線", "暗渠", "溝"]):
                # 3. 三級灌溉圳道 / 區排箱涵：標註為都市下水道/區排，降級關聯母流域
                alignment_status = "WATERSHED_BASIN"
                confidence = 0.80
                reason = "URBAN_DRAINAGE_NO_RIVER"
            else:
                alignment_status = "UNASSIGNED"
                confidence = 0.0
                reason = "MISSING_CIVILIAN_SHP" if rname else "NO_RIVER_NAME"

            attr = {
                "spec_version": "0.3.0",
                "authority_level": "CENTRAL",
                "relation_type": "LOCATED_ON_RIVER" if river_code else "DRAINS_INTO_BASIN",
                "confidence_score": confidence,
                "unassigned_reason": reason,
                "raw_observatory_id": raw_id,
                "raw_river_name": rname,
                "raw_basin_id": aff_basin,
                "observation_status": row.get("observationstatus", "").strip(),
                "history_trail": [
                    {
                        "timestamp": "2026-09-13T08:05:00+08:00",
                        "action": "TIER1_TEXT_EXTRACTION" if river_code else ("CANAL_BASIN_DEGRADE" if alignment_status == "WATERSHED_BASIN" else "INGEST_UNASSIGNED"),
                        "operator": "wra_stations_cleaner",
                        "notes": f"水利署水位站正規化清洗，原始河川: {rname or '無'} (歸位: {river_code or basin_code or '待對齊'})"
                    }
                ]
            }

            admin_code = row.get("areacode", "").strip() or None

            cur.execute("""
            INSERT OR REPLACE INTO station_registry (
                station_id, station_name, station_type, agency_name, river_code, basin_code,
                admin_code, latitude, longitude, alignment_status, attributes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                station_id, station_name, "WATER_LEVEL", "經濟部水利署", river_code, basin_code,
                admin_code, lat, lon, alignment_status, json.dumps(attr, ensure_ascii=False)
            ))
            inserted += 1

    return inserted, skipped_corrupted


def ingest_wra_rainfall_stations(conn: sqlite3.Connection, transformer: pyproj.Transformer, basin_4to6: Dict[str, str]) -> int:
    """採集並正規化水利署所屬雨量站 (243 站)"""
    if not RAINFALL_STATIONS_CSV.exists():
        print(f"[-] 找不到雨量站檔案: {RAINFALL_STATIONS_CSV}，嘗試自動下載...")
        ensure_latest_datasets()

    cur = conn.cursor()
    inserted = 0

    with open(RAINFALL_STATIONS_CSV, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_id = row.get("observatoryidentifier", "").strip()
            station_id = row.get("stationidentifier", "").strip() or raw_id
            if not station_id:
                continue

            station_name = row.get("observatoryname", "").strip()
            if not station_name or "?" in station_name:
                continue

            # 座標轉換 (x_3826, y_3826 -> WGS84)
            x_str = row.get("x_3826", "").strip()
            y_str = row.get("y_3826", "").strip()
            lon, lat = None, None
            if x_str and y_str:
                try:
                    x, y = float(x_str), float(y_str)
                    lon, lat = transformer.transform(x, y)
                    lon, lat = round(lon, 6), round(lat, 6)
                except Exception:
                    pass

            b_id = row.get("basinidentifier", "").strip()
            basin_code = basin_4to6.get(b_id) or (basin_4to6.get(b_id[:4]) if len(b_id) >= 4 else None)

            # 梅子雨量站 (wr1206) 為大甲溪流域 (142000)
            if not basin_code and station_name == "梅子":
                basin_code = "142000"

            if basin_code:
                alignment_status = "WATERSHED_BASIN"
                confidence = 0.85
                reason = None
            else:
                alignment_status = "UNASSIGNED"
                confidence = 0.0
                reason = "UNMATCHED_BASIN"

            attr = {
                "spec_version": "0.3.0",
                "authority_level": "CENTRAL",
                "relation_type": "DRAINS_INTO_BASIN",
                "confidence_score": confidence,
                "unassigned_reason": reason,
                "raw_observatory_id": raw_id,
                "raw_basin_id": b_id,
                "disuse_status": row.get("disusestatus", "").strip(),
                "history_trail": [
                    {
                        "timestamp": "2026-09-13T08:05:00+08:00",
                        "action": "TIER1_BASIN_EXTRACTION",
                        "operator": "wra_stations_cleaner",
                        "notes": f"水利署雨量站正規化清洗，流域程式碼: {b_id} (歸位: {basin_code or '待對齊'})"
                    }
                ]
            }

            admin_code = row.get("areacode", "").strip() or None

            cur.execute("""
            INSERT OR REPLACE INTO station_registry (
                station_id, station_name, station_type, agency_name, river_code, basin_code,
                admin_code, latitude, longitude, alignment_status, attributes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                station_id, station_name, "RAINFALL", "經濟部水利署", None, basin_code,
                admin_code, lat, lon, alignment_status, json.dumps(attr, ensure_ascii=False)
            ))
            inserted += 1

    return inserted


def main():
    parser = argparse.ArgumentParser(description="水利署測站採集、清洗與重建工具")
    parser.add_argument("--reset", action="store_true", help="完全清空既有測站並由 CSV 重新建立")
    parser.add_argument("--download-latest", action="store_true", help="強制先從開放資料平台重新下載最新 CSV")
    args = parser.parse_args()

    if args.download_latest or not WATER_STATIONS_CSV.exists() or not RAINFALL_STATIONS_CSV.exists():
        ensure_latest_datasets()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if args.reset:
        print("[!] 收到 --reset 參數，清空 station_registry 進行全新重建...")
        cur.execute("DELETE FROM station_registry;")
        conn.commit()

    print("[*] 開始執行水利署水位與雨量測站正規化清洗與匯入...")
    transformer = pyproj.Transformer.from_crs("epsg:3826", "epsg:4326", always_xy=True)

    name_to_code, basin_4to6, _ = build_river_lookup(conn)

    water_count, skipped_corrupted = ingest_wra_water_stations(conn, transformer, name_to_code, basin_4to6)
    rain_count = ingest_wra_rainfall_stations(conn, transformer, basin_4to6)

    # 確保種子測站（包含 CWA 氣象署種子測站 C0A980、C0AH00 與代表性水位站）維持存在
    seed_stations = [
        ("C0A980", "芎林雨量站", "RAINFALL", "中央氣象署", "130000-C04", "130000", "10004080", 24.7744, 121.0772, "VERIFIED", '{"spec_version":"0.3.0","authority_level":"CENTRAL","relation_type":"DRAINS_INTO_BASIN","confidence_score":1.0,"unassigned_reason":null}'),
        ("1300H01", "竹東水位站", "WATER_LEVEL", "經濟部水利署", "130000", "130000", "10004030", 24.7333, 121.0890, "VERIFIED", '{"spec_version":"0.3.0","authority_level":"CENTRAL","relation_type":"LOCATED_ON_RIVER","confidence_score":1.0,"unassigned_reason":null}'),
        ("1140H02", "新店溪秀朗橋水位站", "WATER_LEVEL", "經濟部水利署", "114020", "114000", "65000030", 24.9961, 121.5333, "VERIFIED", '{"spec_version":"0.3.0","authority_level":"CENTRAL","relation_type":"LOCATED_ON_RIVER","confidence_score":1.0,"unassigned_reason":null}'),
        ("C0AH00", "烏來雨量站", "RAINFALL", "中央氣象署", "114021", "114000", "65000290", 24.8653, 121.5503, "VERIFIED", '{"spec_version":"0.3.0","authority_level":"CENTRAL","relation_type":"DRAINS_INTO_BASIN","confidence_score":1.0,"unassigned_reason":null}'),
        ("1510H01", "濁水溪集集水位站", "WATER_LEVEL", "經濟部水利署", "151000", "151000", "10008130", 23.8242, 120.7853, "VERIFIED", '{"spec_version":"0.3.0","authority_level":"CENTRAL","relation_type":"LOCATED_ON_RIVER","confidence_score":1.0,"unassigned_reason":null}')
    ]
    cur.executemany("""
    INSERT OR REPLACE INTO station_registry (
        station_id, station_name, station_type, agency_name, river_code, basin_code, admin_code,
        latitude, longitude, alignment_status, attributes_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, seed_stations)

    conn.commit()

    # 統計現況
    cur.execute("SELECT station_type, alignment_status, count(*) FROM station_registry GROUP BY station_type, alignment_status;")
    stats = cur.fetchall()

    conn.close()

    print(f"\n[+] 處理完成！")
    print(f"  • 水位站有效匯入: {water_count} 筆 (剔除缺損/測試站: {skipped_corrupted} 筆)")
    print(f"  • 雨量站有效匯入: {rain_count} 筆")
    print("\n📊 目前 station_registry 測站統計:")
    for st_type, status, count in stats:
        print(f"  • {st_type:<12} | {status:<18} : {count:>4} 筆")


if __name__ == "__main__":
    main()
