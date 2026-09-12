#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: G60 法人企業與農漁會資料表初始化與種子數據灌入工具
description: 建立 universal_keys.sqlite 中的 corporate_registry 與 npo_registry 表，並注入代表性種子企業與全台各級農漁會主檔。
category: maintenance
dependencies: sqlite3
"""

import sys
import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1] / "src" / "modules" / "g60_corporate_indexer"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from npo_resolver import NpoResolver

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "universal_keys.sqlite"


def init_g60_tables(db_path: Path = DEFAULT_DB_PATH):
    print(f"[*] 正在初始化 G60 資料表至: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 1. 建立 corporate_registry (Pass-Through Cache)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS corporate_registry (
        tax_id VARCHAR(8) PRIMARY KEY,
        company_name VARCHAR(256) NOT NULL,
        registered_address VARCHAR(256),
        admin_code VARCHAR(8),
        status VARCHAR(32) DEFAULT 'ACTIVE',
        source VARCHAR(32) DEFAULT 'SEED',
        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_corp_name ON corporate_registry(company_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_corp_admin ON corporate_registry(admin_code);")

    # 2. 建立 npo_registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS npo_registry (
        npo_id VARCHAR(32) PRIMARY KEY,
        npo_name VARCHAR(256) NOT NULL,
        short_name VARCHAR(64),
        npo_type VARCHAR(32) NOT NULL,
        level VARCHAR(16),
        city_name VARCHAR(32),
        admin_code VARCHAR(8),
        address VARCHAR(256),
        parent_id VARCHAR(32),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_npo_name ON npo_registry(npo_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_npo_type ON npo_registry(npo_type);")

    # 3. 注入 corporate_registry 種子企業
    seed_companies = [
        ("04595257", "台灣積體電路製造股份有限公司", "新竹市東區新竹科學園區力行六路8號", "10018010", "ACTIVE", "SEED"),
        ("96979933", "中華電信股份有限公司", "台北市中正區信義路一段21之3號", "63000050", "ACTIVE", "SEED"),
        ("04541302", "鴻海精密工業股份有限公司", "新北市土城區自由街2號", "65000130", "ACTIVE", "SEED"),
        ("16525386", "聯發科技股份有限公司", "新竹市東區新竹科學園區篤行一路1號", "10018010", "ACTIVE", "SEED"),
        ("03077008", "中國鋼鐵股份有限公司", "高雄市小港區中鋼路1號", "64000110", "ACTIVE", "SEED"),
        ("03795505", "台灣電力股份有限公司", "台北市中正區羅斯福路三段242號", "63000050", "ACTIVE", "SEED"),
        ("03704000", "台灣自來水股份有限公司", "台中市北區雙十路二段2-1號", "66000050", "ACTIVE", "SEED"),
        ("03799404", "台灣中油股份有限公司", "台北市信義區松仁路3號", "63000020", "ACTIVE", "SEED")
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO corporate_registry (tax_id, company_name, registered_address, admin_code, status, source)
    VALUES (?, ?, ?, ?, ?, ?)
    """, seed_companies)

    # 4. 注入 npo_registry 種子農漁會
    resolver = NpoResolver()
    npo_rows = []
    for k, rec in resolver.seed_registry.items():
        npo_rows.append((
            rec["npo_id"],
            rec["canonical_name"],
            k,
            rec["type"],
            rec["level"],
            rec["city"],
            rec["admin_code"],
            "",
            ""
        ))

    cursor.executemany("""
    INSERT OR REPLACE INTO npo_registry (npo_id, npo_name, short_name, npo_type, level, city_name, admin_code, address, parent_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, npo_rows)

    conn.commit()
    c_corp = cursor.execute("SELECT count(*) FROM corporate_registry;").fetchone()[0]
    c_npo = cursor.execute("SELECT count(*) FROM npo_registry;").fetchone()[0]
    conn.close()
    print(f"[+] 初始化完成！目前企業快取: {c_corp} 筆，農漁會主檔: {c_npo} 筆。")


if __name__ == "__main__":
    init_g60_tables()
