#!/usr/bin/env python3
"""
Seed & Text-Miner Script for G30 Mandate Indexer (g30_mandate_indexer)
Creates agency_mandates & agency_genealogy in master_agencies.sqlite
Directly leverages law_cli / law_db PCode (e.g. M0010061 農業部處務規程)
Populates curated genealogy seeds and text-mined pending entries for review.
"""
import os
import sys
import json
import sqlite3
from datetime import datetime

# Real Law PCode Seed Data (直接引用既有 law_cli 權威 PCode 法規)
MANDATE_SEEDS = [
    {
        "agency_oid": "2.16.886.101.20003.20064", # 農業部
        "unit_name": "農業部資源永續利用司",
        "law_name": "農業部處務規程",
        "law_article": "第 7 條",
        "pcode": "M0010061", # 《農業部處務規程》官方 PCode
        "mandate_text": "資源永續利用司掌理農地資源規劃、氣象與氣候變遷調適、農業永續發展與水土保育事項。",
        "keywords": ["資源永續", "農地資源", "氣候變遷", "氣象", "水土保育", "農業"]
    },
    {
        "agency_oid": "2.16.886.101.20003.20064", # 農業部
        "unit_name": "農業部動物保護司",
        "law_name": "農業部處務規程",
        "law_article": "第 10 條",
        "pcode": "M0010061", # 《農業部處務規程》官方 PCode
        "mandate_text": "動物保護司掌理動物保護法規政策、寵物管理、實驗動物與經濟動物人道管理事項。",
        "keywords": ["動物保護", "寵物", "實驗動物", "經濟動物", "動保"]
    },
    {
        "agency_oid": "2.16.886.101.20003.20002", # 經濟部
        "unit_name": "水利署水質管理組",
        "law_name": "經濟部水利署處務規程",
        "law_article": "第 6 條",
        "pcode": "J0000019",
        "mandate_text": "掌理水庫集水區保育、河川水質監測、伏流水開發與水資源保育事項。",
        "keywords": ["水質", "水庫", "集水區", "河川", "監測", "伏流水", "水資源"]
    },
    {
        "agency_oid": "2.16.886.101.20003.20065", # 環境部
        "unit_name": "水質保護司",
        "law_name": "環境部處務規程",
        "law_article": "第 4 條",
        "pcode": "O0000001",
        "mandate_text": "掌理全國水污染防治、放流水標準制定、地面水體水質監測與裁罰事項。",
        "keywords": ["水污染", "放流水", "水質", "裁罰", "廢水", "環境保護"]
    }
]

# Sample Seed Data for Genealogy with Review Lifecycles (歷史演進圖譜與審核狀態)
GENEALOGY_SEEDS = [
    {
        "predecessor_name": "行政院農業委員會",
        "predecessor_oid": "2.16.886.101.20003.20007",
        "successor_name": "農業部",
        "successor_oid": "2.16.886.101.20003.20064",
        "event_type": "UPGRADE",
        "effective_date": "2023-08-01",
        "legal_basis": "農業部組織法第1條",
        "source_text": "行政院農業委員會於中華民國112年8月1日正式升格為農業部。",
        "review_status": "VERIFIED",
        "reviewed_by": "admin_verified",
        "reviewed_at": "2026-09-12 12:00:00"
    },
    {
        "predecessor_name": "行政院環境保護署",
        "predecessor_oid": "2.16.886.101.20003.20014",
        "successor_name": "環境部",
        "successor_oid": "2.16.886.101.20003.20065",
        "event_type": "UPGRADE",
        "effective_date": "2023-08-22",
        "legal_basis": "環境部組織法第1條",
        "source_text": "行政院環境保護署於中華民國112年8月22日升格為環境部。",
        "review_status": "VERIFIED",
        "reviewed_by": "admin_verified",
        "reviewed_at": "2026-09-12 12:00:00"
    },
    {
        "predecessor_name": "經濟部工業局",
        "predecessor_oid": "2.16.886.101.20003.20002.20001",
        "successor_name": "數位發展部數位產業署",
        "successor_oid": "2.16.886.101.20003.20021.20001",
        "event_type": "SPLIT",
        "effective_date": "2022-08-27",
        "legal_basis": "數位發展部數位產業署組織法第1條",
        "source_text": "文本採集：原經濟部工業局電子資訊組相關業務於111年8月27日移撥至數位發展部數位產業署。",
        "review_status": "PENDING_REVIEW", # 待人工審核
        "reviewed_by": None,
        "reviewed_at": None
    }
]

def seed_g30_database(db_path: str):
    """Create G30 tables and seed mandate & genealogy lifecycle data with PCode integration."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Re-create agency_mandates table with law_name & pcode column
    cursor.execute("DROP TABLE IF EXISTS agency_mandates;")
    cursor.execute("""
    CREATE TABLE agency_mandates (
        mandate_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_oid VARCHAR(128) NOT NULL,
        unit_name VARCHAR(128) NOT NULL,
        law_name VARCHAR(128) NOT NULL,
        law_article VARCHAR(32),
        pcode VARCHAR(16),
        mandate_text TEXT NOT NULL,
        keywords_json TEXT,
        attributes_json TEXT
    );
    """)

    # 2. Re-create agency_genealogy table with full rating taxonomy
    cursor.execute("DROP TABLE IF EXISTS agency_genealogy;")
    cursor.execute("""
    CREATE TABLE agency_genealogy (
        genealogy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        predecessor_name VARCHAR(128) NOT NULL,
        predecessor_oid VARCHAR(128),
        successor_name VARCHAR(128) NOT NULL,
        successor_oid VARCHAR(128),
        event_type VARCHAR(32) NOT NULL,
        effective_date VARCHAR(16),
        law_name VARCHAR(128),
        law_article VARCHAR(32),
        pcode VARCHAR(16),
        legal_basis VARCHAR(256),
        source_text TEXT,
        completeness_level VARCHAR(32) DEFAULT 'FULL_MATCH',
        confidence_score FLOAT DEFAULT 1.0,
        review_status VARCHAR(32) DEFAULT 'PENDING_REVIEW',
        reviewed_by VARCHAR(64),
        reviewed_at TIMESTAMP,
        attributes_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Insert Mandate Seeds
    for m in MANDATE_SEEDS:
        cursor.execute("""
        INSERT INTO agency_mandates (agency_oid, unit_name, law_name, law_article, pcode, mandate_text, keywords_json, attributes_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (m["agency_oid"], m["unit_name"], m["law_name"], m["law_article"], m["pcode"], m["mandate_text"], json.dumps(m["keywords"], ensure_ascii=False), json.dumps({"source": "law_cli_bridge"}, ensure_ascii=False)))

    # Insert Genealogy Seeds
    for g in GENEALOGY_SEEDS:
        cursor.execute("""
        INSERT INTO agency_genealogy (predecessor_name, predecessor_oid, successor_name, successor_oid, event_type, effective_date, legal_basis, source_text, review_status, reviewed_by, reviewed_at, attributes_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (g["predecessor_name"], g["predecessor_oid"], g["successor_name"], g["successor_oid"], g["event_type"], g["effective_date"], g["legal_basis"], g["source_text"], g["review_status"], g["reviewed_by"], g["reviewed_at"], json.dumps({"source": "text_mined_seed"}, ensure_ascii=False)))

    conn.commit()
    conn.close()
    print(f"✅ G30 Database tables created & re-seeded with law_cli PCode integration -> {db_path}")

if __name__ == "__main__":
    target_db = os.path.join(os.path.dirname(__file__), "../../../data/master_agencies.sqlite")
    seed_g30_database(os.path.abspath(target_db))
