#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: G50 輕量水理拓樸解析引擎 (Micro Topology Engine)
description: 純 Python 實作基於 WRA-Civ topology_path 之上下游微秒級親緣追溯、子樹展開與家族樹生成，零外部第三方庫依賴。
category: core
dependencies: sqlite3
"""

import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "universal_keys.sqlite"

STRIP_RIVER_SUFFIXES = ["水系", "主流", "支流", "溪畔", "河畔", "流域", "排水分線", "排水幹線"]


class RiverTopologyEngine:
    """
    純 Python 微型水理拓樸引擎 (相容 WRA-Civ 雙層編碼與 @ 拓樸樹)
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_river(self, query: str) -> Optional[Dict[str, Any]]:
        """以代碼或名稱精確查詢單一水脈"""
        if not query:
            return None
        q_clean = query.strip()

        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM river_registry WHERE river_code = ?;", (q_clean,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT * FROM river_registry WHERE river_name = ? LIMIT 1;", (q_clean,))
            row = cursor.fetchone()

        if not row:
            # 嘗試剝除綴詞
            for sfx in STRIP_RIVER_SUFFIXES:
                if q_clean.endswith(sfx) and len(q_clean) > len(sfx):
                    stripped = q_clean[:-len(sfx)].strip()
                    cursor.execute("SELECT * FROM river_registry WHERE river_name = ? LIMIT 1;", (stripped,))
                    row = cursor.fetchone()
                    if row:
                        break

        conn.close()
        return dict(row) if row else None

    def get_ancestors(self, river_code: str) -> List[Dict[str, Any]]:
        """
        向主流向下追溯所有直系祖先 (Downstream Mainstream Chain)
        演算法：解析 topology_path 中 @ 分隔的節點鏈
        """
        record = self.get_river(river_code)
        if not record:
            return []

        topo_path = record.get("topology_path", "")
        if not topo_path:
            return [record]

        # 0@114000@114020@114021 -> codes: ['114000', '114020', '114021']
        parts = [p for p in topo_path.split("@") if p and p != "0"]
        if not parts:
            return [record]

        conn = self._get_conn()
        cursor = conn.cursor()

        # 批次取出所有祖先資料
        placeholders = ",".join(["?"] * len(parts))
        cursor.execute(f"SELECT * FROM river_registry WHERE river_code IN ({placeholders});", parts)
        rows_by_code = {r["river_code"]: dict(r) for r in cursor.fetchall()}
        conn.close()

        # 按照親緣鏈由幹流至支流依序排列
        ancestors = []
        for code in parts:
            if code in rows_by_code:
                ancestors.append(rows_by_code[code])
            elif code == record["river_code"]:
                ancestors.append(record)

        return ancestors

    def get_descendants(self, river_code: str, max_depth: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        向上游發源地展開所有支流子樹 (Upstream Source Tree)
        演算法：利用 SQL 前綴比對 topology_path LIKE 'current_path@%'
        """
        record = self.get_river(river_code)
        if not record:
            return []

        current_path = record["topology_path"]
        current_order = record["stream_order"]

        conn = self._get_conn()
        cursor = conn.cursor()

        prefix_pattern = f"{current_path}@%"
        cursor.execute("""
        SELECT * FROM river_registry 
        WHERE topology_path LIKE ? AND river_code != ?
        ORDER BY stream_order ASC, river_code ASC;
        """, (prefix_pattern, record["river_code"]))

        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if max_depth is not None:
            rows = [r for r in rows if r["stream_order"] <= current_order + max_depth]

        return rows

    def search_rivers(
        self,
        keyword: Optional[str] = None,
        basin: Optional[str] = None,
        county: Optional[str] = None,
        official_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """多維度複合檢索水脈"""
        conn = self._get_conn()
        cursor = conn.cursor()

        conditions = ["status = 'ACTIVE'"]
        params = []

        if keyword:
            kw_clean = keyword.strip()
            conditions.append("(river_name LIKE ? OR river_code LIKE ?)")
            params.extend([f"%{kw_clean}%", f"%{kw_clean}%"])

        if basin:
            conditions.append("basin_name LIKE ?")
            params.append(f"%{basin.strip()}%")

        if county:
            conditions.append("primary_county LIKE ?")
            params.append(f"%{county.strip()}%")

        if official_only:
            conditions.append("is_civilian = 0")

        where_clause = " AND ".join(conditions)
        query_sql = f"""
        SELECT * FROM river_registry
        WHERE {where_clause}
        ORDER BY stream_order ASC, river_code ASC
        LIMIT ?;
        """
        params.append(limit)

        cursor.execute(query_sql, params)
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return results

    def get_stations_for_river(self, river_code: str) -> List[Dict[str, Any]]:
        """查詢關聯至該河流或祖先幹流的代表性測站"""
        ancestors = self.get_ancestors(river_code)
        target_codes = [a["river_code"] for a in ancestors] if ancestors else [river_code]

        conn = self._get_conn()
        cursor = conn.cursor()

        placeholders = ",".join(["?"] * len(target_codes))
        cursor.execute(f"""
        SELECT * FROM station_registry 
        WHERE river_code IN ({placeholders});
        """, target_codes)

        stations = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return stations
