# tw-gov-db: 資料庫掛載與跨庫共享協同契約 Prompt

> **調用主體**：需與全政府通用基石庫（`universal_keys.sqlite`）、機關主檔庫（`master_agencies.sqlite`）或研究報告庫（`report_index.sqlite`）進行聯邦查詢、JOIN 關聯或靜態字典反查之外部專案。  
> **遵守規格**：DGS v2.0 (資料庫治理規範) & SQLite 聯邦 ATTACH 協定。

---

## 1. 實體資料庫四階解析路徑 (Priority Chain)

外部 Agent 連線時請遵循四階解析順序：
1. **顯式參數**：`--db <path>`
2. **環境變數**：`GOV_DB_DIR` 或 `GOV_DB_SHARED_DIR`
3. **外接擴充儲存 (標準位址)**：
   - `/Volumes/D2024/data/gov-db-in/db/universal_keys.sqlite`
   - `/Volumes/D2024/data/gov-db-in/db/master_agencies.sqlite`
4. **本地 Fallback**：
   - `events-2026Q3/gov-db-in/tw-gov-db/data/universal_keys.sqlite`
   - `events-2026Q3/gov-db-in/tw-gov-db/data/master_agencies.sqlite`

---

## 2. 外部聯邦掛載語法 (In-Process ATTACH)

外部 Agent 或腳本若需跨庫查詢，請統一使用 **唯讀模式 (mode=ro)** 掛載，防止破壞底層大庫：

```sql
-- 掛載通用基石庫
ATTACH DATABASE 'file:/Volumes/D2024/data/gov-db-in/db/universal_keys.sqlite?mode=ro' AS gov_keys;

-- 掛載權威機關主檔庫
ATTACH DATABASE 'file:/Volumes/D2024/data/gov-db-in/db/master_agencies.sqlite?mode=ro' AS gov_agencies;
```

---

## 3. 🏛️ 核心資料表 (Core Tables) 結構與規模對照

實體庫中包含多張正規化對照表，依五大通用基石劃分：

### 🏛️ 基石一：組織與機關主檔 (`master_agencies.sqlite`)
* **`master_agencies`**：7,956 筆全台灣官方 OID 權威機關（含行政院、各部會署局、處組）。
  - 核心欄位：`agency_oid` (PK), `org_code`, `agency_name`, `parent_oid`, `level_type`, `attributes_json`
* **`publisher_aliases`**：708 筆 data.gov.tw 開放資料發布單位別名對齊映射表。
  - 核心欄位：`alias_id` (PK), `raw_publisher_name` (UNIQUE), `mapped_agency_oid`, `confidence_score`
* **`agency_genealogy`**：214 筆機關改制與歷史演進圖譜表（前身/存續機關關聯）。
  - 核心欄位：`id` (PK), `predecessor_name`, `successor_name`, `successor_oid`, `review_status`
* **`agency_mandates`**：處務規程法定掌理事項與業務關鍵字（虛擬層支援直連法規庫）。
  - 核心欄位：`mandate_id` (PK), `agency_oid`, `unit_name`, `law_article`, `mandate_text`, `keywords_json`
* **`domain_deployments`**：已實體展開之部會子專案（如 `tw-agro-db`, `tw-moi-db`）註冊表。

### 🗺️ 基石二：空間與地籍 (`universal_keys.sqlite`)
* **`admin_codes`**：480 筆 6 碼國家標準行政區劃代碼（22 縣市與 368 鄉鎮市區）。
  - 核心欄位：`admin_code` (PK), `city_name`, `district_name`
* **`zipcode_registry`**：372 筆全台行政區 3 碼/6 碼郵遞區號與路段範圍對照表。
  - 核心欄位：`zipcode` (PK), `city_name`, `district_name`, `scope_description`
* **`cadastral_registry`**：22 筆內政部全國地籍段號預備開口。
  - 核心欄位：`section_code` (PK), `city_name`, `district_name`, `section_name`

### 🌊 基石三：水系與環境 (`universal_keys.sqlite`)
* **`river_registry`**：1,377 筆全台水脈拓樸代碼（含水利署官方 122 幹流與 WRA-Civ 純化民間代碼）。
  - 核心欄位：`river_id` (PK), `river_name`, `main_basin`, `parent_river_id`, `river_order`, `code_status`
* **`station_registry`**：1,100 個水利署、氣象署與環境部水情/雨量/水質官方測站。
  - 核心欄位：`station_id` (PK), `station_name`, `station_type`, `agency_name`, `river_id`, `latitude`, `longitude`

### 🏢 基石四：法人與企業 (`universal_keys.sqlite`)
* **`corporate_registry`**：1,103 筆熱門上市櫃企業與國營事業 Seed 旁路快取（Pass-Through Cache）。
  - 核心欄位：`tax_id` (PK), `company_name`, `registered_address`, `admin_code`, `status`, `cached_at`
* **`npo_registry`**：23,218 筆全國登記 NGO、社團法人與 342 家農漁會主檔。
  - 核心欄位：`npo_id` (PK), `npo_name`, `npo_type`, `city_name`, `address`

### 📅 基石五：時間與日曆 (`universal_keys.sqlite`)
* **`calendar_registry`**：1,801 筆 2018-2026 行政院人事行政總處核定政府辦公日曆。
  - 核心欄位：`date_str` (PK, YYYY-MM-DD), `is_holiday`, `holiday_category`, `description`

---

## 4. 跨專案 JOIN 查詢實務範例

### 範例：跨部會資料發布單位 ➔ 官方機關全名 ➔ 行政區劃 JOIN 碰撞
```sql
SELECT 
    p.raw_publisher_name,
    m.agency_name,
    m.agency_oid,
    z.zipcode,
    z.city_name,
    z.district_name
FROM gov_agencies.publisher_aliases p
JOIN gov_agencies.master_agencies m ON p.mapped_agency_oid = m.agency_oid
LEFT JOIN gov_keys.zipcode_registry z ON m.agency_name LIKE '%' || z.district_name || '%'
WHERE p.raw_publisher_name = '水利署'
LIMIT 1;
```

---

## 5. 跨專案協同邊界與唯讀宣告

1. **嚴禁外部寫入**：`master_agencies.sqlite` 與 `universal_keys.sqlite` 乃全政府公共基準對照庫，外部 Agent 嚴禁執行任何未經審查之 `INSERT`、`UPDATE`、`DROP` 或 `ALTER`。
2. **領域業務資料庫隔離**：部會子專案（如農業部 `agro_integrated.sqlite`、衛福部 `med.db`）之垂直領域資料，應各自維護於該子專案目錄中，不得直接注入此通用底座。
