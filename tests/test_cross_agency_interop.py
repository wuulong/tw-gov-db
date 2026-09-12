#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五大通用基石 (G10-G60) 跨部會 Python Direct Import 與互通整合測試
"""

import sys
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class TestCrossAgencyInterop(unittest.TestCase):

    def test_g10_report_miner_direct_import(self):
        """驗證 G10 施政計畫探勘直接 Import"""
        from modules.g10_report_miner.g10_core import search_grb_projects
        res = search_grb_projects(kw="水利", limit=1)
        self.assertGreater(res["total_results"], 0)
        self.assertGreater(len(res["results"]), 0)

    def test_g20_spatial_indexer_direct_import(self):
        """驗證 G20 空間地理與地址解析直接 Import"""
        from modules.g20_spatial_indexer.g20_cli import parse_address_string
        res = parse_address_string("新竹縣竹北市光明六路10號")
        self.assertEqual(res.get("raw_address"), "新竹縣竹北市光明六路10號")

    def test_g30_mandate_indexer_direct_import(self):
        """驗證 G30 機關權責與組織圖譜直接 Import"""
        from modules.g30_mandate_indexer.g30_cli import get_canonical_oid
        oid = get_canonical_oid("農業部")
        self.assertEqual(oid, "2.16.886.101.20003.20064")

    def test_g40_temporal_indexer_direct_import(self):
        """驗證 G40 時間時序與農曆節氣直接 Import"""
        from modules.g40_temporal_indexer.g40_cli import clean_date_string
        from modules.g40_temporal_indexer.lunar_engine import solar_to_lunar
        
        # 民國年清洗
        d = clean_date_string("113/08/22")
        self.assertEqual(d["date_str"], "2024-08-22")
        self.assertEqual(d["minguo_year"], 113)

        # 農曆節氣解算
        lunar = solar_to_lunar(date(2024, 8, 22))
        self.assertEqual(lunar["gan_zhi"], "甲辰")
        self.assertEqual(lunar["sheng_xiao"], "龍")
        self.assertEqual(lunar["solar_term"], "處暑")

    def test_g60_corporate_indexer_direct_import(self):
        """驗證 G60 法人統編與農漁會消歧義直接 Import"""
        from modules.g60_corporate_indexer.ban_validator import BanValidator
        from modules.g60_corporate_indexer.npo_resolver import NpoResolver

        # 統編加權檢核
        v_tsmc = BanValidator.validate("04595257")
        self.assertTrue(v_tsmc["is_valid"])

        # 農會消歧義
        resolver = NpoResolver()
        npo = resolver.resolve("新埔農會生鮮超市")
        self.assertTrue(npo["is_resolved"])
        self.assertEqual(npo["canonical_name"], "新竹縣新埔鎮農會")
        self.assertEqual(npo["npo_id"], "FA_HSQ_006")


if __name__ == "__main__":
    unittest.main()
