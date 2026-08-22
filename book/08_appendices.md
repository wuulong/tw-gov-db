# 🏛️ 附錄 (Appendix)：全庫 DDL 腳本、CLI 指令速查與全書 Mermaid 圖表索引 (08_appendices.md)

* **專案名稱**：`tw-gov-db` (台灣政府開放資料通用基石對照庫)
* **專案代號**：`GOV-300` (方案 A 權威機關簡碼 `300000000A`)
* **當前版本**：`v0.2.1`
* **歸檔路徑**：`events-2026Q3/gov-db-in/tw-gov-db/book/08_appendices.md`

---

## 📜 附錄 A：GOV-300 全庫 DDL 腳本與完整 Schema 字典 (含詳細欄位註解)

以下提供包含全欄位詳細 SQL 行內註解 (`--`) 的 `GOV-300` 12 大實體資料表完整可執行 DDL 宣告腳本：

### A.1 `master_agencies.sqlite` DDL (4 大機關權威表，帶詳細註解)

```sql
-- ============================================================================
-- 1. 機關權威主檔表 (master_agencies)
-- 用途: 收錄全台 7,956 筆官方權威 OID 組織樹，作為全政府機關身份的 Single Source of Truth
-- ============================================================================
CREATE TABLE IF NOT EXISTS master_agencies (
    agency_oid VARCHAR(128) PRIMARY KEY,     -- [主鍵] 政府 OID 權威識別碼 (如 2.16.886.101.20003.20007)
    org_code VARCHAR(32),                    -- 行政院機關程式碼 (如 313000000G)
    agency_name VARCHAR(128) NOT NULL,       -- 機關官方全稱 (如 經濟部水利署)
    parent_oid VARCHAR(128),                 -- [外鍵] 上級機關 OID (樹狀關聯，指向 master_agencies.agency_oid)
    level_type VARCHAR(16),                  -- 機關層級 (院, 部, 署局, 處組)
    attributes_json TEXT,                    -- [SPC-006] 動態屬性 JSON (含 spec_version: "0.2", 地址, DN, history_trail)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 最後更新時間戳
    FOREIGN KEY(parent_oid) REFERENCES master_agencies(agency_oid)
);

-- ============================================================================
-- 2. 機關處務規程與法定職掌虛擬表 (agency_mandates)
-- 用途: 記錄各機關內部組/科/司/處之法定職掌與法規依據 (Virtual Law Layer，本機 0MB 開銷)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agency_mandates (
    mandate_id INTEGER PRIMARY KEY AUTOINCREMENT, -- [自增主鍵] 職掌流水號
    agency_oid VARCHAR(128) NOT NULL,             -- [外鍵] 對應之機關 OID
    unit_name VARCHAR(128) NOT NULL,              -- 內部單位/組科名稱 (如 水質管理組)
    law_article VARCHAR(32),                      -- 依據法規條文 (如 第 5 條)
    mandate_text TEXT NOT NULL,                   -- 法定掌理事項全文
    keywords_json TEXT,                           -- 萃取之業務關鍵字 JSON 清單
    attributes_json TEXT,                         -- [SPC-006] 動態屬性 JSON (含 spec_version: "0.2")
    FOREIGN KEY(agency_oid) REFERENCES master_agencies(agency_oid)
);

-- ============================================================================
-- 3. 發布機關別名對照表 (publisher_aliases)
-- 用途: 收錄 708 筆 data.gov.tw 異質/俗稱/舊制發布名稱，自動歸併至權威 OID
-- ============================================================================
CREATE TABLE IF NOT EXISTS publisher_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,   -- [自增主鍵] 別名對照流水號
    raw_publisher_name VARCHAR(128) UNIQUE NOT NULL, -- data.gov.tw 原始發布者字串 (如 "農糧署")
    mapped_agency_oid VARCHAR(128) NOT NULL,      -- [外鍵] 映射至權威機關 OID
    confidence_score FLOAT DEFAULT 1.0,           -- 匹配信心分數 (1.0 完全匹配, 0.9 司處上溯, 0.8 簡稱)
    attributes_json TEXT,                         -- [SPC-006] 動態屬性 JSON (含 匹配規則標籤)
    FOREIGN KEY(mapped_agency_oid) REFERENCES master_agencies(agency_oid)
);

-- ============================================================================
-- 4. 部會子專案實體展開註冊表 (domain_deployments)
-- 用途: 登記各部會子專案 (tw-agro-db, tw-moi-db) 於母專案之領域代號與相對路徑
-- ============================================================================
CREATE TABLE IF NOT EXISTS domain_deployments (
    domain_code VARCHAR(32) PRIMARY KEY,          -- [主鍵] 方案 A 官方簡碼 (如 GOV-A19, GOV-A13)
    root_agency_oid VARCHAR(128) NOT NULL,        -- [外鍵] 部會領域根 OID (如 2.16.886.101.20003.20064)
    repo_path VARCHAR(256) NOT NULL,              -- 子專案預定相對磁碟路徑 (如 events-2026Q3/agro-db-in/tw-agro-db)
    attributes_json TEXT,                         -- [SPC-006] 動態屬性 JSON (含 維護團隊與 Repo 網址)
    FOREIGN KEY(root_agency_oid) REFERENCES master_agencies(agency_oid)
);
```

---

### A.2 `universal_keys.sqlite` DDL (5 大通用基石庫 8 大實體表，帶詳細註解)

```sql
-- ============================================================================
-- 1. 行政區劃主檔表 (admin_codes) [基石二: 空間地籍]
-- 用途: 收錄全台 480 筆 6 碼國家標準行政區劃程式碼 (22 縣市 + 368 鄉鎮市區)
-- ============================================================================
CREATE TABLE IF NOT EXISTS admin_codes (
    admin_code VARCHAR(16) PRIMARY KEY,           -- [主鍵] 6 碼行政區劃程式碼 (如 630000 臺北市)
    city_name VARCHAR(32) NOT NULL,               -- 縣市名稱 (如 臺北市)
    district_name VARCHAR(32) NOT NULL,           -- 鄉鎮市區名稱 (如 中正區)
    attributes_json TEXT                          -- [SPC-006] 動態屬性 JSON (含 舊制程式碼對照)
);

-- ============================================================================
-- 2. 全國地籍段名段號表 (cadastral_registry) [基石二: 空間地籍]
-- 用途: 收錄全台灣權威地籍段名與正則化地籍段號 (cadastral_id)
-- ============================================================================
CREATE TABLE IF NOT EXISTS cadastral_registry (
    cadastral_id VARCHAR(64) PRIMARY KEY,         -- [主鍵] 正則化地籍編號 [admin_code][section_code][land_no]
    admin_code VARCHAR(16) NOT NULL,              -- [外鍵] 所屬行政區劃程式碼
    section_code VARCHAR(16) NOT NULL,            -- 地政司段程式碼
    section_name VARCHAR(64) NOT NULL,            -- 地籍段名 (如 成功段)
    attributes_json TEXT,                         -- [SPC-006] 動態屬性 JSON (含 面積, 分區)
    FOREIGN KEY(admin_code) REFERENCES admin_codes(admin_code)
);

-- ============================================================================
-- 3. 郵遞區號與地址對照表 (zipcode_registry) [基石二: 空間地籍]
-- 用途: 3 碼本機郵遞區號與地址對照表 (線上即時支援 6 碼投遞區號反查)
-- ============================================================================
CREATE TABLE IF NOT EXISTS zipcode_registry (
    zipcode VARCHAR(8) PRIMARY KEY,               -- [主鍵] 郵遞區號 (如 100)
    admin_code VARCHAR(16) NOT NULL,              -- [外鍵] 對應行政區劃程式碼
    road_name VARCHAR(64) NOT NULL,               -- 路名/街名 (如 重慶南路一段)
    attributes_json TEXT,                         -- [SPC-006] 動態屬性 JSON (含 6碼投遞區號介面)
    FOREIGN KEY(admin_code) REFERENCES admin_codes(admin_code)
);

-- ============================================================================
-- 4. 水系河川主檔表 (river_registry) [基石三: 水系氣象]
-- 用途: 收錄全台灣 122 條國家水系與主幹流域程式碼 (river_id)
-- ============================================================================
CREATE TABLE IF NOT EXISTS river_registry (
    river_id VARCHAR(16) PRIMARY KEY,             -- [主鍵] 國家水系程式碼 (如 1300 淡水河水系)
    river_name VARCHAR(64) NOT NULL,              -- 河川全稱 (如 淡水河)
    main_basin VARCHAR(64),                       -- 所屬主幹流域 (如 淡水河水系)
    attributes_json TEXT                          -- [SPC-006] 動態屬性 JSON (含 水利署水系長度)
);

-- ============================================================================
-- 5. 氣象與環境監測站點主檔表 (station_registry) [基石三: 水系氣象]
-- 用途: 收錄全台 450 個中央氣象署與環境部官方測站 (經緯度 WGS84)
-- ============================================================================
CREATE TABLE IF NOT EXISTS station_registry (
    station_id VARCHAR(32) PRIMARY KEY,           -- [主鍵] 氣象/環境測站編號 (如 466920)
    station_name VARCHAR(64) NOT NULL,            -- 測站名稱 (如 臺北氣象站)
    longitude FLOAT NOT NULL,                     -- [WGS84 經度] (如 121.5148)
    latitude FLOAT NOT NULL,                      -- [WGS84 緯度] (如 25.0377)
    station_type VARCHAR(32) NOT NULL,            -- 測站類型 (WEATHER 氣象, WATER_QUALITY 水質)
    attributes_json TEXT                          -- [SPC-006] 動態屬性 JSON (含 海拔高度, 管轄單位)
);

-- ============================================================================
-- 6. 法人與企業旁路透傳快取表 (corporate_registry) [基石四: 法人企業]
-- 用途: 收錄 1,103 筆 Seed 快取上市/國營企業 (Cache Miss 時自動透傳 GCIS API 寫回)
-- ============================================================================
CREATE TABLE IF NOT EXISTS corporate_registry (
    tax_id VARCHAR(16) PRIMARY KEY,               -- [主鍵] 8 碼統一編號 (如 22570177)
    company_name VARCHAR(128) NOT NULL,           -- 公司/企業名稱
    registered_address VARCHAR(256),              -- 官方登記營業地址
    admin_code VARCHAR(16),                       -- [外鍵] 營業地址對應之行政區劃程式碼
    attributes_json TEXT,                         -- [SPC-006] 動態屬性 JSON (含 資本額, 營業狀態, TTL)
    FOREIGN KEY(admin_code) REFERENCES admin_codes(admin_code)
);

-- ============================================================================
-- 7. 農會與非營利組織法人主檔表 (npo_registry) [基石四: 法人企業]
-- 用途: 收錄 23,218 筆 NGO 法人與全台 342 家農漁會法人資料
-- ============================================================================
CREATE TABLE IF NOT EXISTS npo_registry (
    npo_id VARCHAR(32) PRIMARY KEY,               -- [主鍵] NPO / 農會法人編號
    npo_name VARCHAR(128) NOT NULL,               -- 法人官方全稱 (如 板橋區農會)
    npo_type VARCHAR(32) NOT NULL,                -- 法人類型 (FARMERS_ASSOC 農會, NGO 基金會)
    address VARCHAR(256),                         -- 會址/聯絡地址
    attributes_json TEXT                          -- [SPC-006] 動態屬性 JSON (含 信用部/推廣課清單)
);

-- ============================================================================
-- 8. 行政機關辦公日曆表 (calendar_registry) [基石五: 時間時序]
-- 用途: 收錄 1,199 筆 2018-2026 政府辦公日曆 (放假日與颱風假分類)
-- ============================================================================
CREATE TABLE IF NOT EXISTS calendar_registry (
    date_key VARCHAR(10) PRIMARY KEY,             -- [主鍵] 日期字串 YYYY-MM-DD (如 2024-08-22)
    is_holiday BOOLEAN NOT NULL,                  -- 是否為放假日 (1 是, 0 否)
    holiday_category VARCHAR(32),                 -- 放假類別 (WEEKEND 周休, TYPHOON 颱風假)
    attributes_json TEXT                          -- [SPC-006] 動態屬性 JSON (含 備註與補班日)
);
```

---

## 🛠️ 附錄 B：`opendata_cli.py`與 Core CLI 指令速查手冊

### B.1 `opendata_cli.py` 子命令速查
```bash
# 1. 查詢 6 碼門牌投遞區號與行政區劃
python src/cli/opendata_cli.py zipcode "臺北市中正區重慶南路一段120號"

# 2. 檢索開放資料集並觸發 Circuit Breaker 品質 profiling
python src/cli/opendata_cli.py profile --dataset-id 173440

# 3. 強制刷新發布單位別名對齊
python src/cli/opendata_cli.py align-publisher "農業部農糧署"
```

### B.2 Core CLI (`main.py`) 全局診斷手冊
```bash
# 一鍵發動全全全系統健康診斷 (PASS 判定)
python src/cli/main.py doctor
```

---

## 🧙‍♂️ 附錄 C：`gov-db-wizard` Agent 技能調用手冊

### C.1 System Prompt 指引範例
```text
[System Prompt for GOV-300 Agentic Navigation]
你是一個精通台灣政府開放資料通用基石 (GOV-300) 的 AI Agent。
1. 當收到發布單位時，優先呼叫 BaseDomainAdapter.align_publisher_oid() 取得 100% 權威 OID。
2. 進行空間查詢時，將文字地址轉為 admin_code 與 cadastral_id 進行對照整合。
3. 輸出結果強制包含 Schema.org (JSON-LD) @context 物件。
```

---

## 🎨 附錄 D：全書高質感 Mermaid 圖表索引與寫作規範指南

全書共收錄 **14 張** 符合 GitHub 渲染標準的高質感 Mermaid 圖表：

| 所在章節 | 圖表名稱 / 繪製目的 | 圖表類型 (Type) |
| :--- | :--- | :--- |
| **第 2 章 2.5 節** | `DomainRegistryResolver` 三層式 Co-work 協作圖 | `graph TD` |
| **第 3 章 3.0 節** | GOV-300 全庫 12 大實體資料表 ERD 關聯圖 | `erDiagram` |
| **第 4 章 4.0 節** | 第 4 章各部會檔案 8 大寫作結構區塊圖 | `graph TD` |
| **第 4 章 4.A19 節** | GOV-A19 農業部與母大腦實體關聯拓樸圖 | `graph TD` |
| **第 4 章 4.A19 節** | 最複雜四重跨部會連鎖查詢時序圖 | `sequenceDiagram` |
| **第 4 章 4.A13 節** | GOV-A13 內政部國土利用分區對照整合圖 | `graph TD` |
| **第 4 章 4.A09 節** | GOV-A09 經濟部 Pass-Through 快取圖 | `graph TD` |
| **第 5 章 5.1 節** | 基層公務人員防災應變對照整合流程圖 | `flowchart LR` |
| **第 5 章 5.2 節** | 開放資料分析師別名與時間清洗流程圖 | `flowchart LR` |
| **第 5 章 5.3 節** | AI 架構師 GraphRAG 零幻覺 Grounding 流程圖 | `flowchart LR` |
| **第 5 章 5.4 節** | 企業法務旁路快取身份驗證流程圖 | `flowchart LR` |
| **第 5 章 5.5 節** | ESG 顧問國土利用分區空間對疊流程圖 | `flowchart LR` |
| **第 5 章 5.6 節** | 調查記者跨部會實體勾稽流程圖 | `flowchart LR` |
| **第 5 章 5.7 節** | 公民科技反饋報告公私協同治理流程圖 | `flowchart LR` |
| **第 6 章 6.1 節** | SE-6D 六維度追溯鏈拓樸圖 | `graph LR` |
| **第 6 章 6.2 節** | 4 大階梯式跨部會整合完成測試時序圖 | `sequenceDiagram` |
| **第 7 章 7.2 節** | 全台灣開放資料大聯盟黃金三角藍圖 | `graph TD` |
