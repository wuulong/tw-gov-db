#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
GOV-AXX 子模組對接整合測試套件範本 (拒絕空洞 Dummy 測試，與 Spec 強烈 Grounding 對齊)
對齊規格: [SPC-011, SPC-014]
"""

import sys
from pathlib import Path

# 動態加載 SDK
gov_src = Path(__file__).resolve().parents[2] / "src"
if str(gov_src) not in sys.path:
    sys.path.insert(0, str(gov_src))

from core.domain_registry_resolver import DomainRegistryResolver
from core.base_adapter import BaseDomainAdapter

def test_axx_template_spec_grounded_integration():
    resolver = DomainRegistryResolver()
    
    # 1. 階梯 1：三層連線驗證/Assert
    gov_info = resolver.get_domain_info("GOV-300")
    assert gov_info["project_code"] == "GOV-300"
    
    # 2. 階梯 2：基石一 OID 歸併驗證/Assert (實體權威 OID 存在)
    master_db_path = resolver.get_shared_db_path("master_agencies.sqlite")
    adapter = BaseDomainAdapter(root_agency_oid="2.16.886.101", master_db=master_db_path)
    aligned_oid = adapter.align_publisher_oid("行政院")
    assert aligned_oid != ""
    
    # 3. 階梯 3：基石二門牌地碼驗證/Assert (6 碼 admin_code 存在)
    conn_keys = resolver.get_domain_core_db_connection("GOV-300", "universal_keys.sqlite")
    cursor = conn_keys.cursor()
    cursor.execute("SELECT admin_code FROM admin_codes WHERE city_name='臺北市' AND district_name='中正區';")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "630001"
    conn_keys.close()
    
    print("✅ GOV-AXX 模板與 Spec 強對照整合之測試通過！")

if __name__ == "__main__":
    test_axx_template_spec_grounded_integration()
