# ==============================================================================
# tw-gov-db 全政府資料治理與語意中繼底座 實體 Schema (schema.sql)
# Last Updated: 2026-08-22
# Spec Traceability: [SPC-001 ~ SPC-007, DSN-S01 ~ DSN-S04]
# Database Targets:
#   1. master_agencies.sqlite (全台灣權威機關、處務規程、發布單位別名、部會子專案註冊)
#   2. universal_keys.sqlite (全政府五大基石 10 大共通對照資料庫)
#   資料來源追溯清冊參閱獨立檔案: ontology/datasource_metadata.json
# ==============================================================================

-- ==============================================================================
-- Part 1: master_agencies.sqlite 權威機關主檔與資料治理 schema
-- ==============================================================================

-- 1. 機關主檔 (Agencies)
CREATE TABLE IF NOT EXISTS master_agencies (
    agency_oid VARCHAR(128) PRIMARY KEY,           -- 政府 OID (如 2.16.886.101.20003.20007)
    org_code VARCHAR(32),                          -- 行政院機關代碼 (如 313000000G)
    agency_name VARCHAR(128) NOT NULL,             -- 官方全稱 (如 經濟部水利署)
    parent_oid VARCHAR(128),                       -- 上級機關 OID (組織樹父子關聯)
    level_type VARCHAR(16),                        -- 層級 (院, 部, 署局, 處組)
    attributes_json TEXT,                          -- [SPC-006] 動態屬性 JSON (含 spec_version, address, dn 等)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(parent_oid) REFERENCES master_agencies(agency_oid)
);

-- 2. 處務規程法定職掌 (Mandates) - [虛擬層 Virtual Layer]
-- 本機不硬載龐大法條，查詢時由 VirtualLawAdapter 透過 law_cli.py / law_db MCP (PostgreSQL) 虛擬檢索
-- 參考規格: events-2026Q3/law_meta_in (LAW_DB_ONBOARDING.md)
CREATE TABLE IF NOT EXISTS agency_mandates (
    mandate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agency_oid VARCHAR(128) NOT NULL,              -- 對應之機關 OID
    unit_name VARCHAR(128) NOT NULL,               -- 內部組/科名稱 (如 水質管理組)
    law_article VARCHAR(32),                       -- 依據法規條文 (如 第 5 條)
    mandate_text TEXT NOT NULL,                    -- 法定掌理事項內文
    keywords_json TEXT,                            -- 萃取之業務關鍵字 JSON 清單
    attributes_json TEXT,                          -- [SPC-006] 動態屬性 JSON (含 spec_version)
    FOREIGN KEY(agency_oid) REFERENCES master_agencies(agency_oid)
);

-- 3. 發布機關別名對照表 (Publisher Aliases)
CREATE TABLE IF NOT EXISTS publisher_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_publisher_name VARCHAR(128) UNIQUE NOT NULL, -- data.gov.tw 原始發布名稱 (如 教育部政風處 / 消防署)
    mapped_agency_oid VARCHAR(128) NOT NULL,          -- 映射之權威 OID (如 2.16.886.101.20003.20005)
    confidence_score FLOAT DEFAULT 1.0,               -- 對齊分數 (1.0 完全, 0.9 司處上溯, 0.8 簡稱)
    attributes_json TEXT,                            -- [SPC-006] 動態屬性 JSON (含 spec_version, 規則標籤)
    FOREIGN KEY(mapped_agency_oid) REFERENCES master_agencies(agency_oid)
);

-- 4. 部會子專案實體展開註冊表 (Domain Deployments Registry)
CREATE TABLE IF NOT EXISTS domain_deployments (
    domain_id VARCHAR(64) PRIMARY KEY,                 -- 領域 ID (如 tw-agro-db, tw-moi-db)
    domain_name VARCHAR(128) NOT NULL,                  -- 領域專案名稱 (如 台灣農漁畜開放數據全景圖鑑)
    root_agency_oid VARCHAR(128) NOT NULL,              -- 領域根機關 OID (如 2.16.886.101.20003.20064)
    repo_path VARCHAR(256),                             -- 專案實體相對路徑 (如 events-2026Q3/agro-db-in/tw-agro-db)
    deployment_status VARCHAR(32) DEFAULT 'ACTIVE',     -- 展開狀態 (ACTIVE, INACTIVE, DRAFT)
    attributes_json TEXT,                              -- [SPC-006] 動態屬性 JSON (含 spec_version, 維護團隊, Schema 標籤)
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(root_agency_oid) REFERENCES master_agencies(agency_oid)
);


-- ==============================================================================
-- Part 2: universal_keys.sqlite 全政府五大基石 10 大共通對照資料庫 schema
-- ==============================================================================

-- 5. 基石二：行政區劃主檔 (admin_codes)
CREATE TABLE IF NOT EXISTS admin_codes (
    admin_code VARCHAR(8) PRIMARY KEY,             -- 6碼國家標準代碼 (如 630000 臺北市)
    city_name VARCHAR(32) NOT NULL,                -- 縣市名稱
    district_name VARCHAR(32) NOT NULL,             -- 鄉鎮市區名稱
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 基石二：全國地籍段名段號表 (cadastral_registry)
CREATE TABLE IF NOT EXISTS cadastral_registry (
    section_code VARCHAR(16) PRIMARY KEY,          -- 地籍段號代碼 (如 F-01-0001)
    city_name VARCHAR(32) NOT NULL,                -- 縣市名稱
    district_name VARCHAR(32) NOT NULL,            -- 鄉鎮區名稱
    section_name VARCHAR(64) NOT NULL,             -- 地籍段名 (如 成功段)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 基石二：郵遞區號與地址對照表 (zipcode_registry)
CREATE TABLE IF NOT EXISTS zipcode_registry (
    zipcode VARCHAR(8) PRIMARY KEY,                -- 3碼/5碼/6碼郵遞區號
    city_name VARCHAR(32) NOT NULL,                -- 縣市名稱
    district_name VARCHAR(32) NOT NULL,            -- 鄉鎮區名稱
    scope_description VARCHAR(256),                -- 涵蓋路段描述
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 基石三：水系河川主檔 (river_registry)
CREATE TABLE IF NOT EXISTS river_registry (
    river_id VARCHAR(32) PRIMARY KEY,              -- 國家水系代碼 (如 1300 淡水河水系)
    river_name VARCHAR(64) NOT NULL,               -- 水系名稱
    main_basin VARCHAR(64),                        -- 主幹流域 (如 淡水河水系)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. 基石三：環境/氣象/水文測站主檔 (station_registry)
CREATE TABLE IF NOT EXISTS station_registry (
    station_id VARCHAR(64) PRIMARY KEY,            -- 測站代碼 (如 C0A980)
    station_name VARCHAR(128) NOT NULL,            -- 測站名稱
    station_type VARCHAR(32),                      -- 測站類型 (WEATHER, WATER_QUALITY, RAINFALL)
    agency_name VARCHAR(128),                      -- 所屬機關 (如 中央氣象署, 環境部)
    latitude FLOAT,
    longitude FLOAT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. 基石四：法人與企業主檔 (corporate_registry) - [快取層 Pass-Through Cache Layer]
-- 借鏡 tw-med-db (m5x_*_cache 旁路透傳快取模式)，本機僅保留常用 Seed，Miss 時自動透傳連線 GCIS API 並快取寫回
-- 參考規格: events/TDHI_haba/med-db-in/tw-med-db (book/03_00_structure_guide.md)
CREATE TABLE IF NOT EXISTS corporate_registry (
    tax_id VARCHAR(8) PRIMARY KEY,                 -- 8碼統一編號
    company_name VARCHAR(256) NOT NULL,            -- 公司/商號名稱
    registered_address VARCHAR(256),               -- 登記地址
    admin_code VARCHAR(8),                         -- 所屬行政區代碼
    is_seed BOOLEAN DEFAULT 0,                     -- 是否為熱門 Seed 採樣
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 快取寫入時間戳 (支援 TTL 淘汰/更新)
);

-- 11. 基石四：農會與非營利組織法人主檔 (npo_registry)
CREATE TABLE IF NOT EXISTS npo_registry (
    npo_id VARCHAR(32) PRIMARY KEY,                -- 農會/NPO代碼或統編
    npo_name VARCHAR(256) NOT NULL,                -- 農會或法人名稱
    npo_type VARCHAR(32),                          -- 類型 (FARMERS_ASSOCIATION, FOUNDATION, NGO)
    city_name VARCHAR(32),                         -- 所在縣市
    address VARCHAR(256),                          -- 機構地址
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. 基石五：行政機關辦公日曆表 (calendar_registry)
CREATE TABLE IF NOT EXISTS calendar_registry (
    date_str VARCHAR(10) PRIMARY KEY,              -- 日期 (YYYY-MM-DD)
    is_holiday BOOLEAN NOT NULL,                   -- 是否為放假日/例假日
    holiday_category VARCHAR(64),                  -- 節日類型 (國定假日, 颱風假, 周休二日)
    description VARCHAR(256),                      -- 節日說明
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


