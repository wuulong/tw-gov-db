#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CGS v2.4 (Pipeline-Native) 管道串接單元測試
"""

import sys
import json
import unittest
from io import StringIO
from unittest.mock import patch
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
GOV_SRC = MODULE_ROOT / "src"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
if str(GOV_SRC) not in sys.path:
    sys.path.insert(0, str(GOV_SRC))


import importlib.util

govdb_cli_path = MODULE_ROOT / "scripts" / "govdb_cli.py"
spec = importlib.util.spec_from_file_location("govdb_cli", govdb_cli_path)
govdb_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(govdb_cli)

search_publisher_alias = govdb_cli.search_publisher_alias
from modules.g10_report_miner.g10_core import search_grb_projects



class TestCGSV24Pipeline(unittest.TestCase):

    def test_VAL_CGS_V24_001_govdb_alias_query(self):
        """驗證 govdb_cli alias API 在預設/外接 DB 環境下正常查獲 OID"""
        results = search_publisher_alias("經濟部水利署")
        self.assertTrue(len(results) > 0, "應查得水利署別名資訊")
        self.assertEqual(results[0]["mapped_agency_oid"], "2.16.886.101.20003.20007.20014")

    def test_VAL_CGS_V24_002_grb_search_query(self):
        """驗證 g10_cli search_grb 關鍵字檢索正常回傳結果"""
        res = search_grb_projects(kw="石門水庫", limit=5)
        self.assertIn("results", res)
        self.assertTrue(len(res["results"]) > 0, "應檢索出石門水庫相關計畫")


if __name__ == "__main__":
    unittest.main()
