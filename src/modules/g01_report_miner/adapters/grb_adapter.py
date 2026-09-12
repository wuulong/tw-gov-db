# -*- coding: utf-8 -*-
"""
G10 GrbAdapter (政府研究資訊系統 GRB 全量開放資料與 XML/API 剖析適配器)
自動化等級: OPEN_DATA_XML / API
"""

import os
import ssl
import json
import zipfile
import io
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List
from .base_adapter import BaseReportAdapter

ssl_context = ssl._create_unverified_context()

class GrbAdapter(BaseReportAdapter):
    """GRB 全量開放資料 XML 剖析與計畫實體下載適配器"""

    def parse_xml_file(self, xml_path: Path, limit: int = 0) -> List[Dict[str, Any]]:
        """剖析本地 GRB XML 檔案並解開 grb_projects 全量專屬欄位條目"""
        if not xml_path.exists():
            raise FileNotFoundError(f"找不到 GRB XML 檔案: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        parsed_items = []
        for idx, elem in enumerate(root):
            if limit > 0 and idx >= limit:
                break

            grb_id = elem.findtext("ID") or f"GRB_UNKNOWN_{idx+1}"
            projkey = elem.findtext("PROJKEY") or f"GRB_PROJ_{idx+1}"
            plan_no = elem.findtext("PLAN_NO") or ""
            title = elem.findtext("PNCH_DESC") or "未命名計畫"
            title_en = elem.findtext("PENG_DESC") or ""
            agency_name = elem.findtext("PLAN_ORGAN_CODE") or "國家科學及技術委員會"
            exec_organ = elem.findtext("EXCU_ORGAN_NAME") or ""
            pi = elem.findtext("PI") or ""
            researcher = elem.findtext("RESEARCHER") or ""
            year_raw = elem.findtext("PLAN_YEAR") or "113"
            
            research_type = elem.findtext("RESEARCH_TYPE") or ""
            research_attribute = elem.findtext("RESEARCH_ATTRIBUTE") or ""
            research_field = elem.findtext("RESEARCH_FIELD") or ""
            period_start = elem.findtext("PERIOD_STYM") or ""
            period_end = elem.findtext("PERIOD_ENYM") or ""
            
            amt_raw = elem.findtext("PLAN_AMT") or "0"
            try:
                plan_amt = int(amt_raw)
            except ValueError:
                plan_amt = 0

            detail_url = elem.findtext("ABSTRACT_C") or elem.findtext("ABSTRACT_E") or f"https://www.grb.gov.tw/search/planDetail2?id={grb_id}"
            keyword_c = elem.findtext("KEYWORD_C") or ""
            keyword_e = elem.findtext("KEYWORD_E") or ""
            abstract_c = elem.findtext("ABSTRACT_C") or ""

            try:
                pub_year = int(year_raw)
            except ValueError:
                pub_year = 113

            # 專屬 report_uid 命名規範
            report_uid = f"GRB_{projkey}" if projkey else f"GRB_{grb_id}"

            parsed_items.append({
                "seq_idx": idx + 1,
                "report_uid": report_uid,
                "grb_id": grb_id.strip(),
                "projkey": projkey.strip(),
                "plan_no": plan_no.strip(),
                "title": title.strip(),
                "title_en": title_en.strip(),
                "pub_year": pub_year,
                "agency_name_raw": agency_name.strip(),
                "exec_organ": exec_organ.strip(),
                "pi": pi.strip(),
                "researchers": researcher.strip(),
                "plan_amt": plan_amt,
                "research_type": research_type.strip(),
                "research_attribute": research_attribute.strip(),
                "research_field": research_field.strip(),
                "period_start": period_start.strip(),
                "period_end": period_end.strip(),
                "keyword_c": keyword_c.strip(),
                "keyword_e": keyword_e.strip(),
                "abstract_c": abstract_c.strip(),
                "remote_url": detail_url.strip(),
                "raw_row": [grb_id, projkey, plan_no, title, agency_name, exec_organ, pi, plan_amt]
            })

        return parsed_items

    def ingest_catalog(self, source_path: str) -> int:
        """實作 BaseReportAdapter 介面：載入全量目錄總表"""
        xml_path = Path(source_path)
        items = self.parse_xml_file(xml_path)
        return len(items)

    def fetch_report(self, report_uid: str, remote_url: str, output_dir: str) -> Dict[str, Any]:
        """實作 BaseReportAdapter 介面：採集實體檔案與詳情頁面"""
        out_path = Path(output_dir) / f"{report_uid}.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(
            remote_url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        try:
            with urllib.request.urlopen(req, context=ssl_context, timeout=15) as resp:
                content = resp.read()
                with open(out_path, 'wb') as f:
                    f.write(content)
                return {
                    "status": "SUCCESS",
                    "local_path": str(out_path),
                    "bytes": len(content)
                }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
