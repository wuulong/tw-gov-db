import csv
import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Tuple

PRIMARY_OID_CSV = Path("/Volumes/D2024/data/prj/公文模型/政府組織/政府機關唯一識別程式碼.csv")
PRIMARY_ORG_TREE = Path("/Volumes/D2024/data/prj/公文模型/政府組織/政府組織架構_全.txt")

ALT_OID_CSV = Path(__file__).resolve().parents[3] / "sys_eng" / "01_requirements" / "政府機關唯一識別程式碼.csv"
ALT_ORG_TREE = Path(__file__).resolve().parents[3] / "sys_eng" / "01_requirements" / "政府組織架構_全.txt"

OPEN_DATA_DB_PATH = Path.home() / "github/bmad-pa/data/open-data/gov_opendata_platform.db"
TARGET_DB_PATH = Path(__file__).resolve().parents[2] / "ontology" / "master_agencies.sqlite"

class BootstrapAligner:
    def __init__(self, target_db: Path = TARGET_DB_PATH):
        self.target_db = target_db
        self.name_to_oid: Dict[str, str] = {}
        self.child_to_parent: Dict[str, str] = {}

    def _open_file(self, primary_path: Path, alt_path: Path, mode: str = "r", encoding: str = "utf-8-sig"):
        if alt_path.exists():
            return open(alt_path, mode=mode, encoding=encoding)
        return open(primary_path, mode=mode, encoding=encoding)

    def load_oid_csv(self) -> int:
        """讀取 OID CSV 檔並寫入 master_agencies 表格"""
        conn = sqlite3.connect(str(self.target_db))
        cursor = conn.cursor()
        count = 0

        with self._open_file(PRIMARY_OID_CSV, ALT_OID_CSV) as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("機關名稱", "").strip()
                oid = row.get("OID", "").strip()
                org_code = row.get("機關代號", "").strip()
                if not name or not oid:
                    continue

                self.name_to_oid[name] = oid
                cursor.execute("""
                    INSERT OR REPLACE INTO master_agencies (agency_oid, org_code, agency_name)
                    VALUES (?, ?, ?)
                """, (oid, org_code, name))
                count += 1

        conn.commit()
        conn.close()
        print(f"✅ [1/3] 成功載入 OID 機關主檔: {count} 筆")
        return count

    def build_parent_hierarchy(self) -> int:
        """解析組織樹文字檔並更新 parent_oid (父子階層)"""
        stack: List[Tuple[int, str]] = []

        with self._open_file(PRIMARY_ORG_TREE, ALT_ORG_TREE) as f:
            for line in f:
                raw_line = line.rstrip("\n\r")
                if not raw_line.strip():
                    continue

                indent = 0
                if "|--" in raw_line:
                    indent = raw_line.find("|--") // 4 + 1
                    name = raw_line.split("|--")[-1].strip()
                else:
                    name = raw_line.strip()

                while stack and stack[-1][0] >= indent:
                    stack.pop()

                if stack:
                    parent_name = stack[-1][1]
                    self.child_to_parent[name] = parent_name

                stack.append((indent, name))

        conn = sqlite3.connect(str(self.target_db))
        cursor = conn.cursor()
        updated_parents = 0

        for child_name, parent_name in self.child_to_parent.items():
            child_oid = self.name_to_oid.get(child_name)
            parent_oid = self.name_to_oid.get(parent_name)
            if child_oid and parent_oid:
                cursor.execute("""
                    UPDATE master_agencies
                    SET parent_oid = ?
                    WHERE agency_oid = ?
                """, (parent_oid, child_oid))
                updated_parents += 1

        conn.commit()
        conn.close()
        print(f"✅ [2/3] 成功綁定組織樹父子階層 (parent_oid): {updated_parents} 筆")
        return updated_parents

    def align_publisher_aliases(self) -> int:
        """從開放資料 DB 讀取發布單位名稱，執行「精準對齊」與「內部司處/簡稱上溯對齊」並寫入 publisher_aliases"""
        if not OPEN_DATA_DB_PATH.exists():
            print(f"⚠️ 開放資料 DB 不存在: {OPEN_DATA_DB_PATH}")
            return 0

        source_conn = sqlite3.connect(str(OPEN_DATA_DB_PATH))
        source_cursor = source_conn.cursor()
        source_cursor.execute("SELECT DISTINCT 提供機關 FROM open_data_catalog WHERE 提供機關 IS NOT NULL")
        publishers = [row[0].strip() for row in source_cursor.fetchall() if row[0].strip()]
        source_conn.close()

        target_conn = sqlite3.connect(str(self.target_db))
        target_cursor = target_conn.cursor()
        matched = 0

        for pub in publishers:
            mapped_oid = None
            confidence = 1.0

            # 1. 第一階：完全比對權威 OID 主檔名稱
            if pub in self.name_to_oid:
                mapped_oid = self.name_to_oid[pub]
                confidence = 1.0
            # 2. 第二階：若屬於組織樹內部司處，向父機關上溯
            elif pub in self.child_to_parent:
                parent_name = self.child_to_parent[pub]
                if parent_name in self.name_to_oid:
                    mapped_oid = self.name_to_oid[parent_name]
                    confidence = 0.9
            # 3. 第三階：常態簡稱/後綴模糊對齊 (如 "消防署" -> "內政部消防署")
            else:
                for full_name, oid in self.name_to_oid.items():
                    if full_name.endswith(pub) or pub in full_name:
                        mapped_oid = oid
                        confidence = 0.8
                        break

            if mapped_oid:
                target_cursor.execute("""
                    INSERT OR REPLACE INTO publisher_aliases (raw_publisher_name, mapped_agency_oid, confidence_score)
                    VALUES (?, ?, ?)
                """, (pub, mapped_oid, confidence))
                matched += 1

        target_conn.commit()
        target_conn.close()
        rate = (matched / len(publishers) * 100) if publishers else 0
        print(f"✅ [3/3] 成功完成發布單位對齊 (含司處上溯與簡稱匹配): {matched} / {len(publishers)} 筆 (對齊率 {rate:.1f}%)")
        return matched

def run_full_bootstrap():
    aligner = BootstrapAligner()
    aligner.load_oid_csv()
    aligner.build_parent_hierarchy()
    aligner.align_publisher_aliases()

if __name__ == "__main__":
    run_full_bootstrap()
