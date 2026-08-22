-- ============================================================================
-- GOV-AXX 子模組 SQLite 實體對照表 DDL 剛性範本 (schema.sql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS axx_core_entity (
    entity_id VARCHAR(64) PRIMARY KEY,       -- [主鍵] 領域權威識別碼
    publisher_oid VARCHAR(128) NOT NULL,     -- [外鍵] 對齊 GOV-300 master_agencies.agency_oid
    admin_code VARCHAR(16),                  -- [外鍵] 對齊 GOV-300 admin_codes
    cadastral_id VARCHAR(64),                -- [外鍵] 對齊 GOV-300 cadastral_registry
    tax_id VARCHAR(16),                      -- [外鍵] 對齊 GOV-300 corporate_registry
    date_clean VARCHAR(32) NOT NULL,         -- [時間] ISO-8601 格式
    attributes_json TEXT                     -- [SPC-006] 含 spec_version: "0.2.1" 與 history_trail
);
