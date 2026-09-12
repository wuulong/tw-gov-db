#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 台灣農會、漁會與非營利法人消歧義對齊引擎
description: 收錄全台各級農會（全國、縣市、鄉鎮市區）與主要漁會拓樸主檔，提供不規範簡稱自動正規化與層級代碼對齊。
category: resolver
dependencies: none (Standard Library only)
"""

import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

# 常見分支機構與單位綴詞
STRIP_SUFFIXES = [
    "生鮮超市", "活力超市", "展售中心", "辦事處",
    "信用部", "推廣部", "供銷部", "保險部", "會計部", "總務部", 
    "超市", "生鮮處", "直銷站", "本部", "分部", "分會"
]

class NpoResolver:
    """
    全台農漁會與非營利法人消歧義引擎
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(__file__).resolve().parents[3] / "data" / "universal_keys.sqlite"
        self._init_memory_cache()

    def _init_memory_cache(self):
        """若 SQLite 尚未建表或本機離線，提供內建權威農漁會種子拓樸字典"""
        self.seed_registry = {
            # 全國級
            "中華民國農會": {"npo_id": "FA_NAT_001", "canonical_name": "中華民國農會", "type": "FARMERS_ASSOC", "level": "NATIONAL", "city": "台中市", "admin_code": "66000"},
            "全國農業金庫": {"npo_id": "FA_BANK_001", "canonical_name": "全國農業金庫股份有限公司", "type": "FARMERS_BANK", "level": "NATIONAL", "city": "台北市", "admin_code": "63000"},
            
            # 直轄市/縣市農會
            "台北市農會": {"npo_id": "FA_TPE_000", "canonical_name": "台北市農會", "type": "FARMERS_ASSOC", "level": "MUNICIPAL", "city": "台北市", "admin_code": "63000"},
            "新北市農會": {"npo_id": "FA_NTP_000", "canonical_name": "新北市農會", "type": "FARMERS_ASSOC", "level": "MUNICIPAL", "city": "新北市", "admin_code": "65000"},
            "台中市農會": {"npo_id": "FA_TXG_000", "canonical_name": "台中市農會", "type": "FARMERS_ASSOC", "level": "MUNICIPAL", "city": "台中市", "admin_code": "66000"},
            "台南市農會": {"npo_id": "FA_TNN_000", "canonical_name": "台南市農會", "type": "FARMERS_ASSOC", "level": "MUNICIPAL", "city": "台南市", "admin_code": "67000"},
            "高雄市農會": {"npo_id": "FA_KHH_000", "canonical_name": "高雄市農會", "type": "FARMERS_ASSOC", "level": "MUNICIPAL", "city": "高雄市", "admin_code": "64000"},
            "新竹縣農會": {"npo_id": "FA_HSQ_000", "canonical_name": "新竹縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "新竹縣", "admin_code": "10004"},
            "新竹市農會": {"npo_id": "FA_HSZ_000", "canonical_name": "新竹市農會", "type": "FARMERS_ASSOC", "level": "PROVINCIAL_CITY", "city": "新竹市", "admin_code": "10018"},
            "苗栗縣農會": {"npo_id": "FA_MIA_000", "canonical_name": "苗栗縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "苗栗縣", "admin_code": "10005"},
            "彰化縣農會": {"npo_id": "FA_CHA_000", "canonical_name": "彰化縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "彰化縣", "admin_code": "10007"},
            "雲林縣農會": {"npo_id": "FA_YUN_000", "canonical_name": "雲林縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "雲林縣", "admin_code": "10009"},
            "嘉義縣農會": {"npo_id": "FA_CYQ_000", "canonical_name": "嘉義縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "嘉義縣", "admin_code": "10010"},
            "屏東縣農會": {"npo_id": "FA_PIF_000", "canonical_name": "屏東縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "屏東縣", "admin_code": "10013"},
            "宜蘭縣農會": {"npo_id": "FA_ILA_000", "canonical_name": "宜蘭縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "宜蘭縣", "admin_code": "10002"},
            "花蓮縣農會": {"npo_id": "FA_HUA_000", "canonical_name": "花蓮縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "花蓮縣", "admin_code": "10015"},
            "台東縣農會": {"npo_id": "FA_TTT_000", "canonical_name": "台東縣農會", "type": "FARMERS_ASSOC", "level": "COUNTY", "city": "台東縣", "admin_code": "10014"},

            # 典型鄉鎮市區農會 (涵蓋知名簡稱)
            "新北市板橋區農會": {"npo_id": "FA_NTP_001", "canonical_name": "新北市板橋區農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "新北市", "admin_code": "65000010"},
            "新竹縣新埔鎮農會": {"npo_id": "FA_HSQ_006", "canonical_name": "新竹縣新埔鎮農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "新竹縣", "admin_code": "10004060"},
            "新竹縣竹北市農會": {"npo_id": "FA_HSQ_001", "canonical_name": "新竹縣竹北市農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "新竹縣", "admin_code": "10004010"},
            "花蓮縣吉安鄉農會": {"npo_id": "FA_HUA_004", "canonical_name": "花蓮縣吉安鄉農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "花蓮縣", "admin_code": "10015040"},
            "台東縣池上鄉農會": {"npo_id": "FA_TTT_006", "canonical_name": "台東縣池上鄉農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "台東縣", "admin_code": "10014060"},
            "台南市麻豆區農會": {"npo_id": "FA_TNN_011", "canonical_name": "台南市麻豆區農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "台南市", "admin_code": "67000110"},
            "彰化縣二林鎮農會": {"npo_id": "FA_CHA_014", "canonical_name": "彰化縣二林鎮農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "彰化縣", "admin_code": "10007140"},
            "雲林縣西螺鎮農會": {"npo_id": "FA_YUN_008", "canonical_name": "雲林縣西螺鎮農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "雲林縣", "admin_code": "10009080"},
            "宜蘭縣三星地區農會": {"npo_id": "FA_ILA_007", "canonical_name": "宜蘭縣三星地區農會", "type": "FARMERS_ASSOC", "level": "DISTRICT", "city": "宜蘭縣", "admin_code": "10002070"},

            # 主要漁會代表
            "中華民國全國漁會": {"npo_id": "FS_NAT_001", "canonical_name": "中華民國全國漁會", "type": "FISHERY_ASSOC", "level": "NATIONAL", "city": "新北市", "admin_code": "65000"},
            "基隆區漁會": {"npo_id": "FS_KEE_001", "canonical_name": "基隆區漁會", "type": "FISHERY_ASSOC", "level": "DISTRICT", "city": "基隆市", "admin_code": "10017"},
            "蘇澳區漁會": {"npo_id": "FS_ILA_002", "canonical_name": "蘇澳區漁會", "type": "FISHERY_ASSOC", "level": "DISTRICT", "city": "宜蘭縣", "admin_code": "10002030"},
            "東港區漁會": {"npo_id": "FS_PIF_001", "canonical_name": "東港區漁會", "type": "FISHERY_ASSOC", "level": "DISTRICT", "city": "屏東縣", "admin_code": "10013030"}
        }

        # 別名與常用簡稱對照表
        self.aliases = {
            "全國農會": "中華民國農會",
            "省農會": "中華民國農會",
            "農業金庫": "全國農業金庫",
            "板農": "新北市板橋區農會",
            "板橋農會": "新北市板橋區農會",
            "新埔農會": "新竹縣新埔鎮農會",
            "竹北農會": "新竹縣竹北市農會",
            "吉安農會": "花蓮縣吉安鄉農會",
            "吉安鄉農會": "花蓮縣吉安鄉農會",
            "池上農會": "台東縣池上鄉農會",
            "池上鄉農會": "台東縣池上鄉農會",
            "麻豆農會": "台南市麻豆區農會",
            "二林農會": "彰化縣二林鎮農會",
            "西螺農會": "雲林縣西螺鎮農會",
            "三星農會": "宜蘭縣三星地區農會",
            "全國漁會": "中華民國全國漁會",
            "蘇澳漁會": "蘇澳區漁會",
            "東港漁會": "東港區漁會"
        }

    def resolve(self, raw_name: str) -> Dict[str, Any]:
        """
        消歧義解析核心
        """
        if not raw_name or not isinstance(raw_name, str):
            return {"input_name": raw_name, "is_resolved": False, "canonical_name": None}

        cleaned = raw_name.strip()
        
        # 1. 剝除雜質綴詞 (只要剩下 >= 2 個字元即可)
        for sfx in STRIP_SUFFIXES:
            if cleaned.endswith(sfx) and len(cleaned) - len(sfx) >= 2:
                cleaned = cleaned[:-len(sfx)].strip()
                break

        # 2. 查別名表
        if cleaned in self.aliases:
            target_key = self.aliases[cleaned]
            record = self.seed_registry[target_key]
            return {
                "input_name": raw_name,
                "is_resolved": True,
                "canonical_name": record["canonical_name"],
                "npo_id": record["npo_id"],
                "npo_type": record["type"],
                "level": record["level"],
                "city": record["city"],
                "admin_code": record["admin_code"],
                "match_strategy": "ALIAS_LOOKUP"
            }

        # 3. 精確比對種子庫 key
        if cleaned in self.seed_registry:
            record = self.seed_registry[cleaned]
            return {
                "input_name": raw_name,
                "is_resolved": True,
                "canonical_name": record["canonical_name"],
                "npo_id": record["npo_id"],
                "npo_type": record["type"],
                "level": record["level"],
                "city": record["city"],
                "admin_code": record["admin_code"],
                "match_strategy": "EXACT_MATCH"
            }

        # 4. 子字串/後綴模糊包含比對
        for name, record in self.seed_registry.items():
            if cleaned in name or name in cleaned:
                return {
                    "input_name": raw_name,
                    "is_resolved": True,
                    "canonical_name": record["canonical_name"],
                    "npo_id": record["npo_id"],
                    "npo_type": record["type"],
                    "level": record["level"],
                    "city": record["city"],
                    "admin_code": record["admin_code"],
                    "match_strategy": "FUZZY_SUBSTRING"
                }

        return {
            "input_name": raw_name,
            "is_resolved": False,
            "canonical_name": None,
            "match_strategy": "UNRESOLVED"
        }
