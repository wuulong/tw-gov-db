#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 全政府通用基礎實體模型與五大基石驗證器 (GovBaseEntity & Pillars)
description: 提供全政府共通鍵定義 (Identity, Spatial, Hydrology, Corporate, Temporal) 與 Core SDK 基底驗證器 (無外部相依性)
category: core
dependencies: sqlite3, json, re, datetime
"""

import re
import json
from typing import Optional, Dict, Any
from datetime import datetime

def clean_datetime(dt_input: Any) -> str:
    """自動將民國年 (如 115/08/22) 或各類時間字串統一轉化為 ISO-8601 時間格式"""
    if not dt_input:
        return datetime.now().isoformat()

    dt_str = str(dt_input).strip()
    
    # 處理民國年格式: 115/08/22, 115-08-22, 1150822
    minguo_match = re.match(r"^(\d{2,3})[/\-\.]?(\d{2})[/\-\.]?(\d{2})$", dt_str)
    if minguo_match:
        year = int(minguo_match.group(1)) + 1911
        month = int(minguo_match.group(2))
        day = int(minguo_match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}T00:00:00+08:00"

    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception:
        return dt_str

class GovBaseEntity:
    """
    [基石五] 核心基底實體：所有部會 Domain Adapter 匯出之實體必須繼承此物件
    """
    def __init__(
        self,
        agency_oid: str,
        spec_version: str = "0.2",
        updated_at: Optional[str] = None,
        org_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        cadastral_id: Optional[str] = None,
        admin_code: Optional[str] = None,
        river_id: Optional[str] = None,
        station_id: Optional[str] = None,
        tax_id: Optional[str] = None,
        pseudonym_id: Optional[str] = None,
        **extra
    ):
        if not agency_oid:
            raise ValueError("必填欄位 agency_oid 不能為空")

        self.spec_version = spec_version
        self.updated_at = clean_datetime(updated_at)
        self.agency_oid = agency_oid
        self.org_code = org_code
        self.latitude = latitude
        self.longitude = longitude
        self.cadastral_id = cadastral_id
        self.river_id = river_id
        self.station_id = station_id
        self.pseudonym_id = pseudonym_id

        # 基石四：驗證 tax_id 8 碼
        if tax_id:
            if not re.match(r"^\d{8}$", str(tax_id)):
                raise ValueError(f"統一編號必須為 8 碼數字: {tax_id}")
            self.tax_id = str(tax_id)
        else:
            self.tax_id = None

        # 基石二：驗證 admin_code 6 碼
        if admin_code:
            if not re.match(r"^\d{6}$", str(admin_code)):
                raise ValueError(f"行政區程式碼必須為 6 碼數字: {admin_code}")
            self.admin_code = str(admin_code)
        else:
            self.admin_code = None

        self.extra = extra

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "spec_version": self.spec_version,
            "updated_at": self.updated_at,
            "agency_oid": self.agency_oid,
            "org_code": self.org_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "cadastral_id": self.cadastral_id,
            "admin_code": self.admin_code,
            "river_id": self.river_id,
            "station_id": self.station_id,
            "tax_id": self.tax_id,
            "pseudonym_id": self.pseudonym_id,
        }
        res.update(self.extra)
        return res

def validate_base_entity(data: Dict[str, Any]) -> GovBaseEntity:
    """驗證資料是否符合全政府五大基石介面規範"""
    return GovBaseEntity(**data)
