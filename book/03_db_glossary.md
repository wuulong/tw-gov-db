# 🏛️ 第 3 章：GOV-300 核心資料庫與 12 大實體表圖鑑百科 (03_db_glossary.md)

* **專案名稱**：`tw-gov-db` (台灣政府開放資料通用基石對照庫)
* **專案代號**：`GOV-300` (方案 A 權威機關簡碼 `300000000A`)
* **當前版本**：`v0.2.1`
* **歸檔路徑**：`events-2026Q3/gov-db-in/tw-gov-db/book/03_db_glossary.md`

---

## 🗺️ 3.0 12 大實體表總覽與雙資料庫關聯圖 (ERD)

`tw-gov-db` (`GOV-300`) 採用實體分庫與關聯對照整合設計。全系統共包含 **12 大核心實體資料表**，分別存放於 `master_agencies.sqlite` (4 張表) 與 `universal_keys.sqlite` (8 張表) 兩個 SQLite 檔案中，其實體 DDL 總藍圖集中管理於 [`ontology/schema.sql`](../ontology/schema.sql)：

```mermaid
erDiagram
    %% Part A: master_agencies.sqlite
    master_agencies ||--o{ master_agencies : "parent_oid (組織樹)"
    master_agencies ||--o{ agency_mandates : "agency_oid (虛擬法規)"
    master_agencies ||--o{ publisher_aliases : "mapped_agency_oid (708別名)"
    master_agencies ||--o{ domain_deployments : "root_agency_oid (子專案)"

    %% Part B: universal_keys.sqlite
    admin_codes ||--o{ cadastral_registry : "admin_code (行政區劃)"
    admin_codes ||--o{ zipcode_registry : "admin_code (郵遞區號)"
    admin_codes ||--o{ npo_registry : "admin_code (農會/NPO)"
    river_registry ||--o{ station_registry : "river_id (水文氣象)"
    admin_codes ||--o{ corporate_registry : "admin_code (企業地緣)"

    master_agencies {
        string agency_oid PK "2.16.886.101..."
        string org_code "313000000G"
        string agency_name "機關全稱"
        string parent_oid FK "上級 OID"
        text attributes_json "Sys Meta / 版號"
    }

    publisher_aliases {
        int alias_id PK
        string raw_publisher_name UK "data.gov.tw 原始發布名"
        string mapped_agency_oid FK "權威 OID"
        float confidence_score "1.0 / 0.9 / 0.8"
    }

    admin_codes {
        string admin_code PK "630000 臺北市"
        string city_name "臺北市"
        string district_name "中正區"
    }

    corporate_registry {
        string tax_id PK "8 碼統一編號"
        string company_name "企業名稱"
        string registered_address "營業地址"
        string admin_code FK "行政區劃"
    }
```

---

## 🏛️ Part A: `master_agencies.sqlite` 權威機關與領域註冊庫 (4 大實體表)

### 3.1 機關權威主檔表 (`master_agencies`)
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄全台灣 **7,956 筆** 官方權威 OID 組織樹，作為全政府機關身份的「單一真實來源 (Single Source of Truth)」。為所有開放資料集的發布者提供不可變、不重複的權威實體編號。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `publisher_aliases` 連結**：被 `publisher_aliases.mapped_agency_oid` 引用。將發布單位別名（如「農糧署」）向上對齊歸併至本表的權威 OID。
  - **與 `domain_deployments` 連結**：被 `domain_deployments.root_agency_oid` 引用。作為部會子專案（如 `GOV-A19` 農業部 `2.16.886.101.20003.20064`）的領域根節點。
  - **跨部會 DB 直連 (如 `tw-agro-db`)**：子專案中的資料集（如農藥登記表）強制以本表的 `agency_oid` 標註主管權責機關。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE master_agencies (
      agency_oid VARCHAR(128) PRIMARY KEY, -- 政府 OID (如 2.16.886.101.20003.20007)
      org_code VARCHAR(32),                -- 行政院機關程式碼 (如 313000000G)
      agency_name VARCHAR(128) NOT NULL,   -- 官方全稱 (如 經濟部水利署)
      parent_oid VARCHAR(128),             -- 上級機關 OID (樹狀關聯)
      level_type VARCHAR(16),              -- 層級 (院, 部, 署局, 處组)
      attributes_json TEXT,                -- [SPC-006] 動態屬性 JSON (地址, DN, spec_version)
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(parent_oid) REFERENCES master_agencies(agency_oid)
  );
  ```

### 3.2 機關處務規程與法定職掌虛擬表 (`agency_mandates`)
* 🎯 **詳細表格用途 (Table Purpose)**：
  記錄各中央與地方機關內設單位（組、科、司、處）的法定職掌與依據法規條文。採用 **法規虛擬層 (Virtual Law Layer)** 架構，本機 0MB 開銷，線上查詢時即時連線 PostgreSQL / `law_db` MCP。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `master_agencies` 連結**：透過外鍵 `agency_oid` 連結至權威機關主檔。
  - **與外部 `law_db` 連結**：透過 `law_article` 條文編號與 `unit_name`，由 `VirtualLawAdapter` 連線外部全國法規資料庫/處務規程，提供 AI Agent 進行「這個資料集屬於哪一個科室的法定職掌」業務歸屬分析。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE agency_mandates (
      mandate_id INTEGER PRIMARY KEY AUTOINCREMENT,
      agency_oid VARCHAR(128) NOT NULL,    -- 對應之機關 OID
      unit_name VARCHAR(128) NOT NULL,     -- 內部組/科名稱 (如 水質管理組)
      law_article VARCHAR(32),             -- 依據法規條文 (如 第 5 條)
      mandate_text TEXT NOT NULL,          -- 法定掌理事項內文
      keywords_json TEXT,                  -- 萃取之業務關鍵字 JSON 清單
      attributes_json TEXT,                -- [SPC-006] 動態屬性 JSON (含 spec_version)
      FOREIGN KEY(agency_oid) REFERENCES master_agencies(agency_oid)
  );
  ```

### 3.3 發布機關別名對照表 (`publisher_aliases`)
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄 **708 筆** `data.gov.tw` 網路上各種髒亂、俗稱、舊制或業務司處字串（如「農糧署」、「行政院農業委員會農糧署」、「農糧署作物生產組」），透過名稱正規化清理並映射至權威 OID。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `master_agencies` 連結**：`mapped_agency_oid` 外鍵直連 `master_agencies.agency_oid`。
  - **跨資料集對照整合 (Data Alignment Pipeline)**：當 Core SDK `BaseDomainAdapter.align_publisher_oid()` 收到任意字串時，查詢本表進行 1 毫秒別名歸併，傳回標註信心分數 (`confidence_score` 1.0/0.9/0.8) 的權威 OID。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE publisher_aliases (
      alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
      raw_publisher_name VARCHAR(128) UNIQUE NOT NULL, -- data.gov.tw 原始名稱 (如 農糧署)
      mapped_agency_oid VARCHAR(128) NOT NULL,          -- 映射之 OID (2.16.886.101.20003.20064.20070)
      confidence_score FLOAT DEFAULT 1.0,               -- 匹配信心度 (1.0 完全, 0.9 司處上溯, 0.8 簡稱)
      attributes_json TEXT,                            -- [SPC-006] 規則標籤與修訂履歷
      FOREIGN KEY(mapped_agency_oid) REFERENCES master_agencies(agency_oid)
  );
  ```

### 3.4 部會子專案實體展開註冊表 (`domain_deployments`)
* 🎯 **詳細表格用途 (Table Purpose)**：
  負責登記所有已啟動建置或前置規劃中的部會子專案（如 `GOV-A19` 農業部 `tw-agro-db`、`GOV-A13` 內政部 `tw-moi-db`），保存其磁碟相對路徑 `repo_path` 與根機關 OID。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `master_agencies` 連結**：`root_agency_oid` 直連領域根機關。
  - **與 `domain_map_config.json` 及 `DomainRegistryResolver` 連結**：作為動態路由的核心依據。Core SDK 導航解析器讀取本表，實現跨專案 CLI 命令調用 (`run_domain_cli`) 與跨專案 SQLite DB 實體直連。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE domain_deployments (
      domain_id VARCHAR(64) PRIMARY KEY,       -- 領域 ID (如 GOV-A19, GOV-A13)
      domain_name VARCHAR(128) NOT NULL,      -- 專案名稱 (如 農業部開放資料主題對照庫)
      root_agency_oid VARCHAR(128) NOT NULL,  -- 根機關 OID (如 2.16.886.101.20003.20064)
      repo_path VARCHAR(256),                 -- 相對路徑 (events-2026Q3/agro-db-in/tw-agro-db)
      deployment_status VARCHAR(32) DEFAULT 'ACTIVE',
      attributes_json TEXT,                  -- 維護團隊標籤與版本號
      registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(root_agency_oid) REFERENCES master_agencies(agency_oid)
  );
  ```

### 3.4.1 機關歷史改制與組織演進圖譜審核表 (`agency_genealogy`) [G30 核心實體表]
* 🎯 **詳細表格用途 (Table Purpose)**：
  記錄中央各部會、附屬機關歷史改制、升格、更名與廢止演進歷程。實裝 **JIT 輕量化巨觀推導 (JIT Macro Pattern Derivation)** 機制，資料庫僅記錄抽象演進骨幹規則與法規依據（如各河川局 ➔ 各河川分署），執行期動態對齊官方 6,937 筆最新 OID，避免底層資料庫膨脹數千筆附屬機構。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `master_agencies` 連結**：`successor_oid` 與 `predecessor_oid` 直接對齊權威機關 OID 主檔。
  - **與外部 `law_cli` 連結**：透過 `pcode` 與 `law_name` 直連全國法規資料庫歷史沿革與廢止條例。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE agency_genealogy (
      genealogy_id INTEGER PRIMARY KEY AUTOINCREMENT,
      predecessor_name VARCHAR(128) NOT NULL,   -- 前身機關名稱 (如 行政院農業委員會)
      predecessor_oid VARCHAR(128),              -- 前身機關 OID
      successor_name VARCHAR(128) NOT NULL,     -- 繼承/現行機關名稱 (如 農業部)
      successor_oid VARCHAR(128),                -- 現行權威 OID (如 2.16.886.101.20003.20064)
      event_type VARCHAR(32) NOT NULL,           -- UPGRADE (改制), ABOLISH (廢止), MERGE (整併)
      effective_date VARCHAR(16),                -- 生效日期 (如 112年8月1日)
      law_name VARCHAR(128) NOT NULL,            -- 依據法規 (如 農業部組織法)
      law_article VARCHAR(32),                    -- 法規條次
      pcode VARCHAR(16),                          -- law_cli PCode 識別碼
      source_text TEXT,                          -- 法規原文摘要
      completeness_level VARCHAR(32) NOT NULL,   -- FULL_MATCH, PARTIAL_MATCH, TEXT_ONLY
      confidence_score FLOAT DEFAULT 0.5,        -- 0.0 ~ 1.0
      review_status VARCHAR(32) DEFAULT 'PENDING_REVIEW', -- VERIFIED, PENDING_REVIEW, NEEDS_PATCH
      reviewed_by VARCHAR(64),
      reviewed_at TIMESTAMP,
      attributes_json TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

---

## 🔑 Part B: `universal_keys.sqlite` 五大通用基石庫 (8 大實體表)

### 3.5 行政區劃主檔表 (`admin_codes`) [基石二]
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄 **480 筆** 6 碼國家標準行政區劃程式碼 (22 縣市 + 368 鄉鎮市區，如 `630000` 臺北市、`680000` 桃園市)。為全台灣地理空間資料提供唯一的行政邊界關鍵字。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **被多表強烈引用 (Spatial Hub)**：被 `cadastral_registry` (地籍)、`zipcode_registry` (門牌)、`npo_registry` (農會) 與 `corporate_registry` (企業) 之 `admin_code` 外鍵引用。
  - **跨部會聯防 (如 `tw-agro-db` ↔ `tw-moi-db`)**：將農業部的休閒農場與內政部的國土使用分區，透過 6 碼 `admin_code` 於 SQL 中一秒完成 `JOIN` 碰撞！
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE admin_codes (
      admin_code VARCHAR(8) PRIMARY KEY,   -- 6碼國家標準程式碼 (如 630000 臺北市)
      city_name VARCHAR(32) NOT NULL,      -- 縣市名稱
      district_name VARCHAR(32) NOT NULL,  -- 鄉鎮市區名稱
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

### 3.6 全國地籍段名段號表 (`cadastral_registry`) [基石二]
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄全台地籍段名與段號正則化 `cadastral_id`（格式：`行政區碼_段碼_地號`，如 `68000_0100_0000`），解決中文地籍字串無法直接比對的痛點。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `admin_codes` 連結**：透過 `admin_code` 歸屬至鄉鎮市區。
  - **與內政部地政庫 (`tw-moi-db`) 連結**：提供地籍圖邊界與土地變更對照整合。
  - **與農業部農地庫 (`tw-agro-db`) 連結**：連線農糧署產銷班與農地重劃圖資，進行國土違規侵占聯防。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE cadastral_registry (
      cadastral_id VARCHAR(32) PRIMARY KEY, -- 格式: 縣市碼_段號_地號 (如 68000_0100_0000)
      section_code VARCHAR(16) NOT NULL,   -- 段程式碼
      section_name VARCHAR(64) NOT NULL,   -- 段名稱 (如 成功段)
      admin_code VARCHAR(8) NOT NULL,      -- 所屬行政區劃
      attributes_json TEXT,
      FOREIGN KEY(admin_code) REFERENCES admin_codes(admin_code)
  );
  ```

### 3.7 郵遞區號與地址對照表 (`zipcode_registry`) [基石二]
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄 **117+ 筆全台實體** 與 372 筆通用 3 碼郵遞區號。搭配 CGS v2.4 CLI 工具 `g20_cli.py align-address` 提供門牌地址串流正規化、舊制縣市升格轉譯（如「桃園縣中壢市」轉「桃園市中壢區」）與門牌結構完整度指標 (AIS - Address Integrity Score, 🟢 HIGH / 🟡 MEDIUM / 🔴 LOW) 反查。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `admin_codes` 連結**：透過 `admin_code` 連結至 6 碼國家標準行政區劃。
  - **與門牌地址轉碼服務 (TGOS / `tw-moi-db`) 連結**：將異質文字地址（如「臺北市信義區市府路1號」）轉譯為 3 碼/6 碼郵遞區號與行政區劃主鍵。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE zipcode_registry (
      zipcode VARCHAR(8) PRIMARY KEY,      -- 3碼郵遞區號 (如 302, 110)
      admin_code VARCHAR(8) NOT NULL,      -- 所屬行政區劃 (如 10004010, 63000060)
      county_name VARCHAR(32) NOT NULL,    -- 權威縣市名
      town_name VARCHAR(32) NOT NULL,      -- 權威鄉鎮區名
      attributes_json TEXT,                -- 半結構化屬性與清洗紀錄
      FOREIGN KEY(admin_code) REFERENCES admin_codes(admin_code)
  );
  ```

### 3.8 水系河川主檔表 (`river_registry`) [基石三]
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄 **122 條** 國家標準水系與主幹流域程式碼 (`river_id`，如 `1300` 淡水河水系、`1510` 濁水溪水系)。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **被 `station_registry` 引用**：氣象與水質監測站點透過 `river_id` 歸屬至流域。
  - **與經濟部水利署 (`tw-moea-db`) 連結**：連結水庫集水區、淹水潛勢圖與河川污染防治資料集。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE river_registry (
      river_id VARCHAR(16) PRIMARY KEY,    -- 水系程式碼 (如 1300 淡水河水系)
      river_name VARCHAR(64) NOT NULL,     -- 水系名稱
      main_stream VARCHAR(64),             -- 主幹流
      basin_area_sqkm FLOAT,               -- 流域面積 (平方公里)
      attributes_json TEXT
  );
  ```

### 3.9 氣象與環境監測站點主檔表 (`station_registry`) [基石三]
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄 **450 個** 中央氣象署與環境部官方測站，提供 WGS84 經緯度座標 (`latitude`, `longitude`)。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `river_registry` 連結**：外鍵 `river_id` 標註水文站點流域。
  - **與農業部災防網 (`tw-agro-db`) 連結**：將氣象局低溫寒害測站資料與農藝作物產區進行 WGS84 空間碰撞。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE station_registry (
      station_id VARCHAR(32) PRIMARY KEY,  -- 測站程式碼 (如 466920 臺北氣象站)
      station_name VARCHAR(64) NOT NULL,   -- 測站名稱
      station_type VARCHAR(32) NOT NULL,   -- 類型 (WEATHER 氣象, WATER_QUALITY 水質)
      latitude FLOAT NOT NULL,             -- WGS84 緯度
      longitude FLOAT NOT NULL,            -- WGS84 經度
      river_id VARCHAR(16),                -- 鄰近水系
      attributes_json TEXT,
      FOREIGN KEY(river_id) REFERENCES river_registry(river_id)
  );
  ```

### 3.10 法人與企業旁路透傳快取表 (`corporate_registry`) [基石四]
* 🎯 **詳細表格用途 (Table Purpose)**：
  採用 **Pass-Through Cache 旁路透傳快取架構**。本機收錄代表性上市櫃與國營企業權威 Seed 快取，搭配 CGS v2.4 CLI 工具 `g60_cli.py` 提供純 Python 8 碼統一編號加權檢核（相容舊制除 10、第 7 位為 7 特例與 2023 年 4 月財政部新制除 5/10 雙重規則）、長文本串流統編萃取濾網 (`pipe --extract`)，以及 Cache Miss 時連線經濟部 GCIS API 動態寫回。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `admin_codes` 連結**：外鍵 `admin_code` 提供企業登記地緣分析。
  - **與經濟部商業庫 (`tw-moea-db`) 連結**：作為 160 萬全量公司商業登記的本地極速快取代理。
  - **跨部會 UNIX 管線穿透**：支援衛福部食安裁罰 (A18)、採購公報廠商名冊直接透過管道輸入 `g60` 進行合法性校驗與地址反查。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE corporate_registry (
      tax_id VARCHAR(8) PRIMARY KEY,       -- 8碼企業統一編號 (如 22570177)
      company_name VARCHAR(128) NOT NULL,  -- 企業名稱 (如 台灣積體電路製造股份有限公司)
      registered_address VARCHAR(256),     -- 登記營業地址
      admin_code VARCHAR(8),               -- 所屬行政區劃
      status VARCHAR(32) DEFAULT 'ACTIVE', -- 營運狀態
      source VARCHAR(32) DEFAULT 'SEED',   -- 資料來源 (SEED, GCIS_API)
      cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(admin_code) REFERENCES admin_codes(admin_code)
  );
  ```

### 3.11 農會與非營利組織法人主檔表 (`npo_registry`) [基石四]
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄依法登記之 NGO、基金會與全台 302 家各級農會與 40 家漁會拓樸主檔。搭配 G60 維度器提供「消歧義對齊引擎 (`resolve`)」，能自動剝除分支機構綴詞（信用部、生鮮超市、辦事處），並結合 G20 空間行政區外推，將不規範的民間簡稱（如「板農」、「新埔農會」）精準對齊至官方正式全名與組織程式碼。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **與 `admin_codes` 連結**：外鍵 `admin_code` 進行基層農會與鄉鎮市區對照整合。
  - **與農業部農會庫 (`tw-agro-db`) 連結**：連結農業部產銷班、天然災害救助申請單位、推廣課、信用部與休閒農場輔導名錄。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE npo_registry (
      npo_id VARCHAR(32) PRIMARY KEY,      -- 法人程式碼 / 統編 (如 FA_NTP_001)
      npo_name VARCHAR(128) NOT NULL,      -- 法人官方正式名稱 (如 新北市板橋區農會)
      short_name VARCHAR(64),              -- 通俗簡稱或別名 (如 板農)
      npo_type VARCHAR(32) NOT NULL,       -- 類型 (FARMERS_ASSOC 農會, FISHERY_ASSOC 漁會, NGO 非營利)
      level VARCHAR(16),                   -- 層級 (NATIONAL, MUNICIPAL, COUNTY, DISTRICT)
      city_name VARCHAR(32),               -- 所在縣市
      admin_code VARCHAR(8),               -- 行政區程式碼
      address VARCHAR(256),                -- 登記地址
      parent_id VARCHAR(32),               -- 上級輔導農會程式碼
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(admin_code) REFERENCES admin_codes(admin_code)
  );
  ```

### 3.12 行政機關辦公日曆表 (`calendar_registry`) [基石五]
* 🎯 **詳細表格用途 (Table Purpose)**：
  收錄 **1,801 筆** (2013-2028 跨越 16 年) 全國行政機關辦公行事曆、例假日、調移放假與補行上班日。搭配 CGS v2.4 CLI 工具 `g40_cli.py` 提供全政府異質日期清理（民國年月日、中文農曆、季度、會計年度）、跨度法定工作天精確計算、補班日逆向判定、純 Python 緊湊農曆（1900-2100 年公曆農曆雙向轉換、生肖天干地支）、二十四節氣天文常數計算與 UNIX Pipe 流式資料過濾。
* 🔗 **跨 DB / 跨模組連結性 (Inter-DB Connectivity)**：
  - **時序對照整合 (Temporal Alignment)**：為所有跨部會資料集中異質時間字串清洗後生成的 ISO-8601 日期，提供「是否為工作日/放假日/補上班日」的時序脈絡對照整合，並自動附帶農曆歲次、生肖與傳統三大節（春節、端午、中秋）標記。
  - **跨模組管線 (UNIX Pipe Native)**：可直接透過管道串接 G10（標案計畫履約天數計算）、G20（空間時序交叉統計）及 GOV-A19（農漁批發市場初一十五休市日與節氣產銷分析）。
* 📜 **DDL 宣告**：
  ```sql
  CREATE TABLE calendar_registry (
      date_str VARCHAR(10) PRIMARY KEY,    -- ISO-8601 日期 (如 2024-08-22)
      year INTEGER NOT NULL,               -- 西元年 (如 2024)
      minguo_year INTEGER NOT NULL,        -- 民國年 (如 113)
      month INTEGER NOT NULL,              -- 月份 (1-12)
      day INTEGER NOT NULL,                -- 日期 (1-31)
      day_of_week INTEGER NOT NULL,        -- 星期幾 (1=Mon ... 7=Sun)
      is_holiday BOOLEAN NOT NULL,         -- 是否為例假日/放假日
      is_working_day BOOLEAN NOT NULL,     -- 是否為法定上班日 (含週六補班日)
      holiday_category VARCHAR(64),        -- 假別分類 (放假之紀念日及節日、補行上班日、調整放假日等)
      description VARCHAR(256),            -- 節日或放假事由說明
      attributes_json TEXT,                -- 動態屬性與更新歷史
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE INDEX idx_calendar_year ON calendar_registry(year);
  CREATE INDEX idx_calendar_minguo ON calendar_registry(minguo_year);
  CREATE INDEX idx_calendar_working ON calendar_registry(is_working_day);
  ```

---

## ⚙️ Part C: 追溯與擴充中繼管線

### 3.13 `attributes_json` 欄位解析器與 SDK 動態讀寫指南 (`GovBaseEntity`)

所有實體表中的 `attributes_json` 均透過 Core SDK 中的 [`GovBaseEntity`](../src/core/gov_base_entity.py) 進行透明化讀寫。此欄位不僅保存 `spec_version: "0.2"` 受控版號與 Sys Meta，更完全負責儲存符合 `[SPC-013]` 規範的修訂履歷陣列 (`history_trail`)：

```python
from src.core.gov_base_entity import GovBaseEntity

# 實體化通用 Base Entity
entity = GovBaseEntity(
    entity_id="2.16.886.101.20003.20064.20070",
    spec_version="0.2"
)

# 寫入修訂履歷軌跡 (history_trail)
entity.add_history_trail(
    field="date_raw",
    original_val="113/08/22",
    cleaned_val="2024-08-22T00:00:00+08:00",
    rule_applied="BaseDomainAdapter.clean_datetime"
)

# 匯出符合 Schema.org 規範之 JSON-LD 物件
json_ld_output = entity.to_jsonld()
```

### 3.14 資料來源追溯中繼檔 (`datasource_metadata.json`) 與 CI/CD

為了確保 SQLite 實體庫保持純粹性，`GOV-300` 將原始資料集下載 URL、發布單位與歷史快照 Sha256 雜湊碼，完全解耦至獨立中繼檔案 [`ontology/datasource_metadata.json`](../ontology/datasource_metadata.json)：

```json
{
  "spec_version": "0.2",
  "datasources": [
    {
      "dataset_id": "master_agencies_oid_v1",
      "dataset_name": "政府機關唯一識別程式碼 (OID)",
      "publisher_oid": "2.16.886.101.20003.20007",
      "source_url": "https://data.gov.tw/dataset/173440",
      "sha256_hash": "a8f9c2d1b0e3f4a5...",
      "last_harvested": "2026-08-22T10:40:00+08:00"
    }
  ]
}
```
這種「Schema.sql + JSON 中繼檔」的解耦設計，能讓資料庫隨時進行 CI/CD 自動化重建驗證與 GitHub 差異追溯！
