import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "ontology" / "master_agencies.sqlite"

DDL_SQL = """
-- 1. 機關主檔 (Agencies)
CREATE TABLE IF NOT EXISTS master_agencies (
    agency_oid VARCHAR(128) PRIMARY KEY,
    org_code VARCHAR(32),
    agency_name VARCHAR(128) NOT NULL,
    parent_oid VARCHAR(128),
    level_type VARCHAR(16),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(parent_oid) REFERENCES master_agencies(agency_oid)
);

-- 2. 處務規程法定職掌 (Mandates)
CREATE TABLE IF NOT EXISTS agency_mandates (
    mandate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agency_oid VARCHAR(128) NOT NULL,
    unit_name VARCHAR(128) NOT NULL,
    law_article VARCHAR(32),
    mandate_text TEXT NOT NULL,
    keywords_json TEXT,
    FOREIGN KEY(agency_oid) REFERENCES master_agencies(agency_oid)
);

-- 3. 發布機關別名對照表 (Publisher Aliases)
CREATE TABLE IF NOT EXISTS publisher_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_publisher_name VARCHAR(128) UNIQUE NOT NULL,
    mapped_agency_oid VARCHAR(128) NOT NULL,
    confidence_score FLOAT DEFAULT 1.0,
    FOREIGN KEY(mapped_agency_oid) REFERENCES master_agencies(agency_oid)
);
"""

def init_database(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.executescript(DDL_SQL)
    conn.commit()
    conn.close()
    print(f"✅ 成功初始化底座 DB 結構: {db_path}")

if __name__ == "__main__":
    init_database()
