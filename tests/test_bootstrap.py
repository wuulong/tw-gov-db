import unittest
import sqlite3
from pathlib import Path

import os

env_db_dir = os.environ.get("GOV_DB_DIR")
if env_db_dir:
    TARGET_DB_PATH = Path(env_db_dir) / "master_agencies.sqlite"
elif Path("/Volumes/D2024/data/gov-db-in/db/master_agencies.sqlite").exists():
    TARGET_DB_PATH = Path("/Volumes/D2024/data/gov-db-in/db/master_agencies.sqlite")
else:
    TARGET_DB_PATH = Path(__file__).resolve().parents[1] / "ontology" / "master_agencies.sqlite"


class TestBootstrapDB(unittest.TestCase):
    def setUp(self):
        self.assertTrue(TARGET_DB_PATH.exists(), f"DB 不存在: {TARGET_DB_PATH}")
        self.conn = sqlite3.connect(str(TARGET_DB_PATH))
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def test_VAL_GOV_G00_001_db_schema_tables(self):
        """驗證底座 SQLite 實體建立與 3 張表格結構"""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in self.cursor.fetchall()]
        self.assertIn("master_agencies", tables)
        self.assertIn("agency_mandates", tables)
        self.assertIn("publisher_aliases", tables)

    def test_VAL_GOV_G00_002_oid_count(self):
        """驗證 OID 機關寫入總數量門檻 (> 7000 筆)"""
        self.cursor.execute("SELECT COUNT(*) FROM master_agencies;")
        count = self.cursor.fetchone()[0]
        print(f"\n[VAL-GOV-G00-002] 當前寫入 OID 筆數: {count}")
        self.assertGreater(count, 7000)

    def test_VAL_GOV_G00_003_publisher_aliases(self):
        """驗證開放資料別名對齊筆數"""
        self.cursor.execute("SELECT COUNT(*) FROM publisher_aliases;")
        count = self.cursor.fetchone()[0]
        print(f"[VAL-GOV-G00-003] 當前對齊發布單位筆數: {count}")
        self.assertGreater(count, 0)

if __name__ == "__main__":
    unittest.main()
