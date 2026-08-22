#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 通用對照資料庫開放資料全量灌入管線 (Universal Keys Ingester)
description: 自動從開放資料平台抓取水利署河川程式碼與環境部/氣象署測站資料，灌入 universal_keys.sqlite。
category: database
dependencies: requests, sqlite3
"""

import ssl
import json
import sqlite3
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "ontology" / "universal_keys.sqlite"

# 水利署：主要河川對照表 API URL
RIVER_API_URL = "https://opendata.wra.gov.tw/api/v2/1d4d24f4-4745-40e3-b51c-8c422aae4fd7?sort=_importdate%20asc&format=JSON"

# 環境部：水質測站基本資料 API URL
STATION_API_URL = "https://data.moenv.gov.tw/api/v2/wqx_p_06?api_key=af57253c-e838-46da-a1f5-12b43afd75f3&limit=1000&sort=ImportDate%20desc&format=JSON"

def fetch_json_data(url: str):
    import subprocess
    # 嘗試 Python urllib
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            if response.status == 200:
                data = response.read().decode("utf-8")
                return json.loads(data)
    except Exception as e:
        # 降級採用系統 curl 指令抓取 (突破 403)
        try:
            cmd = ["curl", "-s", "-k", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", url]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception as err:
            print(f"⚠️ 無法讀取 API: {url}, 原因: {e} / curl error: {err}")
    return None

def ingest_rivers(conn: sqlite3.Connection) -> int:
    """全量灌入經濟部水利署河川程式碼檔"""
    data = fetch_json_data(RIVER_API_URL)
    count = 0
    cursor = conn.cursor()

    if data:
        items = data if isinstance(data, list) else data.get("records", [])
        for row in items:
            # 兼容 API 欄位
            river_id = str(row.get("RiverCode") or row.get("河川程式碼") or row.get("Code") or "").strip()
            river_name = str(row.get("RiverName") or row.get("河川名稱") or row.get("Name") or "").strip()
            main_basin = str(row.get("BasinName") or row.get("流域名稱") or river_name).strip()

            if river_id and river_name:
                cursor.execute("""
                    INSERT OR REPLACE INTO river_registry (river_id, river_name, main_basin)
                    VALUES (?, ?, ?)
                """, (river_id, river_name, main_basin))
                count += 1

    conn.commit()
    print(f"✅ [1/2] 成功灌入水利署河川程式碼對照表: {count} 筆")
    return count

def ingest_stations(conn: sqlite3.Connection) -> int:
    """全量灌入環境部/氣象署測站資料"""
    data = fetch_json_data(STATION_API_URL)
    count = 0
    cursor = conn.cursor()

    if data:
        records = data.get("records", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for row in records:
            site_id = str(row.get("siteid") or row.get("測站程式碼") or "").strip()
            site_name = str(row.get("sitename") or row.get("測站名稱") or "").strip()
            lat = float(row.get("twd97lat") or row.get("latitude") or 0.0) if row.get("twd97lat") or row.get("latitude") else None
            lon = float(row.get("twd97lon") or row.get("longitude") or 0.0) if row.get("twd97lon") or row.get("longitude") else None

            if site_id and site_name:
                cursor.execute("""
                    INSERT OR REPLACE INTO station_registry (station_id, station_name, station_type, agency_name, latitude, longitude)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (site_id, site_name, "WATER_QUALITY", "環境部", lat, lon))
                count += 1

    conn.commit()
    print(f"✅ [2/2] 成功灌入環境部水質監測站資料: {count} 筆")
    return count

def run_ingestion():
    if not DB_PATH.exists():
        print(f"⚠️ 資料庫不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    ingest_rivers(conn)
    ingest_stations(conn)
    conn.close()

if __name__ == "__main__":
    run_ingestion()
