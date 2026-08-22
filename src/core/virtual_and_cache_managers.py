#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: Corporate Pass-Through Cache 與 Virtual Law Adapter Core SDK
description: 提供 corporate_registry 通用快照旁路透傳快取 (Pass-Through Cache) 與外部 law_db 虛擬層適配器。
category: core
dependencies: sqlite3, urllib, json
"""

import sys
import ssl
import json
import sqlite3
import urllib.request
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

DB_PATH = Path(__file__).resolve().parents[2] / "ontology" / "universal_keys.sqlite"
LAW_CLI_PATH = Path(__file__).resolve().parents[3] / "law_meta_in" / "scripts" / "law_cli.py"

class CorporateCacheManager:
    """
    [快取層 Cache Layer] 企業法人資料 Pass-Through 快取管理器 (借鏡 tw-med-db 模式)
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def get_company(self, tax_id: str) -> Optional[Dict[str, Any]]:
        """1. 優先查詢本機 Cache"""
        if not tax_id or len(tax_id) != 8:
            return None

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT tax_id, company_name, registered_address, admin_code, cached_at FROM corporate_registry WHERE tax_id = ?", (tax_id,))
        row = cursor.fetchone()

        if row:
            conn.close()
            return {
                "tax_id": row[0],
                "company_name": row[1],
                "registered_address": row[2],
                "admin_code": row[3],
                "cached_at": row[4],
                "cache_hit": True
            }

        # 2. Cache Miss: 自動發動旁路透傳 Pass-Through
        fetched = self._fetch_from_remote_gcis(tax_id)
        if fetched:
            cursor.execute("""
                INSERT OR REPLACE INTO corporate_registry (tax_id, company_name, registered_address, admin_code)
                VALUES (?, ?, ?, ?)
            """, (fetched["tax_id"], fetched["company_name"], fetched.get("registered_address"), fetched.get("admin_code")))
            conn.commit()
            fetched["cache_hit"] = False
            conn.close()
            return fetched

        conn.close()
        return None

    def _fetch_from_remote_gcis(self, tax_id: str) -> Optional[Dict[str, Any]]:
        """旁路透傳：連線商業發展署 API 抓取並回傳"""
        url = f"https://data.gcis.nat.gov.tw/od/data/api/5F64D864-6D36-4D50-A540-8918B42E469C?$format=json&$filter=Business_Accounting_NO eq {tax_id}"
        try:
            cmd = ["curl", "-s", "-k", "-A", "Mozilla/5.0", url]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                items = json.loads(res.stdout)
                if items and isinstance(items, list):
                    item = items[0]
                    return {
                        "tax_id": tax_id,
                        "company_name": item.get("Company_Name") or item.get("Bussiness_Name") or "未知企業",
                        "registered_address": item.get("Company_Location") or item.get("Bussiness_Address")
                    }
        except Exception:
            pass
        return None


class VirtualLawAdapter:
    """
    [虛擬層 Virtual Layer] 外部 law_db 法律與處務規程適配器 (零本機儲存)
    """
    def __init__(self, law_cli_script: Path = LAW_CLI_PATH):
        self.law_cli_script = law_cli_script

    def search_mandate_laws(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """透過 law_cli.py 查詢外部法規與處務規程"""
        if not self.law_cli_script.exists():
            return []

        try:
            python_bin = sys.executable
            cmd = [python_bin, str(self.law_cli_script), "search", keyword, "--limit", str(limit), "--json"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        return []
