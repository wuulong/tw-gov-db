#!/usr/bin/env python3
"""
[metadata]
name: etl.py
description: GOV-AXX 子模組 ETL 資料處理與 attributes_json (spec_version: 0.2.1) 範本
"""

import json

def parse_and_transform_record(raw_record: dict) -> dict:
    """
    實作資料清洗與 attributes_json 強制寫入
    """
    history_trail = []
    
    # 範例：時間清洗
    raw_date = raw_record.get("date_raw", "")
    clean_date = raw_date  # 呼叫 BaseDomainAdapter.clean_datetime(raw_date)
    history_trail.append({
        "timestamp": "2026-08-22T16:58:00+08:00",
        "field": "date_raw",
        "original_val": raw_date,
        "cleaned_val": clean_date,
        "rule_applied": "clean_datetime"
    })

    attributes_json = {
        "_v": "0.2.1",
        "history_trail": history_trail
    }

    return {
        "entity_id": raw_record.get("id"),
        "date_clean": clean_date,
        "attributes_json": json.dumps(attributes_json, ensure_ascii=False)
    }
