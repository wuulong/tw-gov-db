---
name: gov-db-wizard
description: 專門協助導航、查詢與協同全台灣政府開放資料通用基石 (GOV-300 tw-gov-db) 的專家技能。提供 OID 機關對齊、3+3 碼門牌即時反查、五大基石直連與跨專案 Co-work 導航。
---

# 🏛️ GOV-DB Wizard Skill (台灣政府通用基石導航器)

本技能專門提供 AI Agent 在面對全台灣政府開放資料治理、權威機關 OID 對齊、五大通用基石 (Identity, Spatial, Hydrology, Corporate, Temporal) 與跨專案 Co-work 時的標準導航指引。

---

## 1. 核心查詢與工具呼叫指引

### A. 機關 OID 與發布者別名對齊
當使用者或 Agent 需對齊 data.gov.tw 開放資料發布單位時，請調用 `BaseDomainAdapter`：
```python
from core.domain_registry_resolver import DomainRegistryResolver

resolver = DomainRegistryResolver()
resolver.bootstrap_domain_python_path("GOV-300")
from core.base_adapter import BaseDomainAdapter

adapter = BaseDomainAdapter(root_agency_oid="2.16.886.101")
official_oid = adapter.align_publisher_oid("農業部農糧署")
# 回傳: "2.16.886.101.20003.20064.20070"
```

### B. 3+3 碼 (6碼) 門牌即時線上反查
當需要反查精確門牌投遞區號時，請透過 `opendata_cli.py zipcode` 子命令：
```bash
python scripts/open_data/opendata_cli.py zipcode "臺北市中正區重慶南路一段120號"
# 回傳: 100005
```

### C. 跨專案 Co-work 三層式導航 (`DomainRegistryResolver`)
當需要在母專案 (`GOV-300`) 與子專案 (`GOV-A19` 農業部, `GOV-A13` 內政部) 之間進行協同查詢時：
```python
from core.domain_registry_resolver import DomainRegistryResolver

resolver = DomainRegistryResolver()

# 1. 取得子專案 DB 直連
conn = resolver.get_domain_core_db_connection("GOV-A19", "agro_integrated.sqlite")

# 2. 發動跨專案 CLI 工具
cli_out = resolver.run_domain_cli("GOV-A19", "query-crop", ["--crop", "稻米"])
```

---

## 2. 五大通用基石 (5 Universal Baseline Cornerstones) 檢索速查

1. **基石一 (Identity)**：`master_agencies.sqlite` 7,956 筆 OID 機關 + 708 筆別名。
2. **基石二 (Spatial)**：`universal_keys.sqlite` 480 筆國家行政區劃程式碼 (22縣市+368鄉鎮區)。
3. **基石三 (Hydrology)**：`universal_keys.sqlite` 122 條全國主要水系 + 450 個官方測站。
4. **基石四 (Corporate)**：`universal_keys.sqlite` 1,103 上市/國營 Seed + 23,218 筆 NPO/農會。
5. **基石五 (Temporal)**：`universal_keys.sqlite` 1,199 政府辦公日曆 + `clean_datetime()` ISO-8601 轉碼。
