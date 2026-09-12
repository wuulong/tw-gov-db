#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOV-A18 (tw-med-db) ↔ GOV-300 (tw-gov-db) 跨部會對接整合測試套件
對齊規格: [SPC-011, SPC-014, G300-REQ-MOHW-01~04]
"""

import sys
import time
import sqlite3
from pathlib import Path

# 動態加載 G300 SDK
g300_src = Path(__file__).resolve().parents[1] / "src"
if str(g300_src) not in sys.path:
    sys.path.insert(0, str(g300_src))

from core.domain_registry_resolver import DomainRegistryResolver

def test_gov_a18_synergy_integration():
    t0 = time.time()
    print("🚀 啟動 GOV-A18 (tw-med-db) ↔ GOV-300 (tw-gov-db) 跨部會對接實測...")
    
    # 1. 階梯 1：初始化 Resolver 並測試 mohw、med、GOV-A18 別名解析
    t_start = time.time()
    print("🔍 [Step 1] 初始化 DomainRegistryResolver 驗證別名 (mohw, med, GOV-A18)...")
    resolver = DomainRegistryResolver()
    
    info_mohw = resolver.get_domain_info("mohw")
    info_med = resolver.get_domain_info("med")
    info_code = resolver.get_domain_info("GOV-A18")
    t_step1 = (time.time() - t_start) * 1000
    
    assert info_mohw["project_code"] == "GOV-A18"
    assert info_med["project_code"] == "GOV-A18"
    assert info_code["project_code"] == "GOV-A18"
    
    print(f"  ├─ 成功解析 mohw ➔ {info_mohw['name']}")
    print(f"  ├─ 成功解析 med  ➔ {info_med['name']}")
    print(f"  ├─ 根機關 OID: {info_mohw['root_oid']}")
    print(f"  └─ 耗時: {t_step1:.3f} ms")
    
    # 2. 階梯 2：基石一 OID 歸併與衛福部/食藥署對齊驗證 (master_agencies.sqlite)
    t_start = time.time()
    print("🔍 [Step 2] 驗證基石一 OID 歸併 (master_agencies.sqlite)...")
    conn_agencies = resolver.get_domain_core_db_connection("GOV-300", "master_agencies.sqlite")
    cur_a = conn_agencies.cursor()
    cur_a.execute("SELECT agency_name, agency_oid FROM master_agencies WHERE agency_name LIKE '%衛生福利部%' LIMIT 1")
    row_a = cur_a.fetchone()
    t_step2 = (time.time() - t_start) * 1000
    
    assert row_a is not None
    print(f"  ├─ 衛福機關名稱成功對齊權威 OID: {row_a[0]} -> {row_a[1]}")
    print(f"  └─ 耗時: {t_step2:.3f} ms")
    conn_agencies.close()
    
    # 3. 階梯 3：直連 MOHW 核心資料庫 (/Volumes/D2024/data/med-db-in/db/med.db)
    t_start = time.time()
    print("🔍 [Step 3] 驗證 G300 直連 MOHW 核心庫 (med.db)...")
    conn_med = resolver.get_domain_core_db_connection("GOV-A18", "med.db")
    cur_m = conn_med.cursor()
    
    # 讀取藥品許可證 m01_tw_drug_db
    cur_m.execute("SELECT count(*) FROM m01_tw_drug_db")
    drug_cnt = cur_m.fetchone()[0]
    
    # 讀取醫院診所機構 m05_hospitals
    cur_m.execute("SELECT count(*) FROM m05_hospitals")
    hosp_cnt = cur_m.fetchone()[0]
    t_step3 = (time.time() - t_start) * 1000
    
    assert drug_cnt >= 60000
    assert hosp_cnt >= 500
    print(f"  ├─ 成功讀取 m01_tw_drug_db 藥品許可證: {drug_cnt:,} 筆")
    print(f"  ├─ 成功讀取 m05_hospitals 醫院診所機構: {hosp_cnt:,} 家")
    print(f"  └─ 耗時: {t_step3:.3f} ms")
    conn_med.close()
    
    # 4. 階梯 4：發動跨專案 CLI 命令調度 (meddb_cli.py status)
    t_start = time.time()
    print("🔍 [Step 4] 驗證跨專案 CLI 發動 (meddb_cli.py status)...")
    output = resolver.run_domain_cli("GOV-A18", "status")
    t_step4 = (time.time() - t_start) * 1000
    assert "M00" in output or "tw-med-db" in output or "狀態" in output
    print(f"  ├─ CLI 輸出摘要: {output[:100]}...")
    print(f"  └─ 耗時: {t_step4:.3f} ms")
        
    total_time = (time.time() - t0) * 1000
    print(f"⏱️ 全套跨部會對接實測總耗時: {total_time:.3f} ms")
    print("✅ GOV-A18 (mohw/med) ↔ GOV-300 跨部會對接驗證 100% 通過！")

if __name__ == "__main__":
    test_gov_a18_synergy_integration()
