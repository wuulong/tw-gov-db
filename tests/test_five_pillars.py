#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 全政府五大基石與 Core SDK 單元測試套件
description: 測試 GovBaseEntity 繼承、民國內時間清洗、5 Pillars 驗證器與 BaseAdapter。
category: testing
dependencies: unittest
"""

import sys
import unittest
from pathlib import Path

# 將專案目錄加入 sys.path 以防 import 失敗
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

src_path = Path(__file__).resolve().parents[1] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from core.gov_base_entity import GovBaseEntity, clean_datetime, validate_base_entity
from core.base_adapter import BaseDomainAdapter

class TestAgroCropEntity(GovBaseEntity):
    """模擬 tw-agro-db 子專案繼承模型"""
    def __init__(self, crop_code: str, crop_name: str, **kwargs):
        super().__init__(**kwargs)
        self.crop_code = crop_code
        self.crop_name = crop_name

class TestFivePillars(unittest.TestCase):

    def test_VAL_GOV_G02_001_required_fields(self):
        """驗證 [VAL-GOV-G02-001] GovBaseEntity 必填欄位校驗"""
        with self.assertRaises(ValueError):
            # 缺少 agency_oid 應拋出 ValueError
            GovBaseEntity(agency_oid="")

    def test_VAL_GOV_G02_002_datetime_cleaning(self):
        """驗證 [VAL-GOV-G02-002] 民國年自動轉換 ISO-8601"""
        iso_dt = clean_datetime("115/08/22")
        self.assertTrue(iso_dt.startswith("2026-08-22"))

    def test_VAL_GOV_G02_003_universal_key_validators(self):
        """驗證 [VAL-GOV-G02-003] 統編 8 碼與行政區 6 碼格式稽核"""
        # 合法格式
        entity = GovBaseEntity(
            agency_oid="2.16.886.101.20003.20064",
            tax_id="12345678",
            admin_code="630000"
        )
        self.assertEqual(entity.tax_id, "12345678")

        # 不合法統編 (非 8 碼)
        with self.assertRaises(ValueError):
            GovBaseEntity(agency_oid="2.16.886.101.20003.20064", tax_id="12345")

    def test_VAL_GOV_G02_004_subdomain_inheritance(self):
        """驗證 [VAL-GOV-G02-004] 子專案 (tw-agro-db) 模型成功繼承 GovBaseEntity"""
        crop = TestAgroCropEntity(
            agency_oid="2.16.886.101.20003.20064",
            crop_code="N04",
            crop_name="高麗菜",
            cadastral_id="F-01-0001-0000",
            river_id="1300"
        )
        self.assertEqual(crop.agency_oid, "2.16.886.101.20003.20064")
        self.assertEqual(crop.crop_name, "高麗菜")
        self.assertEqual(crop.river_id, "1300")
        self.assertEqual(crop.spec_version, "0.2")

if __name__ == "__main__":
    unittest.main()
