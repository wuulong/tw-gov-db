#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: WRA-Civ 全台灣水文拓樸數據同步與初始化工具 (G50)
description: 將 WRA-Civ 1,397+ 筆權威水脈 JSONL 同步匯入至 universal_keys.sqlite 之 river_registry 與 station_registry 表中，具備 SHA-256 指紋檢測與交易原子性。
category: maintenance
dependencies: sqlite3, hashlib, json
"""

import sys
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "universal_keys.sqlite"

def get_candidate_jsonl_paths() -> list[Path]:
    return [
        Path(__file__).resolve().parents[4] / "events" / "AIBooks" / "RiverExploration" / "taiwan_river_topology_registry.jsonl",
        Path(__file__).resolve().parents[3] / "events" / "AIBooks" / "RiverExploration" / "taiwan_river_topology_registry.jsonl",
        Path("/Users/wuulong/github/bmad-pa/events/AIBooks/RiverExploration/taiwan_river_topology_registry.jsonl")
    ]


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def ensure_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # 1. 增強版 river_registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS river_registry (
        river_code VARCHAR(32) PRIMARY KEY,
        river_name VARCHAR(128) NOT NULL,
        basin_name VARCHAR(64),
        parent_code VARCHAR(32),
        topology_path VARCHAR(256) NOT NULL,
        stream_order INTEGER DEFAULT 1,
        is_civilian BOOLEAN DEFAULT 0,
        primary_county VARCHAR(32),
        admin_code VARCHAR(8),
        river_office VARCHAR(64),
        confluence_lon FLOAT,
        confluence_lat FLOAT,
        status VARCHAR(16) DEFAULT 'ACTIVE',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_river_name ON river_registry(river_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_river_topo ON river_registry(topology_path);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_river_basin ON river_registry(basin_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_river_county ON river_registry(primary_county);")

    # 2. station_registry (環境水文氣象測站主檔)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS station_registry (
        station_id VARCHAR(64) PRIMARY KEY,
        station_name VARCHAR(128) NOT NULL,
        station_type VARCHAR(32),
        agency_name VARCHAR(128),
        river_code VARCHAR(32),
        admin_code VARCHAR(8),
        latitude FLOAT,
        longitude FLOAT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_station_river ON station_registry(river_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_station_type ON station_registry(station_type);")

    # 3. 同步歷史審計表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_target VARCHAR(64) NOT NULL,
        sha256 VARCHAR(64) NOT NULL,
        records_count INTEGER NOT NULL,
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()


def sync_wra_civ_rivers(
    db_path: Path = DEFAULT_DB_PATH,
    jsonl_path: Optional[Path] = None,
    force: bool = False
) -> Dict[str, Any]:
    resolved_jsonl = None
    if jsonl_path:
        resolved_jsonl = Path(jsonl_path)
    else:
        for p in get_candidate_jsonl_paths():
            if p.exists() and p.is_file():
                resolved_jsonl = p
                break

    if not resolved_jsonl or not resolved_jsonl.exists():
        print(f"[-] 錯誤: 找不到 WRA-Civ JSONL 檔案，請指定路徑。")
        return {"status": "ERROR", "message": "FILE_NOT_FOUND"}

    print(f"[*] 正在檢查 WRA-Civ 資料源: {resolved_jsonl}")
    current_hash = compute_file_sha256(resolved_jsonl)
    conn = sqlite3.connect(str(db_path))
    ensure_tables(conn)
    cursor = conn.cursor()

    if not force:
        cursor.execute("SELECT sha256 FROM sync_history WHERE sync_target = 'WRA-Civ' ORDER BY id DESC LIMIT 1;")
        last_row = cursor.fetchone()
        if last_row and last_row[0] == current_hash:
            c = cursor.execute("SELECT count(*) FROM river_registry;").fetchone()[0]
            conn.close()
            print(f"[+] 資料庫已有最新 WRA-Civ 版本 (SHA256 吻合，共 {c} 筆水脈)，略過重複同步。")
            return {"status": "UP_TO_DATE", "records_count": c, "sha256": current_hash}

    print(f"[*] 開始同步 WRA-Civ 水脈數據至 {db_path} (Hash: {current_hash[:8]}...)...")

    river_rows = []
    with open(resolved_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            data = json.loads(line_str)
            
            # 萃取各欄位
            code = data.get("river_code")
            name = data.get("river_name", "")
            basin = data.get("basin_name", "")
            parent = data.get("parent_code", "")
            topo = data.get("topology_path", "")
            order = data.get("stream_order", 1)
            is_civ = 1 if data.get("is_civilian") else 0
            
            attr = data.get("attribute_json", {})
            county = attr.get("primary_county", "")
            office = attr.get("river_office_name", "")

            plugins = data.get("plugins", {})
            gis = plugins.get("gis", {})
            lon = gis.get("confluence_lon")
            lat = gis.get("confluence_lat")

            river_rows.append((
                code, name, basin, parent, topo, order, is_civ, county, None, office, lon, lat, "ACTIVE"
            ))

    # 原子交易寫入
    cursor.execute("BEGIN TRANSACTION;")
    cursor.executemany("""
    INSERT OR REPLACE INTO river_registry (
        river_code, river_name, basin_name, parent_code, topology_path, stream_order,
        is_civilian, primary_county, admin_code, river_office, confluence_lon, confluence_lat, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, river_rows)

    # 注入種子水文測站 (若 station_registry 為空)
    cursor.execute("SELECT count(*) FROM station_registry;")
    st_count = cursor.fetchone()[0]
    if st_count == 0:
        seed_stations = [
            ("C0A980", "芎林雨量站", "RAINFALL", "中央氣象署", "130000-C04", "10004080", 24.7744, 121.0772),
            ("1300H01", "竹東水位站", "WATER_LEVEL", "經濟部水利署", "130000", "10004030", 24.7333, 121.0890),
            ("1140H02", "新店溪秀朗橋水位站", "WATER_LEVEL", "經濟部水利署", "114020", "65000030", 24.9961, 121.5333),
            ("C0AH00", "烏來雨量站", "RAINFALL", "中央氣象署", "114021", "65000290", 24.8653, 121.5503),
            ("1510H01", "濁水溪集集水位站", "WATER_LEVEL", "經濟部水利署", "151000", "10008130", 23.8242, 120.7853)
        ]
        cursor.executemany("""
        INSERT OR REPLACE INTO station_registry (station_id, station_name, station_type, agency_name, river_code, admin_code, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, seed_stations)

    # 記錄審計
    cursor.execute("""
    INSERT INTO sync_history (sync_target, sha256, records_count)
    VALUES ('WRA-Civ', ?, ?);
    """, (current_hash, len(river_rows)))

    conn.commit()
    conn.close()

    print(f"[+] 成功同步 {len(river_rows)} 筆 WRA-Civ 水脈紀錄！")
    return {
        "status": "SYNCED",
        "records_count": len(river_rows),
        "sha256": current_hash
    }


if __name__ == "__main__":
    force_sync = "--force" in sys.argv
    sync_wra_civ_rivers(force=force_sync)
