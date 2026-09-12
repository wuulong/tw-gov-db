#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G40 Temporal Indexer 單元測試 (CGS v2.4 規範)
"""

import sys
import os
import unittest
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = MODULE_ROOT / "src"
G40_DIR = SRC_DIR / "modules" / "g40_temporal_indexer"

if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(G40_DIR) not in sys.path:
    sys.path.insert(0, str(G40_DIR))

import importlib.util
g40_path = G40_DIR / "g40_cli.py"
spec = importlib.util.spec_from_file_location("g40_cli", g40_path)
g40_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g40_cli)

clean_date_string = g40_cli.clean_date_string


class TestG40TemporalIndexer(unittest.TestCase):

    def test_VAL_G40_001_clean_minguo_dates(self):
        """驗證民國年多種格式清洗為標準 ISO-8601"""
        # 民國斜線格式
        res1 = clean_date_string("113/08/22")
        self.assertEqual(res1["type"], "DATE")
        self.assertEqual(res1["year"], 2024)
        self.assertEqual(res1["minguo_year"], 113)
        self.assertEqual(res1["date_str"], "2024-08-22")

        # 中文民國格式
        res2 = clean_date_string("民國113年8月22日")
        self.assertEqual(res2["type"], "DATE")
        self.assertEqual(res2["date_str"], "2024-08-22")

        # 民國 7 碼緊湊格式
        res3 = clean_date_string("1130822")
        self.assertEqual(res3["type"], "DATE")
        self.assertEqual(res3["date_str"], "2024-08-22")

    def test_VAL_G40_002_clean_quarters_and_years(self):
        """驗證季度與年度維度解析"""
        res_q = clean_date_string("113Q3")
        self.assertEqual(res_q["type"], "QUARTER")
        self.assertEqual(res_q["quarter"], 3)
        self.assertEqual(res_q["start_date"], "2024-07-01")
        self.assertEqual(res_q["end_date"], "2024-09-30")

        res_y = clean_date_string("113年度")
        self.assertEqual(res_y["type"], "YEAR")
        self.assertEqual(res_y["year"], 2024)
        self.assertEqual(res_y["start_date"], "2024-01-01")
        self.assertEqual(res_y["end_date"], "2024-12-31")

    def test_VAL_G40_003_makeup_workday_detection(self):
        """驗證政府辦公日曆對補班日 (週六出勤) 的判定"""
        import sqlite3
        db_path = str(MODULE_ROOT / "data" / "universal_keys.sqlite")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 2024-02-17 為春節小年夜補上班日 (週六)
        cursor.execute("SELECT is_holiday, is_working_day, holiday_category FROM calendar_registry WHERE date_str = '2024-02-17';")
        row = cursor.fetchone()
        self.assertIsNotNone(row, "應有 2024-02-17 紀錄")
        self.assertEqual(row[0], 0, "補上班日非放假日")
        self.assertEqual(row[1], 1, "補上班日為法定工作日")
        self.assertEqual(row[2], "補行上班日")

        # 2024-02-09 為除夕 (週五)
        cursor.execute("SELECT is_holiday, is_working_day, holiday_category FROM calendar_registry WHERE date_str = '2024-02-09';")
        row_cny = cursor.fetchone()
        self.assertIsNotNone(row_cny, "應有 2024-02-09 紀錄")
        self.assertEqual(row_cny[0], 1, "除夕為放假日")
        self.assertEqual(row_cny[1], 0, "除夕非工作日")

        conn.close()

    def test_VAL_G40_004_lunar_conversion(self):
        """驗證純 Python 農曆與公曆雙向精確轉換與節日辨識"""
        # 1. 2024 春節正月初一 (甲辰年、生肖龍)
        from datetime import date
        lunar_cny = g40_cli.solar_to_lunar(date(2024, 2, 10))
        self.assertEqual(lunar_cny["lunar_year"], 2024)
        self.assertEqual(lunar_cny["lunar_month"], 1)
        self.assertEqual(lunar_cny["lunar_day"], 1)
        self.assertEqual(lunar_cny["gan_zhi"], "甲辰")
        self.assertEqual(lunar_cny["sheng_xiao"], "龍")
        self.assertEqual(lunar_cny["festival"], "春節")

        # 2. 中秋節反查 (農曆 113 年八月十五 ➔ 2024-09-17)
        solar_mf = g40_cli.lunar_to_solar(2024, 8, 15)
        self.assertEqual(solar_mf["solar_date"], "2024-09-17")
        self.assertEqual(solar_mf["festival"], "中秋節")

        # 3. 中文農曆文字清洗: 農曆113年五月初五 ➔ 端午節 2024-06-10
        cleaned = g40_cli.clean_date_string("農曆113年五月初五")
        self.assertEqual(cleaned["type"], "LUNAR_DATE")
        self.assertEqual(cleaned["date_str"], "2024-06-10")
        self.assertEqual(cleaned["lunar"]["festival"], "端午節")

    def test_VAL_G40_005_solar_terms(self):
        """驗證二十四節氣計算精確度"""
        terms_2024 = g40_cli.get_solar_terms_for_year(2024)
        self.assertIn("清明", terms_2024)
        self.assertEqual(terms_2024["清明"], "2024-04-04")
        self.assertIn("冬至", terms_2024)
        self.assertEqual(terms_2024["冬至"], "2024-12-21")


if __name__ == "__main__":
    unittest.main()
