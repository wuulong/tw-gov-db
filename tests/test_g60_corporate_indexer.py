#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G60 全政府法人、企業與農漁會維度器自動化單元測試 (CGS v2.4)
"""

import sys
import json
import subprocess
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = PROJECT_ROOT / "src" / "modules" / "g60_corporate_indexer"
PYTHON_BIN = "/Users/wuulong/opt/anaconda3/envs/m2504/bin/python"

if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from ban_validator import BanValidator
from npo_resolver import NpoResolver


class TestG60CorporateIndexer(unittest.TestCase):

    def test_ban_validator_legacy_and_new_rule(self):
        """測試 1: 統編雙軌加權檢查碼驗證 (舊制、2023新制、第7位為7特例、偽碼)"""
        # 台積電 (符合舊制除10)
        res_tsmc = BanValidator.validate("04595257")
        self.assertTrue(res_tsmc["is_valid"])
        self.assertTrue(res_tsmc["valid_by_legacy"])
        self.assertTrue(res_tsmc["valid_by_current"])

        # 聯發科 (符合2023新制除5)
        res_mtk = BanValidator.validate("16525386")
        self.assertTrue(res_mtk["is_valid"])
        self.assertTrue(res_mtk["valid_by_current"])

        # 第 7 位為 7 特例
        res_r7 = BanValidator.validate("10458575")
        self.assertTrue(res_r7["is_valid"])
        self.assertTrue(res_r7["has_special_rule_7"])

        # 偽碼
        res_fake = BanValidator.validate("12345678")
        self.assertFalse(res_fake["is_valid"])

    def test_text_stream_extraction(self):
        """測試 2: 長文本萃取合法統編並排除日期與偽碼"""
        text = "標案公告：台灣積體電路(04595257)得標，開工日期20240912，履約保證金偽碼88888888，協力廠商為中華電信(96979933)。"
        extracted = BanValidator.extract_from_text(text)
        tax_ids = [x["tax_id"] for x in extracted]
        self.assertIn("04595257", tax_ids)
        self.assertIn("96979933", tax_ids)
        self.assertNotIn("20240912", tax_ids)
        self.assertNotIn("88888888", tax_ids)

    def test_npo_resolver(self):
        """測試 3: 全台農漁會消歧義與後綴剝除"""
        resolver = NpoResolver()
        
        # 別名與後綴剝除
        res1 = resolver.resolve("板農信用部")
        self.assertTrue(res1["is_resolved"])
        self.assertEqual(res1["canonical_name"], "新北市板橋區農會")
        self.assertEqual(res1["level"], "DISTRICT")

        # 鄉鎮農會與超市綴詞
        res2 = resolver.resolve("新埔農會生鮮超市")
        self.assertTrue(res2["is_resolved"])
        self.assertEqual(res2["canonical_name"], "新竹縣新埔鎮農會")

        # 漁會
        res3 = resolver.resolve("東港漁會")
        self.assertTrue(res3["is_resolved"])
        self.assertEqual(res3["canonical_name"], "東港區漁會")

    def test_g60_cli_commands(self):
        """測試 4: g60_cli 常用命令與純淨 JSON 輸出"""
        cli_path = MODULE_DIR / "g60_cli.py"

        # status
        p = subprocess.run([PYTHON_BIN, str(cli_path), "status", "-j"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertEqual(data["module"], "g60_corporate_indexer")
        self.assertEqual(data["cgs_version"], "2.4")

        # check
        p = subprocess.run([PYTHON_BIN, str(cli_path), "check", "04595257", "-j"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertTrue(data[0]["is_valid"])

        # lookup
        p = subprocess.run([PYTHON_BIN, str(cli_path), "lookup", "04595257", "-j"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertEqual(data[0]["company_name"], "台灣積體電路製造股份有限公司")

        # resolve
        p = subprocess.run([PYTHON_BIN, str(cli_path), "resolve", "板農", "-j"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertEqual(data[0]["canonical_name"], "新北市板橋區農會")

    def test_g60_cli_pipeline_stdin(self):
        """測試 5: UNIX Pipe Stdin 串流輸入"""
        cli_path = MODULE_DIR / "g60_cli.py"

        # 1. 批量 check via stdin
        input_data = "04595257\n12345678\n96979933"
        p = subprocess.run([PYTHON_BIN, str(cli_path), "check", "-j"], input=input_data, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        items = json.loads(p.stdout)
        self.assertEqual(len(items), 3)
        self.assertTrue(items[0]["is_valid"])
        self.assertFalse(items[1]["is_valid"])
        self.assertTrue(items[2]["is_valid"])

        # 2. pipe --extract-tax-id via stdin
        long_doc = "重要標案記錄：由中華電信(96979933)承作，無效統編11111111。"
        p2 = subprocess.run([PYTHON_BIN, str(cli_path), "pipe"], input=long_doc, capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0)
        extracted = json.loads(p2.stdout)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["tax_id"], "96979933")


if __name__ == "__main__":
    unittest.main()
