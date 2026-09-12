# -*- coding: utf-8 -*-
"""
G10 DataGovAdapter (Data.gov.tw 直連與總表剖析適配器)
自動化等級: DIRECT_URL
"""

import os
import ssl
import csv
import io
import json
import urllib.request
import hashlib
from typing import Dict, Any, List
from .base_adapter import BaseReportAdapter

ssl_context = ssl._create_unverified_context()

class DataGovAdapter(BaseReportAdapter):
    """Data.gov.tw 直連採集與總表剖析適配器 (支援 UTF-8 與 Big5 / CP950 自動容錯備援)"""

    def ingest_catalog(self, download_url: str) -> List[Dict[str, Any]]:
        """線上下載並剖析 Data.gov.tw 總表 CSV 內容"""
        req = urllib.request.Request(
            download_url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as resp:
            raw_bytes = resp.read()

        # 雙軌編碼嘗試: 先試 utf-8-sig，若失敗/亂碼自動切換至 cp950 (Big5)
        try:
            content = raw_bytes.decode('utf-8-sig')
            reader = list(csv.reader(io.StringIO(content)))
            if reader and len(reader) > 0 and len(reader[0]) > 0 and '' in reader[0][0]:
                content = raw_bytes.decode('cp950', errors='ignore')
                reader = list(csv.reader(io.StringIO(content)))
        except UnicodeDecodeError:
            content = raw_bytes.decode('cp950', errors='ignore')
            reader = list(csv.reader(io.StringIO(content)))

        if not reader:
            return []

        header = reader[0]
        # 若剖析出的 rows 只有 1 筆，或包含 header 但只有 1 列資料，亦即「個案計畫專用 Dataset」
        if not rows and len(header) >= 2:
            rows = [header]  # 降級無標頭處理

        parsed_items = []
        for idx, r in enumerate(rows):
            if not r or len(r) < 1:
                continue
            
            # 尋找 90~115 之間的年份數字與標題欄位
            pub_year = 110
            title = ""
            pi_or_dept = ""
            pdf_url = ""

            # 智慧剖析：如果 r[0] 是項號 1, 2, 3，則 r[1] 可能是年份，r[2] 是標題
            cell_0 = r[0].strip()
            cell_1 = r[1].strip() if len(r) > 1 else ""
            cell_2 = r[2].strip() if len(r) > 2 else ""

            if cell_0.isdigit() and int(cell_0) < 50: # r[0] 是項次 (1~50)
                if cell_1.isdigit() and 80 <= int(cell_1) <= 120:
                    pub_year = int(cell_1)
                    title = cell_2
                else:
                    title = cell_1
            elif cell_0.isdigit() and 80 <= int(cell_0) <= 120: # r[0] 剛好是民國年份 (如 110)
                pub_year = int(cell_0)
                title = cell_1
            else:
                title = cell_0

            if not title:
                title = "未命名計畫"

            for cell in reversed(r):
                if cell.strip().startswith("http"):
                    pdf_url = cell.strip()
                    break

            if not pdf_url and download_url.startswith("http"):
                pdf_url = download_url

            parsed_items.append({
                "seq_idx": idx + 1,
                "title": title,
                "pub_year": pub_year,
                "authors_or_pi": pi_or_dept,
                "unit": "",
                "remote_url": pdf_url,
                "raw_row": r[:6]
            })

        return parsed_items

    def fetch_report(self, report_uid: str, remote_url: str, output_dir: str) -> Dict[str, Any]:
        """直連下載資源實體檔案"""
        if not remote_url or not remote_url.startswith("http"):
            raise ValueError(f"無效的 URL: {remote_url}")

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{report_uid}.bin"
        if "pdf" in remote_url.lower():
            filename = f"{report_uid}.pdf"
        elif "csv" in remote_url.lower():
            filename = f"{report_uid}.csv"
        elif "id=" in remote_url.lower() or "planDetail" in remote_url.lower():
            filename = f"{report_uid}.html"

        target_path = os.path.join(output_dir, filename)
        
        req = urllib.request.Request(
            remote_url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=20) as response, open(target_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
            sha256 = hashlib.sha256(data).hexdigest()

        return {
            "status": "DIRECT",
            "file_path": target_path,
            "file_sha256": sha256,
            "bytes_downloaded": len(data)
        }
