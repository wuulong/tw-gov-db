# 📝 `tw-gov-db` (代號 `GOV-300`) 核心資產與架構整理清冊 (v0.2)

* **專案名稱**：`tw-gov-db` (全政府權威機關與通用基石對照庫)
* **專案代號 (Project Code)**：`GOV-300` (方案 A 權威行政院機關程式碼 `300000000A`)
* **專案角色**：`MOTHER_CORE` (全政府資料治理總母專案)
* **受控版本號**：`v0.2`
* **根路徑**：`events-2026Q3/gov-db-in/tw-gov-db/`
* **更新日期**：2026-08-22

---

## 🏛️ 1. `tw-gov-db` (GOV-300) 核心目錄與檔案架構

```text
tw-gov-db/
├── domain_map_config.json              ◄── 跨專案領域地圖 (軟連結至 /Volumes/D2024/data/gov-db-in/)
├── ontology/                           ◄── 實體資料庫與 Metadata 區 (受控版號 v0.2)
│   ├── datasource_metadata.json        ◄── 資料來源追溯中繼檔 (含 12 大資料集來源)
│   ├── schema.sql                      ◄── 100% 全量實體庫 DDL 腳本
│   ├── master_agencies.sqlite          🔗 軟連結至 /Volumes/D2024/data/gov-db-in/db/ (7,956 筆 OID)
│   └── universal_keys.sqlite           🔗 軟連結至 /Volumes/D2024/data/gov-db-in/db/ (2.3萬 NPO, 480 行政區)
├── src/                                ◄── Core SDK 核心程式庫
│   └── core/
│       ├── gov_base_entity.py          ◄── 5 Pillars GovBaseEntity 基底類別 (預設 spec_version="0.2")
│       ├── base_adapter.py             ◄── 全政府 BaseDomainAdapter 抽象基底類別
│       ├── virtual_and_cache_managers.py◄── VirtualLawAdapter & CorporateCacheManager
│       └── domain_registry_resolver.py ◄── 三層式 Co-work 導航解析器 (支援 GOV-300, GOV-A19 等)
├── scripts/                            ◄── ETL 匯入與管理 CLI 工具
│   ├── init_universal_keys.py          ◄── 通用基石庫全量資料寫入腳本
│   ├── govdb_cli.py          ◄── 權威機關 OID 與別名查詢 CLI
│   └── universal_keys_ingester.py      ◄── 基石資料入庫轉換器
├── docs/                               ◄── CLI 手冊與檔案
│   └── manuals/govdb_cli.md
└── tests/                              ◄── 100% 合規自動化單元測試套件
    ├── test_five_pillars.py            ◄── 五大基石校驗測試 (PASS 4/4)
    └── test_domain_registry_resolver.py ◄── 跨專案 CLI/DB/Library 導航測試 (PASS)
```

---

## 📊 2. 資料庫與資料規模總覽 (Database Inventory)

1. **`master_agencies.sqlite` (權威機關庫 - 7.5 MB)**：
   - `master_agencies`: **7,956 筆** 官方 OID 權威機關（含行政院及各部會層級）。
   - `publisher_aliases`: **708 筆** data.gov.tw 開放資料發布單位別名對齊表。
2. **`universal_keys.sqlite` (通用基石庫 - 12 MB)**：
   - `npo_registry`: **23,218 筆** 全國依法登記 NGO、社團法人與 342 家農漁會。
   - `calendar_registry`: **1,199 筆** 2018-2026 行政院人事行政總處政府辦公日曆。
   - `corporate_registry`: **1,103 筆** 證交所全量上市公司與國營事業權威 Seed 快取。
   - `admin_codes`: **480 筆** 全台 22 縣市 + 368 鄉鎮市區國家標準行政區劃程式碼。
   - `station_registry`: **450 個** 官方氣象與水文監測站點。
   - `zipcode_registry`: **372 筆** 全台行政區 3 碼郵遞區號。
   - `river_registry`: **122 條** 全國主要水系與流域程式碼。
   - `cadastral_registry`: **22 筆** MOI 全國縣市地籍段號預備開口。

---

## 🚀 3. 版本號統一對齊 (Version v0.2 Verification)

- **SDK 基底類別 (`gov_base_entity.py`)**：`spec_version: str = "0.2"`
- **資料來源中繼檔 (`datasource_metadata.json`)**：`"spec_version": "0.2"`
- **單元測試套件 (`test_five_pillars.py`)**：`self.assertEqual(crop.spec_version, "0.2")` 🟢 PASS
- **系統工程規範 (`spec_functional.md`, `spec_gov_300.md`)**：`version: "0.2"`
