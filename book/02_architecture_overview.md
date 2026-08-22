# 🏛️ 第 2 章：GOV-300 母大腦全景架構、系統中繼與通用基石解構 (02_architecture_overview.md)

* **專案名稱**：`tw-gov-db` (台灣政府開放資料通用基石對照庫)
* **專案代號**：`GOV-300` (方案 A 權威機關簡碼 `300000000A`)
* **當前版本**：`v0.2.1`
* **歸檔路徑**：`events-2026Q3/gov-db-in/tw-gov-db/book/02_architecture_overview.md`

---

## 🏗️ 2.0 全章技術導覽與 4 層架構堆疊

為了徹底解決第 1 章提出的 8 大真實血淚痛點（資料孤島、發布單位別名混亂、民國年陷阱、缺乏診斷工具鏈、缺乏歷史改制脈絡與空間脫鉤等），`tw-gov-db` (`GOV-300`) 採用了現代系統工程中的 **「分散式分層協同架構 (Federated Multi-Tier Architecture)」**。

整個母大腦底座與系統生態系分為以下 4 大核心堆疊層：

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   GOV-300 4 層分層技術堆疊總覽                           │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 4: 應用與聯防層 (Applications & Cross-Domain Synergy)            │
│   - 部會領域子專案: GOV-A19 (農業部), GOV-A13 (內政部), GOV-A09 (經濟部)   │
│   - AI Agent / GraphRAG 零幻覺 Grounding / QGIS 軟體定義地圖 (SDM)      │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 3: 工具鏈與介面層 (Core SDK, CLI & Agent Wizard)                │
│   - Core SDK: GovBaseEntity, BaseDomainAdapter, DomainRegistryResolver  │
│   - CLI 工具: opendata_cli.py (門牌/Zipcode 反查), master_agencies_cli.py  │
│   - Agent 技能: gov-db-wizard ( Antigravity Agentic Skill)             │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 2: 通用基石與權威中繼層 (Baseline Cornerstones & Master Registry)│
│   - master_agencies.sqlite: 7,956 OID 機關主檔 + 708 發布別名 + 子專案註冊│
│   - universal_keys.sqlite: 5 大通用基石 (行政區劃/地籍/水系/企業/日曆)    │
│   - Schema.org / schema.gov.tw 語意對齊與 JSON-LD 物件化               │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 1: 原始資產與快照層 (Raw Assets & External Services)              │
│   - 政府 OID 中心 / 全國法規庫 / data.gov.tw CKAN Catalog              │
│   - 虛擬層 (law_db MCP / PostgreSQL 0MB) & 企業旁路快取 (GCIS API 5MB) │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 2.1 五大通用基石 (5 Baseline Cornerstones) 語意標準與 Schema.org 對齊

全台灣政府開放資料要在 SQL 資料庫中實現 `JOIN` 直連，並支援 LLM / GraphRAG 的無幻覺檢索，關鍵在於將散落的欄位歸併至 **5 大通用基石 (5 Universal Baseline Cornerstones)**。`GOV-300` 完整對齊數位發展部/國發會推動之 `schema.gov.tw` 與國際通用 `Schema.org` 語意模型：

```text
┌────────────────────────────────────────────────────────────────────────┐
│               GOV-300 五大通用基石與 Schema.org 語意對照表              │
├──────────────────┬──────────────────────┬──────────────────────────────┤
│ 通用基石          │ Schema.org 映射實體  │ 實體資料庫與標準對照整合鍵        │
├──────────────────┼──────────────────────┼──────────────────────────────┤
│ 基石一：組織與身份│ GovernmentOrganization│ master_agencies.sqlite       │
│                  │ (Organization)       │ - agency_oid (權威 OID)      │
│                  │                      │ - publisher_aliases (708別名)│
├──────────────────┼──────────────────────┼──────────────────────────────┤
│ 基石二：空間與地籍│ Place / GeoCoordinates│ universal_keys.sqlite        │
│                  │                      │ - admin_code (480 行政區劃)  │
│                  │                      │ - cadastral_id (全國地籍段號)│
│                  │                      │ - zipcode (3+3 精確門牌區號) │
├──────────────────┼──────────────────────┼──────────────────────────────┤
│ 基石三：水系與環境│ BodyOfWater /        │ universal_keys.sqlite        │
│                  │ Observation          │ - river_id (122 國家水系程式碼)│
│                  │                      │ - station_id (450 氣象/水質站)│
├──────────────────┼──────────────────────┼──────────────────────────────┤
│ 基石四：法人與企業│ Corporation /        │ universal_keys.sqlite        │
│                  │ NGO                  │ - tax_id (8碼企業統一編號)   │
│                  │                      │ - npo_registry (2.3萬農會/NPO)│
├──────────────────┼──────────────────────┼──────────────────────────────┤
│ 基石五：時間與時序│ DateTime /           │ universal_keys.sqlite        │
│                  │ Event                │ - calendar_registry (辦公日曆│
│                  │                      │ - clean_datetime (ISO-8601)  │
└──────────────────┴──────────────────────┴──────────────────────────────┘
```

1. **基石一：組織與身份 (Identity & Organization)**
   - 映射至 `Schema.org/GovernmentOrganization`。將全台 7,956 筆官方機關以樹狀 OID (`parent_oid`) 串聯，並透過 `publisher_aliases` 別名庫將異質名稱（如「農糧署」）100% 歸併至權威 OID。
2. **基石二：空間與地籍 (Spatial & Cadastral)**
   - 映射至 `Schema.org/Place` 與 `GeoCoordinates` (`epsg: 4326`)。提供 480 筆 6 碼國家標準行政區劃程式碼、全國地籍段名段號正則化 `cadastral_id`，以及 3+3 碼精確門牌郵遞區號反查。
3. **基石三：水系與環境 (Hydrology & Environment)**
   - 映射至 `Schema.org/BodyOfWater` 與 `Observation`。納入 122 條國家水系程式碼 (`river_id`) 與 450 個中央氣象署/環境部官方監測站 (`station_id`)，實現水文流域與氣象寒害空間碰撞。
4. **基石四：法人與企業 (Corporate & NPO)**
   - 映射至 `Schema.org/Corporation` 與 `NGO`。收錄 1,103 筆熱門 Seed 上市/國營企業與 2.3 萬筆農漁會/NPO 組織，支援 8 碼統一編號 (`tax_id`) 精確對照整合。
5. **基石五：時間與時序 (Temporal & Calendar)**
   - 映射至 `Schema.org/DateTime`。收錄 1,199 筆政府辦公日曆與颱風假分類，內建 `clean_datetime()` 自動將五大民國年文字格式轉換為 ISO-8601 UTC/CST 字串 (`2024-08-22T00:00:00+08:00`)。

---

## 🏷️ 2.2 子專案方案 A 權威命名規範 (Option A Naming Taxonomy: `GOV-[CODE]`)

在跨部會分散式架構中，命名混亂會直接導致專案管理與設定檔崩潰。`GOV-300` 嚴格採用 **方案 A 權威命名規範 (Option A Taxonomy)**：

$$\text{Domain Taxonomy} = \text{Prefix (GOV)} + \text{行政院部會權威程式碼 (CODE)}$$

```text
┌────────────────────────────────────────────────────────────────────────┐
│              方案 A 權威命名規範與跨專案對照地圖 (`domain_map_config.json`) │
├────────────┬─────────────────────────────┬────────────────────────────┤
│ 專案簡碼   │ 行政院官方單位全稱           │ 專案相對路徑 (repo_path)   │
├────────────┼─────────────────────────────┼────────────────────────────┤
│ GOV-300    │ 行政院母專案 (tw-gov-db)     │ events-2026Q3/gov-db-in    │
│ GOV-A19    │ 農業部 (tw-agro-db)         │ events-2026Q3/agro-db-in   │
│ GOV-A13    │ 內政部 (tw-moi-db)          │ events-2026Q3/moi-db-in    │
│ GOV-A09    │ 經濟部 (tw-moea-db)         │ events-2026Q3/moea-db-in   │
└────────────┴─────────────────────────────┴────────────────────────────┘
```

跨專案對照地圖 [`domain_map_config.json`](../domain_map_config.json) 採用軟連結 (Symlink) 共享於各子專案根目錄，使 Core SDK 中的 `DomainRegistryResolver` 能在 1 毫秒內定位任何部會子專案的實體路徑與 DB 連線。

---

## 📋 2.3 Sys Meta、修訂履歷追溯與原始資料源反饋機制 (`[SPC-006, SPC-013]`)

為了擺脫「黑箱清洗」與「洗完不知道原本長怎樣」的弊端，`GOV-300` 在所有核心實體表 (`master_agencies`, `publisher_aliases`, `domain_deployments`) 中均設計了半結構化的 **`attributes_json`** 欄位，嚴格遵從 `[SPC-006]` 與 `[SPC-013]` 治理規範：

### 1. `attributes_json` 動態屬性與 Sys Meta 規格
`attributes_json` 欄位包含系統層受控版號 (DPRV 規範 `spec_version: "0.2"`)、機關英文全稱、DN (Distinguished Name) 屬性與非結構化擴充標籤。

### 2. `history_trail` 修訂履歷與進度追溯陣列
所有經歷清洗與修正的資料列，必須記錄修訂細節（**修到哪邊、修了什麼、套用了什麼規則**）：

```json
{
  "spec_version": "0.2",
  "history_trail": [
    {
      "timestamp": "2026-08-22T14:38:00+08:00",
      "field": "date_raw",
      "original_val": "113/08/22",
      "cleaned_val": "2024-08-22T00:00:00+08:00",
      "rule_applied": "BaseDomainAdapter.clean_datetime"
    },
    {
      "timestamp": "2026-08-22T14:38:05+08:00",
      "field": "publisher_raw",
      "original_val": "農糧署",
      "cleaned_val": "2.16.886.101.20003.20064.20070",
      "rule_applied": "BaseDomainAdapter.align_publisher_oid"
    }
  ]
}
```

### 3. 原始資料源追溯與 `data_correction_feedback.json` 修正反饋
- **原始資料源鎖定 (Source Provenance)**：所有資料實體均追溯至 `ontology/datasource_metadata.json` 中紀錄的原始 Dataset ID、下載 URL、歷史快照 Sha256 雜湊碼。
- **源頭修正反饋報告 (Feedback Loop)**：系統提供 `export_data_feedback()` 介面，自動將比對失敗的別名 (`unmatched_aliases`) 或無效點位，匯出為標準 `data_correction_feedback.json` 反饋報告，可直接提供給原資料發布機關 (data.gov.tw / 政府部會) 進行源頭修正。

---

## ⚡ 2.4 雙軌瘦身架構 (Dual Optimization Architecture)

為了解決痛點 7（巨量 CSV 全量載入與 DB 儲存膨脹），`GOV-300` 研發了 **雙軌瘦身架構 (Dual Optimization Architecture)**，將本機 SQLite 體積從傳統 180MB 以上精簡至僅 **5MB**：

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   GOV-300 雙軌瘦身架構 (Dual Optimization)             │
├────────────────────────────────────────────────────────────────────────┤
│ 1. 法規條文虛擬層 (Virtual Law Layer)                                  │
│    - 實體表 agency_mandates 僅保留 DDL 與結構                          │
│    - 本機 0MB 空間開銷                                                 │
│    - 查詢時由 VirtualLawAdapter 透過 law_cli.py 虛擬檢索 PostgreSQL/ law_db│
├────────────────────────────────────────────────────────────────────────┤
│ 2. 企業統編旁路快取 (Pass-Through Cache)                               │
│    - 本機僅預載 1,103 筆熱門 Seed 上市/國營企業                         │
│    - Cache Hit (命中): 1 毫秒本機 SQLite 快速傳回                         │
│    - Cache Miss (未命中): 自動發動旁路透傳連線 GCIS API 抓取並寫回本機 DB  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 2.5 三層式跨專案 Co-work 協作模式 (`DomainRegistryResolver`)

`GOV-300` 透過 Core SDK 中的 [`DomainRegistryResolver`](../src/core/domain_registry_resolver.py)，為母專案與部會子專案提供三個層級的雙向無縫連線：

1. **CLI 工具層連動 (`run_domain_cli`)**：提供跨專案命令列調用介面，支援直接發動 `opendata_cli.py` 或子專案 CLI（如 `agro_cli.py`）之指令與參數。
2. **Core DB 實體直連層 (`get_domain_core_db_connection`)**：提供資料庫定址介面，免去硬編寫實體路徑，直接傳回 `master_agencies.sqlite` 或子專案核心 DB (`agro_integrated.sqlite`) 之 `sqlite3.Connection`。
3. **Library 免安裝動態注入層 (`bootstrap_domain_python_path`)**：提供免 `pip install` 的套件動態注入機制，將目標領域之 `src` 注入 `sys.path`，實現跨專案 Core SDK 動態加載。

---

## 🧰 2.6 GOV-300 核心函式庫與核心支援功能全景概覽 (Core SDK & Infrastructure Services)

`tw-gov-db` 提供全套標準 Python Core SDK，位於 `src/core/` 目錄，為全系統與所有子專案提供基礎支撐：

```text
src/core/
├── gov_base_entity.py                ◄── 1. GovBaseEntity (基底實體類別)
├── base_adapter.py                   ◄── 2. BaseDomainAdapter (領域適配器基底)
├── domain_registry_resolver.py       ◄── 3. DomainRegistryResolver (跨專案導航器)
└── virtual_and_cache_managers.py     ◄── 4. VirtualLawAdapter & CorporateCacheManager
```

### 1. `GovBaseEntity` (基底實體類別)
- **檔案位址**：[`src/core/gov_base_entity.py`](../src/core/gov_base_entity.py)
- **核心功能**：所有子專案實體之基底。內建 `spec_version: "0.2"` 受控版號驗證、`attributes_json` 透明讀寫、民國年轉 ISO-8601 時間清洗，以及 **`to_jsonld()` Schema.org JSON-LD 物件化轉換**。

### 2. `BaseDomainAdapter` (領域適配器基底)
- **檔案位址**：[`src/core/base_adapter.py`](../src/core/base_adapter.py)
- **核心功能**：規範 Adapter 之 `extract()` ➔ `normalize()` ➔ `enrich()` ➔ `export()` 生命週期。內建 `align_publisher_oid()` 發布者別名歸併與 `clean_datetime()` 異質時間轉換介面。

### 3. `DomainRegistryResolver` (跨專案導航解析器)
- **檔案位址**：[`src/core/domain_registry_resolver.py`](../src/core/domain_registry_resolver.py)
- **核心功能**：解析 `domain_map_config.json`，提供 CLI 連線、DB 直連與 Library 動態注入三層式 Co-work 支援。

### 4. `VirtualLawAdapter` & `CorporateCacheManager` (虛擬與旁路快取適配器)
- **檔案位址**：[`src/core/virtual_and_cache_managers.py`](../src/core/virtual_and_cache_managers.py)
- **核心功能**：實現法規處務規程 0MB 虛擬化查詢與 160 萬公司統編 GCIS API 旁路快取寫回機制。
