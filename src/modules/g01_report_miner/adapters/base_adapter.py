# -*- coding: utf-8 -*-
"""
G10 Base Report Adapter 抽象類別 (ABC)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseReportAdapter(ABC):
    """G10 下載策略抽象類別"""

    @abstractmethod
    def ingest_catalog(self, source_path: str) -> int:
        """載入全量目錄總表，回傳寫入/更新筆數"""
        pass

    @abstractmethod
    def fetch_report(self, report_uid: str, remote_url: str, output_dir: str) -> Dict[str, Any]:
        """二階段按需採集實體檔案，回傳採集結果資訊"""
        pass
