# 🏛️ tw-gov-db: 全台灣政府開放資料通用基石對照庫 (GOV-300)

[![Version](events-2026Q3/gov-db-in/tw-gov-db/VERSION.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Spec Compliance](https://img.shields.io/badge/SE--6D-100%25%20PASS-brightgreen.svg)](book/00_toc.md)

`tw-gov-db` (代號 **`GOV-300`** / 方案 A 權威行政院機關簡碼 `300000000A`) 是全台灣政府開放資料 (data.gov.tw) 作為語意對照、實體連結與 GraphRAG 零幻覺 Grounding 的**開源通用基石對照庫 (Mother Core Infrastructure)**。

本專案解決跨部會資料孤島、發布單位別名混亂、舊民國年格式偏離標準、巨量體積障礙與缺少空間對照整合鍵 6 大現實痛點，為全台灣政府資料治理與部會子專案 (`GOV-A19` 農業部 `tw-agro-db v0.7.1` 相容對接、`GOV-A13` 內政部、`GOV-A09` 經濟部) 提供統一的語意基石與三層式 Co-work 介面。

---

## 📚 開源技術專書與版本看板

* 📘 **[開源專書圖鑑目錄 (book/00_toc.md)](book/00_toc.md)**：《台灣政府開放資料通用基石圖鑑：從權威機關到跨部會基石的資料治理體系》
* 🏷️ **[版本演進與對接相容性看板 (VERSION.md)](events-2026Q3/gov-db-in/tw-gov-db/VERSION.md)**：記錄 `v0.2.1` 版號變更與 `tw-agro-db v0.7.1` 跨部會對接測試 100% PASS 綠燈相容矩陣。

---

## 🌟 五大通用基石 (5 Universal Baseline Cornerstones)

`tw-gov-db` 凝練全全台灣政府資料運作所必需的 5 大核心對照整合基石：

| 通用基石 | 核心資料庫與表格 | 資料規模與對對能力 | 應用範疇 |
| :--- | :--- | :--- | :--- |
| **基石一：組織與身份** | `master_agencies.sqlite`<br>(`master_agencies`, `publisher_aliases`) | **7,956 筆** 官方 OID 機關<br>**708 筆** data.gov.tw 發布者別名 | 自動將異質字串 (如 "農糧署") 100% 對齊至權威 OID (`2.16.886.101...`) |
| **基石二：空間與地籍** | `universal_keys.sqlite`<br>(`admin_codes`, `cadastral_registry`, `zipcode_registry`) | **480 筆** 6 碼國家標準行政區劃<br>**372 筆** 3 碼本機郵遞區號 (支援 6 碼門牌即時反查) | 提供全台縣市鄉鎮、地籍段號與精確門牌投遞區號 Spatial 定址 |
| **基石三：水系與環境** | `universal_keys.sqlite`<br>(`river_registry`, `station_registry`) | **122 條** 國家水系程式碼<br>**450 個** 中央氣象署/環境部官方測站 | 提供水文流域 (如淡水河 1300) 與 WGS84 氣象/水質監測站點空間碰撞 |
| **基石四：法人與企業** | `universal_keys.sqlite`<br>(`corporate_registry`, `npo_registry`) | **1,103 筆** 熱門 Seed 上市/國營企業<br>**23,218 筆** 登記 NGO/農漁會 | 旁路透傳快取 (Pass-Through Cache) 模式，離線本機 5MB，連線 GCIS API 自動快取 |
| **基石五：時間與時序** | `universal_keys.sqlite`<br>(`calendar_registry`) | **1,199 筆** 2018-2026 政府辦公日曆<br>`clean_datetime()` ISO-8601 轉碼 | 自動清洗民國年 (`113/08/22` ➔ `2024-08-22`) 並對齊例假日與颱風假分類 |

---

## ⚡ 快速開始與 Python API 使用指南

### 1. 安裝與環境準備
```bash
# 複製專案庫
git clone https://github.com/wuulong/tw-gov-db.git
cd tw-gov-db
```

### 2. 機關發布者別名自動對齊
```python
from src.core.domain_registry_resolver import DomainRegistryResolver

resolver = DomainRegistryResolver()
resolver.bootstrap_domain_python_path("GOV-300")
from src.core.base_adapter import BaseDomainAdapter

# 建立 Adapter 並清洗發布者別名
adapter = BaseDomainAdapter(root_agency_oid="2.16.886.101")
official_oid = adapter.align_publisher_oid("農業部農糧署")
print(official_oid)
# 輸出: 2.16.886.101.20003.20064.20070
```

### 3. 三層式跨專案 Co-work 導航 (`DomainRegistryResolver`)
```python
from src.core.domain_registry_resolver import DomainRegistryResolver

resolver = DomainRegistryResolver()

# 1. 取得子專案 DB 實體連線 (如 GOV-A19 農業部)
conn = resolver.get_domain_core_db_connection("GOV-A19", "agro_integrated.sqlite")

# 2. 跨專案呼叫 CLI 工具
cli_output = resolver.run_domain_cli("GOV-300", "zipcode", ["臺北市中正區重慶南路一段120號"])
print(cli_output)
# 輸出: 📮 郵遞區號查詢結果 『臺北市中正區...』: 100005
```

---

## 🏛️ 專案架構目錄

```text
tw-gov-db/
├── README.md                           ◄── 本說明檔案
├── VERSION.md                          ◄── 版本演進與跨專案相容性矩陣 (v0.2.1)
├── domain_map_config.json              ◄── 跨專案領域對照地圖 (軟連結)
├── modules/                            ◄── 子專案範本藍圖專區
│   └── template_blueprint/             ◄── 跨部會子專案複製起步模板 (8 大範本)
├── book/                               ◄── 開源技術專書與圖鑑
│   ├── 00_toc.md                       ◄── 專書完整目錄與章節寫作意圖
│   ├── FULL_BOOK_TAIWAN_GOV_DB.md      ◄── 154KB 全書大一統合訂本
│   └── 04_synergy_contracts/prompts/   ◄── 雙向 Prompt 契約 (PROMPT_TO_SUBMODULE_A19.md)
├── ontology/                           ◄── 資料庫 Schema 與軟連結實體庫
│   ├── datasource_metadata.json        ◄── 資料來源追溯中繼檔 (含 12 大資料集來源)
│   ├── schema.sql                      ◄── 100% 全量實體庫 DDL 腳本
│   ├── master_agencies.sqlite          🔗 權威機關主檔與別名庫
│   └── universal_keys.sqlite           🔗 全政府五大通用基石庫
├── src/                                ◄── Core SDK 核心程式庫
│   ├── bootstrap/                      ◄── 資料匯入與對齊模組
│   └── core/                           ◄── 5 Pillars GovBaseEntity, BaseDomainAdapter, DomainRegistryResolver
├── scripts/                            ◄── CLI 工具與自動化腳本
├── docs/                               ◄── CLI 工具速查手冊
└── tests/                              ◄── 100% PASS 單元與跨部會對接測試套件
```

---

## 🧙‍♂️ Agent 導航技能 (`gov-db-wizard`)

本專案附帶適用於 Google Antigravity / Agentic AI 的專屬導航 Skill，位於 `.agent/skills/gov-db-wizard/SKILL.md`，可引導 AI Agent 自動進行跨部會資料對齊與門牌反查。

---

## 📄 授權條款 (License)

本專案採用 [MIT License](LICENSE) 開源授權，歡迎社群自由使用、擴充與商業衍生。
