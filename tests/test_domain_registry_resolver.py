#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
測試跨專案 DomainRegistryResolver 是否能正確地從硬碟與本地配置中定位 tw-gov-db 與 tw-agro-db
"""

import sys
from pathlib import Path

# 加入 tw-gov-db/src 至路徑
gov_src = Path(__file__).resolve().parents[1] / "src"
if str(gov_src) not in sys.path:
    sys.path.insert(0, str(gov_src))

from core.domain_registry_resolver import DomainRegistryResolver

def test_domain_map_resolution():
    resolver = DomainRegistryResolver()
    
    # 1. 驗證讀取母專案 (支援代號 GOV-300 或 tw-gov-db)
    gov_info = resolver.get_domain_info("GOV-300")
    print("✅ 母專案 GOV-300 (tw-gov-db) 官方簡碼定位成功:")
    print(f"   - Project Code: {gov_info['project_code']}")
    print(f"   - Official Org Code: {gov_info['official_org_code']}")
    print(f"   - Role: {gov_info['role']}")
    print(f"   - Repo Path: {gov_info['local_repo_path']}")
    
    # 2. 驗證讀取子專案 (支援代號 GOV-A19 或 tw-agro-db)
    agro_info = resolver.get_domain_info("GOV-A19")
    print("✅ 子專案 GOV-A19 (tw-agro-db) 官方簡碼定位成功:")
    print(f"   - Project Code: {agro_info['project_code']}")
    print(f"   - Official Org Code: {agro_info['official_org_code']}")
    print(f"   - Parent Code: {agro_info['parent_code']}")
    print(f"   - Role: {agro_info['role']}")
    print(f"   - Root OID: {agro_info['root_oid']}")

    # 3. 驗證共用 DB 路徑
    master_db = resolver.get_shared_db_path("master_agencies.sqlite")
    print(f"✅ 共享 DB 實體路徑: {master_db} (Exists: {master_db.exists()})")

    # 4. 測試跨專案 CLI 工具呼叫與 Library 引用
    resolver.bootstrap_domain_python_path("tw-gov-db")
    from core.base_adapter import BaseDomainAdapter
    print("✅ [Library 層引用] 成功載入 Core SDK BaseDomainAdapter 類別!")

    cli_out = resolver.run_domain_cli("tw-gov-db", "search", ["水利署", "-q"])
    print("✅ [CLI Co-work] 成功跨專案呼叫 tw-gov-db govdb_cli.py!")
    print(f"   - CLI 回傳結果摘要: {cli_out.splitlines()[0]}")

    # 5. 測試核心整合 DB 連線
    conn = resolver.get_domain_core_db_connection("tw-gov-db", "universal_keys.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM admin_codes;")
    print(f"✅ [Core DB 整合] 成功取得 tw-gov-db 核心 DB 連線！admin_codes 筆數: {cursor.fetchone()[0]} 筆")
    conn.close()

if __name__ == "__main__":
    test_domain_map_resolution()
