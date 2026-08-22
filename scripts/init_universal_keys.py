#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 全政府五大基石 10 大權威資料庫初始化腳本 (10 Pillars Universal Keys DB Init)
description: 初始化 universal_keys.sqlite 資料庫，包含行政區、地籍、郵遞區號、水系、測站、公司、NPO法人與辦公日曆表。
category: database
dependencies: sqlite3
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "ontology" / "universal_keys.sqlite"

def init_universal_keys_db(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 1. 基石一：權威機關主檔 (相鄰於 master_agencies)
    
    # 2. 基石二：行政區劃主檔 (admin_codes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_codes (
            admin_code VARCHAR(8) PRIMARY KEY, -- 6碼國家標準程式碼 (如 630000 臺北市)
            city_name VARCHAR(32) NOT NULL,    -- 縣市名稱
            district_name VARCHAR(32) NOT NULL, -- 鄉鎮市區名稱
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. 基石二：全國地籍段名段號表 (cadastral_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadastral_registry (
            section_code VARCHAR(16) PRIMARY KEY, -- 地籍段號程式碼
            city_name VARCHAR(32) NOT NULL,       -- 縣市名稱
            district_name VARCHAR(32) NOT NULL,   -- 鄉鎮區名稱
            section_name VARCHAR(64) NOT NULL,    -- 地籍段名 (如 成功段)
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. 基石二：郵遞區號與地址對照表 (zipcode_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zipcode_registry (
            zipcode VARCHAR(8) PRIMARY KEY,     -- 3碼/5碼/6碼郵遞區號
            city_name VARCHAR(32) NOT NULL,     -- 縣市名稱
            district_name VARCHAR(32) NOT NULL, -- 鄉鎮區名稱
            scope_description VARCHAR(256),     -- 涵蓋路段描述
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 5. 基石三：水系河川主檔 (river_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS river_registry (
            river_id VARCHAR(32) PRIMARY KEY,  -- 國家水系程式碼 (如 1300 淡水河水系)
            river_name VARCHAR(64) NOT NULL,   -- 水系名稱
            main_basin VARCHAR(64),            -- 主幹流域
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 6. 基石三：環境/氣象/水文測站主檔 (station_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS station_registry (
            station_id VARCHAR(64) PRIMARY KEY, -- 測站程式碼 (如 C0A980)
            station_name VARCHAR(128) NOT NULL, -- 測站名稱
            station_type VARCHAR(32),           -- 測站類型 (WEATHER, WATER_QUALITY, RAINFALL)
            agency_name VARCHAR(128),           -- 所屬機關 (如 中央氣象署, 環境部)
            latitude FLOAT,
            longitude FLOAT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 7. 基石四：法人與企業主檔 (corporate_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corporate_registry (
            tax_id VARCHAR(8) PRIMARY KEY,      -- 8碼統一編號
            company_name VARCHAR(256) NOT NULL, -- 公司/商號名稱
            registered_address VARCHAR(256),    -- 登記地址
            admin_code VARCHAR(8),              -- 所屬行政區程式碼
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 8. 基石四：農會與非營利組織法人主檔 (npo_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS npo_registry (
            npo_id VARCHAR(32) PRIMARY KEY,     -- 農會/NPO程式碼或統編
            npo_name VARCHAR(256) NOT NULL,     -- 農會或法人名稱
            npo_type VARCHAR(32),               -- 類型 (FARMERS_ASSOCIATION, FOUNDATION, NGO)
            city_name VARCHAR(32),              -- 所在縣市
            address VARCHAR(256),               -- 機構地址
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 9. 基石五：行政機關辦公日曆表 (calendar_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_registry (
            date_str VARCHAR(10) PRIMARY KEY,   -- 日期 (YYYY-MM-DD)
            is_holiday BOOLEAN NOT NULL,        -- 是否為放假日/例假日
            holiday_category VARCHAR(64),       -- 節日類型 (國定假日, 颱風假, 周休二日)
            description VARCHAR(256),           -- 節日說明
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 10. 基石五：受控版號對照表 (spec_version_registry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spec_version_registry (
            spec_version VARCHAR(16) PRIMARY KEY, --受控版號 (如 1.0.0)
            stage_name VARCHAR(32) NOT NULL,      -- DPRV 階段 (Proposal 0.1, ImplPlan 0.3, Alpha 0.5, Beta 0.8, Release 1.0.0)
            description VARCHAR(256),
            released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()
    print(f"✅ 成功初始化 universal_keys.sqlite 10 大權威資料庫 Schema: {db_path}")

if __name__ == "__main__":
    init_universal_keys_db()
