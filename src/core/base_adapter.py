#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: BaseDomainAdapter 共享基底類別
description: 提供各部會 Domain Adapter 繼承調用之 Core SDK 基底類別，實作 5 Pillars 轉換與驗證介面。
category: core
dependencies: pydantic, sqlite3
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.gov_base_entity import GovBaseEntity, validate_base_entity

MASTER_DB_PATH = Path(__file__).resolve().parents[2] / "ontology" / "master_agencies.sqlite"

class BaseDomainAdapter:
    """
    [Core SDK] 全政府部會 Domain Adapter 抽象基底類別
    """
    def __init__(self, root_agency_oid: str, master_db: Path = MASTER_DB_PATH):
        self.root_agency_oid = root_agency_oid
        self.master_db = master_db

    def align_publisher_oid(self, raw_publisher_name: str) -> Optional[str]:
        """從 master_agencies.sqlite 調用發布單位別名對齊，回傳權威 OID"""
        if not self.master_db.exists():
            return None
        
        conn = sqlite3.connect(str(self.master_db))
        cursor = conn.cursor()
        cursor.execute("SELECT mapped_agency_oid FROM publisher_aliases WHERE raw_publisher_name = ?", (raw_publisher_name.strip(),))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else self.root_agency_oid

    def validate_entity(self, entity_data: Dict[str, Any]) -> GovBaseEntity:
        """強制校驗資料是否符合全政府五大基石介面"""
        if "agency_oid" not in entity_data or not entity_data["agency_oid"]:
            entity_data["agency_oid"] = self.root_agency_oid
        return validate_base_entity(entity_data)
