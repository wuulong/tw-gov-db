# -*- coding: utf-8 -*-
"""
G10 Core API - 零 sys.exit, 硬性 OID 防線與報告資料庫核心操作
"""

import os
import sqlite3
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
TW_GOV_DB_ROOT = MODULE_DIR.parents[2]

def _resolve_db_path(db_name: str) -> Path:
    """環境變數優先與外接硬碟智慧定址"""
    env_dir = os.environ.get("GOV_DB_SHARED_DIR")
    if env_dir and Path(env_dir).exists():
        return Path(env_dir) / db_name
    ext_dir = Path("/Volumes/D2024/data/gov-db-in/db")
    if ext_dir.exists() and (ext_dir / db_name).exists():
        return ext_dir / db_name
    return TW_GOV_DB_ROOT / "ontology" / db_name

DB_PATH = _resolve_db_path("report_index.sqlite")
MASTER_AGENCY_DB = _resolve_db_path("master_agencies.sqlite")

def init_db(db_file: Path = DB_PATH) -> None:
    """初始化 DGS v2.0 report_index.sqlite 資料表結構"""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # 1. report_index 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report_index (
        report_uid TEXT PRIMARY KEY,
        agency_oid TEXT NOT NULL,
        title TEXT NOT NULL,
        agency_name_raw TEXT,
        pub_year INTEGER,
        authors_or_pi TEXT,
        source_platform TEXT NOT NULL,
        remote_url TEXT,
        fetch_status TEXT DEFAULT 'UNRESOLVED_ONLINE',
        file_format TEXT DEFAULT 'PDF',
        is_cached INTEGER DEFAULT 0,
        local_cache_path TEXT,
        file_sha256 TEXT,
        attributes_json TEXT
    );
    """)

    # 1.1 grb_projects 專用資料表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grb_projects (
        report_uid TEXT PRIMARY KEY,
        grb_id TEXT NOT NULL,
        projkey TEXT NOT NULL,
        plan_no TEXT,
        tender_number TEXT,
        title TEXT NOT NULL,
        title_en TEXT,
        pub_year INTEGER NOT NULL,
        agency_oid TEXT NOT NULL,
        agency_name_raw TEXT,
        exec_organ TEXT,
        vendor_ubn TEXT,
        pi TEXT,
        researchers TEXT,
        plan_amt INTEGER DEFAULT 0,
        research_type TEXT,
        research_attribute TEXT,
        research_field TEXT,
        period_start TEXT,
        period_end TEXT,
        keyword_c TEXT,
        keyword_e TEXT,
        abstract_c TEXT,
        remote_url TEXT,
        is_cached INTEGER DEFAULT 0,
        local_cache_path TEXT,
        attributes_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. sys_namespace_status 看板表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sys_namespace_status (
        namespace_code TEXT PRIMARY KEY,
        namespace_name TEXT NOT NULL,
        has_master_catalog INTEGER DEFAULT 0,
        catalog_ingested INTEGER DEFAULT 0,
        catalog_total_count INTEGER DEFAULT 0,
        auto_download_level TEXT DEFAULT 'NONE',
        last_catalog_sync DATETIME,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 預載預設代號系統狀態
    default_namespaces = [
        ('DATA_GOV', '政府開放資料平台', 1, 0, 0, 'DIRECT_URL'),
        ('GRB', '政府研究資訊系統', 1, 0, 0, 'SCRAPER'),
        ('GPN', '國家圖書館出版品號', 1, 0, 0, 'API'),
        ('USER', '臨時與暫存歸檔', 0, 0, 0, 'STAGING_MANUAL')
    ]
    for ns in default_namespaces:
        cursor.execute("""
            INSERT OR IGNORE INTO sys_namespace_status 
            (namespace_code, namespace_name, has_master_catalog, catalog_ingested, catalog_total_count, auto_download_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ns)

    conn.commit()
    conn.close()

def validate_oid_exists(agency_oid: str, master_db: Path = MASTER_AGENCY_DB) -> bool:
    """防線一：硬性檢查 OID 是否存在於 master_agencies.sqlite 中"""
    if agency_oid == "UNKNOWN_PENDING":
        return True  # 允許暫存區 OID

    if not master_db.exists():
        return True  # 容錯備援
        
    conn = sqlite3.connect(master_db)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM master_agencies WHERE agency_oid = ?", (agency_oid,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise KeyError(f"❌ 硬性防線拒絕：OID [{agency_oid}] 不存在於權威機關主檔！嚴禁隨意發明新 OID。")
    return True

def get_namespace_status(db_file: Path = DB_PATH) -> List[Dict[str, Any]]:
    """取得代號系統能力矩陣清單"""
    init_db(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT namespace_code, namespace_name, has_master_catalog, catalog_ingested, 
               catalog_total_count, auto_download_level, last_catalog_sync 
        FROM sys_namespace_status
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "namespace_code": r[0],
            "namespace_name": r[1],
            "has_master_catalog": r[2],
            "catalog_ingested": r[3],
            "catalog_total_count": r[4],
            "auto_download_level": r[5],
            "last_catalog_sync": r[6]
        })
    return result

def get_catalog_registry(db_file: Path = DB_PATH) -> List[Dict[str, Any]]:
    """取得已註冊之總表追溯地圖清單"""
    init_db(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT catalog_id, namespace_code, agency_oid, catalog_title, source_dataset_id, 
               download_url, file_format, total_items_count, verification_status, last_fetched_at
        FROM sys_master_catalog_registry
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "catalog_id": r[0],
            "namespace_code": r[1],
            "agency_oid": r[2],
            "catalog_title": r[3],
            "source_dataset_id": r[4],
            "download_url": r[5],
            "file_format": r[6],
            "total_items_count": r[7],
            "verification_status": r[8],
            "last_fetched_at": r[9]
        })
    return result

def register_and_ingest_catalog(
    dataset_id: str,
    agency_oid: str,
    title: str,
    download_url: str,
    namespace_code: str = "DATA_GOV",
    db_file: Path = DB_PATH
) -> Dict[str, Any]:
    """核心 API: 註冊總表來源、線上下載剖析並寫入報告條目至 report_index (包含 REJECTED_INVALID 容錯升級)"""
    init_db(db_file)
    validate_oid_exists(agency_oid)

    catalog_key = f"{namespace_code}_{dataset_id}"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 1. 寫入 sys_master_catalog_registry 標註 SUSPECTED
    cursor.execute("""
        INSERT OR REPLACE INTO sys_master_catalog_registry 
        (catalog_id, namespace_code, agency_oid, catalog_title, source_dataset_id, download_url, verification_status)
        VALUES (?, ?, ?, ?, ?, ?, 'SUSPECTED')
    """, (catalog_key, namespace_code, agency_oid, title, dataset_id, download_url))
    conn.commit()

    # 2. 發動 DataGovAdapter 剖析內文
    try:
        from modules.g10_report_miner.adapters.datagov_adapter import DataGovAdapter
        adapter = DataGovAdapter()
        items = adapter.ingest_catalog(download_url)
    except Exception as e:
        # 下載失敗/壞連結，自動標註 REJECTED_INVALID
        cursor.execute("""
            UPDATE sys_master_catalog_registry 
            SET verification_status = 'REJECTED_INVALID',
                last_fetched_at = CURRENT_TIMESTAMP
            WHERE catalog_id = ?
        """, (catalog_key,))
        conn.commit()
        conn.close()
        return {
            "status": "FAILED",
            "catalog_id": catalog_key,
            "verification_status": "REJECTED_INVALID",
            "error": str(e),
            "items_parsed": 0
        }

    # 判斷是否為無效/非報告總表 (如空白項 0 筆)
    if not items or len(items) == 0:
        cursor.execute("""
            UPDATE sys_master_catalog_registry 
            SET verification_status = 'REJECTED_INVALID',
                total_items_count = 0,
                last_fetched_at = CURRENT_TIMESTAMP
            WHERE catalog_id = ?
        """, (catalog_key,))
        conn.commit()
        conn.close()
        return {
            "status": "REJECTED",
            "catalog_id": catalog_key,
            "verification_status": "REJECTED_INVALID",
            "items_parsed": 0
        }

    # 3. 寫入個案報告至 report_index
    inserted_cnt = 0
    for idx, item in enumerate(items):
        report_uid = f"{catalog_key}_{item['seq_idx']:04d}"
        cursor.execute("""
            INSERT OR REPLACE INTO report_index 
            (report_uid, agency_oid, title, pub_year, authors_or_pi, source_platform, remote_url, fetch_status, file_format, attributes_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'UNRESOLVED_ONLINE', 'PDF', ?)
        """, (
            report_uid,
            agency_oid,
            item["title"],
            item["pub_year"],
            item["authors_or_pi"],
            namespace_code,
            item["remote_url"],
            json.dumps({"catalog_source": catalog_key, "raw_row": item["raw_row"]}, ensure_ascii=False)
        ))
        inserted_cnt += 1

    # 4. 升級驗證狀態為 CONFIRMED_VALID
    cursor.execute("""
        UPDATE sys_master_catalog_registry 
        SET verification_status = 'CONFIRMED_VALID',
            total_items_count = ?,
            last_fetched_at = CURRENT_TIMESTAMP
        WHERE catalog_id = ?
    """, (inserted_cnt, catalog_key))

    # 5. 更新 sys_namespace_status
    cursor.execute("""
        UPDATE sys_namespace_status 
        SET catalog_ingested = 1,
            catalog_total_count = (SELECT COUNT(*) FROM report_index),
            last_catalog_sync = CURRENT_TIMESTAMP
        WHERE namespace_code = ?
    """, (namespace_code,))

    conn.commit()
    conn.close()

    return {
        "status": "SUCCESS",
        "catalog_id": catalog_key,
        "verification_status": "CONFIRMED_VALID",
        "items_parsed": inserted_cnt
    }

def ingest_grb_catalog_full(xml_path: Path, db_file: Path = DB_PATH, limit: int = 0) -> Dict[str, Any]:
    """【核心 API】將 GRB XML 全量專屬欄位高效率寫入 grb_projects 獨立資料表"""
    init_db(db_file)
    from .adapters.grb_adapter import GrbAdapter
    
    adapter = GrbAdapter()
    items = adapter.parse_xml_file(xml_path, limit=limit)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    inserted_cnt = 0
    for item in items:
        # 主管機關 OID (預設帶入國科會/中央權威 OID)
        agency_oid = "2.16.886.101.20003.20002"
        
        cursor.execute("""
            INSERT OR REPLACE INTO grb_projects (
                report_uid, grb_id, projkey, plan_no, tender_number,
                title, title_en, pub_year, agency_oid, agency_name_raw,
                exec_organ, pi, researchers, plan_amt, research_type,
                research_attribute, research_field, period_start, period_end,
                keyword_c, keyword_e, abstract_c, remote_url, attributes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["report_uid"], item["grb_id"], item["projkey"], item["plan_no"], item["plan_no"],
            item["title"], item["title_en"], item["pub_year"], agency_oid, item["agency_name_raw"],
            item["exec_organ"], item["pi"], item["researchers"], item["plan_amt"], item["research_type"],
            item["research_attribute"], item["research_field"], item["period_start"], item["period_end"],
            item["keyword_c"], item["keyword_e"], item["abstract_c"], item["remote_url"],
            json.dumps({"raw_row": item["raw_row"]}, ensure_ascii=False)
        ))
        inserted_cnt += 1

    # 更新 sys_namespace_status
    cursor.execute("""
        UPDATE sys_namespace_status 
        SET catalog_ingested = 1,
            catalog_total_count = (SELECT COUNT(*) FROM grb_projects),
            last_catalog_sync = CURRENT_TIMESTAMP
        WHERE namespace_code = 'GRB'
    """)

    conn.commit()
    conn.close()

    return {
        "status": "SUCCESS",
        "inserted_count": inserted_cnt,
        "table_name": "grb_projects"
    }

def batch_ingest_all_grb_years(db_file: Path = DB_PATH) -> Dict[str, Any]:
    """【核心 API】發動全量 GRB 歷年 (82~115 年共 34 個年度包) 智慧下載、解壓與灌庫"""
    import subprocess
    import zipfile
    import io
    import csv

    init_db(db_file)
    catalogs_dir = db_file.parent.parent / "data" / "reports" / "catalogs_cache"
    catalogs_dir.mkdir(parents=True, exist_ok=True)

    # 1. 向國科會獲取全量歷年短網址清單
    res = subprocess.run(
        ["curl", "-s", "-k", "https://mas.nstc.gov.tw/OPENDATA/GetFile?format=csv&serialno=527&fileodr=1"],
        capture_output=True
    )
    content = res.stdout.decode("utf-8-sig", errors="ignore")
    reader = list(csv.reader(io.StringIO(content)))

    if not reader or len(reader) <= 1:
        raise ValueError("無法向國科會獲取歷年 GRB 開放資料清單")

    results = []
    total_inserted = 0

    for row in reader[1:]:
        if len(row) < 3:
            continue
        year_str = row[0].strip()
        year_title = row[1].strip()
        tiny_url = row[2].strip()

        zip_path = catalogs_dir / f"GRB_{year_str}.zip"
        xml_path = catalogs_dir / f"GRB_{year_str}.xml"

        print(f"🔄 發動 GRB 民國 {year_str} 年度資料包處理 [{tiny_url}]...")
        try:
            # 使用 curl 穩定下載
            dl_res = subprocess.run(["curl", "-s", "-L", "-k", tiny_url, "-o", str(zip_path)], check=True)
            
            # 解壓 XML
            with zipfile.ZipFile(zip_path) as z:
                xml_filename = z.namelist()[0]
                with open(xml_path, "wb") as f_out:
                    f_out.write(z.read(xml_filename))

            # 灌庫
            ingest_res = ingest_grb_catalog_full(xml_path, db_file=db_file)
            cnt = ingest_res["inserted_count"]
            total_inserted += cnt
            print(f"  ✅ 民國 {year_str} 年解開寫入 {cnt:,} 筆計畫！")

            # 寫入總表註冊
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sys_master_catalog_registry (
                    catalog_id, namespace_code, agency_oid, catalog_title, source_dataset_id,
                    download_url, file_format, total_items_count, verification_status,
                    local_catalog_path, last_fetched_at
                ) VALUES (?, 'GRB', '2.16.886.101.20003.20002', ?, '18707', ?, 'XML', ?, 'CONFIRMED_VALID', ?, CURRENT_TIMESTAMP)
            """, (f"GRB_{year_str}", year_title, tiny_url, cnt, f"data/reports/catalogs_cache/GRB_{year_str}.xml"))
            conn.commit()
            conn.close()

            results.append({"year": year_str, "status": "SUCCESS", "count": cnt})
        except Exception as e:
            print(f"  ❌ 民國 {year_str} 年處理失敗: {e}")
            results.append({"year": year_str, "status": "FAILED", "error": str(e)})

    return {
        "status": "SUCCESS",
        "total_years_processed": len(results),
        "total_inserted": total_inserted,
        "details": results
    }

def search_grb_projects(kw: str, pi: Optional[str] = None, limit: int = 20, db_file: Path = DB_PATH) -> Dict[str, Any]:
    """【核心 API】多維度智慧檢索 GRB 研究計畫資料庫"""
    init_db(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    sql = """
        SELECT report_uid, projkey, plan_no, title, pub_year, agency_name_raw, exec_organ, pi, plan_amt, remote_url
        FROM grb_projects
        WHERE 1=1
    """
    params = []

    if kw:
        sql += " AND (title LIKE ? OR keyword_c LIKE ? OR abstract_c LIKE ?)"
        kw_p = f"%{kw}%"
        params.extend([kw_p, kw_p, kw_p])

    if pi:
        sql += " AND pi LIKE ?"
        params.append(f"%{pi}%")

    sql += " ORDER BY pub_year DESC, plan_amt DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "report_uid": r[0],
            "projkey": r[1],
            "plan_no": r[2],
            "title": r[3],
            "pub_year": r[4],
            "agency": r[5],
            "exec_organ": r[6],
            "pi": r[7],
            "plan_amt": r[8],
            "remote_url": r[9]
        })

    return {
        "status": "SUCCESS",
        "query_kw": kw,
        "query_pi": pi,
        "total_results": len(results),
        "results": results
    }
    init_db(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 搜尋特定 GRB 報告或包含 query_key 之計畫
    cursor.execute("""
        SELECT report_uid, title, agency_name_raw, pub_year, authors_or_pi, remote_url, attributes_json
        FROM report_index
        WHERE report_uid = ? 
           OR report_uid = ?
           OR title LIKE ?
           OR attributes_json LIKE ?
        LIMIT 1
    """, (query_key, f"GRB_{query_key}", f"%{query_key}%", f"%{query_key}%"))
    
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "status": "NOT_FOUND",
            "query_key": query_key,
            "message": f"找不到與 [{query_key}] 相符之 GRB 報告"
        }

    report_uid, title, agency, pub_year, pi, remote_url, attr_json = row
    attr = json.loads(attr_json) if attr_json else {}
    grb_projkey = attr.get("projkey") or attr.get("grb_id") or report_uid.replace("GRB_", "")

    # 全文可達性三態判斷邏輯
    if remote_url.endswith(".pdf") or remote_url.endswith(".csv"):
        avail_status = "FULLTEXT_DIRECT_PDF"
        avail_desc = "🟢 可直接下載 PDF/CSV 實體檔案"
    elif "grb.gov.tw" in remote_url:
        avail_status = "METADATA_WITH_ABSTRACT"
        avail_desc = "🟡 包含權威中文摘要與詳細資料 (實體 PDF 需透過瀏覽器驗證或國圖轉址)"
    else:
        avail_status = "BIBLIOGRAPHY_PHYSICAL_ONLY"
        avail_desc = "🔴 屬紙本典藏/限閱報告，無直接電子檔 (請至國圖紙本借閱)"

    # 機制 A 對位計算：自動拼裝 GPN 轉址與碰撞條目
    gpn_simulated = f"GPN_MATCH_{grb_projkey}"
    gpn_url = f"https://gpn.ncl.edu.tw/search?kw={grb_projkey}"

    return {
        "status": "MATCHED",
        "query_key": query_key,
        "report_uid": report_uid,
        "title": title,
        "grb_projkey": grb_projkey,
        "agency_name_raw": agency,
        "pub_year": pub_year,
        "availability_status": avail_status,
        "availability_desc": avail_desc,
        "matched_gpn_uid": gpn_simulated,
        "gpn_download_url": gpn_url,
        "mechanism": "MECHANISM_A_PROJKEY_COLLISION"
    }


def batch_probe_untested_catalogs(opendata_db_path: Path = Path("data/open-data/gov_opendata_platform.db"), db_file: Path = DB_PATH) -> Dict[str, Any]:
    """核心 API: 自動探勘全量 Open Data 資料庫中尚未測試的潛力總表，發動批量下載驗證"""
    init_db(db_file)
    
    if not opendata_db_path.exists():
        raise FileNotFoundError(f"找不到開放資料平台資料庫: {opendata_db_path}")

    # 1. 從 open_data_catalog 撈出所有 220 筆精準潛力總表與個案 Dataset
    conn_od = sqlite3.connect(opendata_db_path)
    cursor_od = conn_od.cursor()
    cursor_od.execute("""
        SELECT 資料集識別碼, 資料集名稱, 提供機關, 資料下載網址
        FROM open_data_catalog
        WHERE 檔案格式 LIKE '%CSV%'
          AND (
            (資料集名稱 LIKE '%委託研究%' OR 資料集名稱 LIKE '%研究計畫%' OR 資料集名稱 LIKE '%研究成果%' OR 資料集名稱 LIKE '%出版品%')
            OR (資料集名稱 LIKE '%研究報告%' AND 資料集名稱 NOT LIKE '%會計報告%' AND 資料集名稱 NOT LIKE '%財務報告%')
          )
    """)
    all_candidates = cursor_od.fetchall()
    conn_od.close()

    # 2. 撈出已在 G10 測試/註冊過的 Dataset ID
    conn_g10 = sqlite3.connect(db_file)
    cursor_g10 = conn_g10.cursor()
    cursor_g10.execute("SELECT source_dataset_id FROM sys_master_catalog_registry")
    ingested_ids = set(r[0] for r in cursor_g10.fetchall() if r[0])
    conn_g10.close()

    untested = [c for c in all_candidates if c[0] not in ingested_ids]

    # 3. 嘗試以 publisher_aliases 歸併機關 OID，發動 register_and_ingest_catalog
    success_cnt = 0
    rejected_cnt = 0
    results = []

    conn_master = sqlite3.connect(MASTER_AGENCY_DB)
    cursor_m = conn_master.cursor()

    for item in untested:
        ds_id, title, agency_raw, url_raw = item[0], item[1], item[2], item[3]
        clean_url = url_raw.split(";")[0].strip()

        # 精確查詢機關名稱歸併 OID
        cursor_m.execute("SELECT agency_oid FROM master_agencies WHERE agency_name LIKE '%' || ? || '%' LIMIT 1", (agency_raw[:4],))
        row_m = cursor_m.fetchone()
        agency_oid = row_m[0] if row_m else "UNKNOWN_PENDING"

        res = register_and_ingest_catalog(
            dataset_id=ds_id,
            agency_oid=agency_oid,
            title=title,
            download_url=clean_url
        )
        
        if res["verification_status"] == "CONFIRMED_VALID":
            success_cnt += 1
        else:
            rejected_cnt += 1

        results.append({
            "dataset_id": ds_id,
            "title": title,
            "agency_raw": agency_raw,
            "agency_oid": agency_oid,
            "status": res["verification_status"],
            "items_parsed": res.get("items_parsed", 0)
        })

    conn_master.close()

    return {
        "untested_total": len(untested),
        "confirmed_valid": success_cnt,
        "rejected_invalid": rejected_cnt,
        "details": results
    }


def fetch_report_by_uid(report_uid: str, db_file: Path = DB_PATH) -> Dict[str, Any]:
    """核心 API: 二階段按需採集實體檔案並升級 is_cached 狀態"""
    init_db(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT report_uid, remote_url, title, source_platform FROM report_index WHERE report_uid = ?", (report_uid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise KeyError(f"報告 UID 不存在: {report_uid}")

    uid, remote_url, title, ns_code = row[0], row[1], row[2], row[3]
    if not remote_url:
        raise ValueError(f"該報告無有效遠端下載網址: {title}")

    cache_dir = TW_GOV_DB_ROOT / "data" / "reports" / "cache"
    
    from modules.g10_report_miner.adapters.datagov_adapter import DataGovAdapter
    adapter = DataGovAdapter()
    res = adapter.fetch_report(uid, remote_url, str(cache_dir))

    rel_path = f"data/reports/cache/{os.path.basename(res['file_path'])}"

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE report_index 
        SET is_cached = 1,
            fetch_status = 'DIRECT',
            local_cache_path = ?,
            file_sha256 = ?
        WHERE report_uid = ?
    """, (rel_path, res["file_sha256"], uid))
    conn.commit()
    conn.close()

    res["report_uid"] = uid
    res["title"] = title
    res["local_cache_path"] = rel_path
    return res

def get_db_summary(db_file: Path = DB_PATH) -> Dict[str, Any]:
    """取得 report_index.sqlite 資料庫物件與筆數統計"""
    init_db(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM report_index;")
    total_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM report_index WHERE is_cached = 1;")
    cached_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM report_index WHERE agency_oid = 'UNKNOWN_PENDING';")
    staged_reports = cursor.fetchone()[0]

    conn.close()

    return {
        "total_reports": total_reports,
        "cached_reports": cached_reports,
        "staged_reports": staged_reports,
        "namespace_status": get_namespace_status(db_file)
    }

