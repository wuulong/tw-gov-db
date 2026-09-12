#!/usr/bin/env python3
"""
Seed Data Script for G20 Spatial Indexer (g20_spatial_indexer)
Populates admin_codes and zipcode_registry into universal_keys.sqlite
"""
import os
import sys
import json
import sqlite3

# Seed data for Taiwan County/Town Zipcodes & Admin Codes (Sample subset for bootstrapping)
TAIWAN_ZIPCODE_SEEDS = [
    {"zipcode": "100", "county": "臺北市", "town": "中正區", "admin_code": "63000010"},
    {"zipcode": "103", "county": "臺北市", "town": "大同區", "admin_code": "63000020"},
    {"zipcode": "104", "county": "臺北市", "town": "中山區", "admin_code": "63000030"},
    {"zipcode": "105", "county": "臺北市", "town": "松山區", "admin_code": "63000040"},
    {"zipcode": "106", "county": "臺北市", "town": "大安區", "admin_code": "63000050"},
    {"zipcode": "110", "county": "臺北市", "town": "信義區", "admin_code": "63000060"},
    {"zipcode": "300", "county": "新竹市", "town": "東區", "admin_code": "10018010"},
    {"zipcode": "302", "county": "新竹縣", "town": "竹北市", "admin_code": "10004010"},
    {"zipcode": "303", "county": "新竹縣", "town": "湖口鄉", "admin_code": "10004020"},
    {"zipcode": "305", "county": "新竹縣", "town": "新埔鎮", "admin_code": "10004030"},
    {"zipcode": "310", "county": "新竹縣", "town": "竹東鎮", "admin_code": "10004040"},
    {"zipcode": "400", "county": "臺中市", "town": "中區", "admin_code": "66000010"},
    {"zipcode": "700", "county": "臺南市", "town": "中西區", "admin_code": "67000010"},
    {"zipcode": "800", "county": "高雄市", "town": "新興區", "admin_code": "64000010"},
    {"zipcode": "950", "county": "臺東縣", "town": "臺東市", "admin_code": "10014010"},
    {"zipcode": "970", "county": "花蓮縣", "town": "花蓮市", "admin_code": "10015010"},
]

def seed_g20_database(db_path: str):
    """Ensure database schema exists and populate G20 baseline tables."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create admin_codes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_codes (
        admin_code TEXT PRIMARY KEY,
        county_name TEXT NOT NULL,
        town_name TEXT NOT NULL,
        attributes_json TEXT
    );
    """)

    # Create zipcode_registry table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zipcode_registry (
        zipcode TEXT PRIMARY KEY,
        county_name TEXT NOT NULL,
        town_name TEXT NOT NULL,
        admin_code TEXT NOT NULL,
        attributes_json TEXT
    );
    """)

    # Insert seeds
    for item in TAIWAN_ZIPCODE_SEEDS:
        attr = json.dumps({"source": "official_seed", "status": "active"}, ensure_ascii=False)
        cursor.execute("""
        INSERT OR REPLACE INTO admin_codes (admin_code, county_name, town_name, attributes_json)
        VALUES (?, ?, ?, ?);
        """, (item["admin_code"], item["county"], item["town"], attr))

        cursor.execute("""
        INSERT OR REPLACE INTO zipcode_registry (zipcode, county_name, town_name, admin_code, attributes_json)
        VALUES (?, ?, ?, ?, ?);
        """, (item["zipcode"], item["county"], item["town"], item["admin_code"], attr))

    conn.commit()
    conn.close()
    print(f"✅ G20 Baseline Seed populated successfully: {len(TAIWAN_ZIPCODE_SEEDS)} records -> {db_path}")

if __name__ == "__main__":
    target_db = os.path.join(os.path.dirname(__file__), "../../../data/universal_keys.sqlite")
    seed_g20_database(os.path.abspath(target_db))
