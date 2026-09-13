# G30 全政府水系流域與水情測站維度器模組 (g30_hydrology_indexer) 業務與系統規格書

- **模組名稱**: `g30_hydrology_indexer`
- **所屬專案 / 權威代號**: `tw-gov-db` / `GOV-300` (全政府通用基石對照庫)
- **規範版本**: `v2.4` (CGS Pipeline-Native UNIX Standard)
- **基石定位**: 基石三 (Cornerstone 3: 水系與環境 Hydrology & Environmental Sensors)
- **水文拓樸權威來源 (Upstream SSOT)**: WRA-Civ (Civilian Water Resources Agency Hydrology System / 1,380 筆純化水脈拓樸，全面收斂官方 6 碼)
- **對齊標準**: 經濟部水利署水文編碼規範、環境部水質監測站標準、中央氣象署自動雨量站編碼、SPEC-GOV-G30-STA-001 測站歸位治理規格

---

## 🏛️ 業務功能本位 5 大核心情境 (5 Core Business Scenarios)

### 1. 全國水系雙層編碼與 WRA-Civ 親緣拓樸樹 (Hydrological Topology & Double-Layer Coding)
* **業務痛點**:
  跨部會資料庫（經濟部水利署、農業部農田水利署、環境部水保署）在記錄水系時存在嚴重斷層：官方公告河川僅 122 條幹流，而絕大多數山區土石流、農田灌排與生態系系採樣區均位於「無官方 6 碼的小溪或野溪支流」，導致資料無法關聯與溯源。
* **業務規格與實作機制**:
  - 全面接軌 **WRA-Civ 水系親緣拓樸體系** 作為單一真實來源 (SSOT)。
  - **雙層編碼支援**:
    - **官方 6 碼權威編碼 (`is_civilian: 0`)**: 如 `114000` (淡水河)、`114022` (北勢溪)、`114011` (三峽溪)、`130000` (頭前溪)、`151000` (濁水溪)。
    - **民間連字號延伸編碼 (`is_civilian: 1`)**: 如 `130000-C04` (油羅溪)、`130000-C04-C01` (王爺坑溪)。
  - **親緣路徑樹 (`topology_path`)**:
    - 採用 `@` 符號連接親緣鏈 (如 `0@130000@130000-C04@130000-C04-C01`)。
    - 支援微秒級上下游雙向追溯 (Upstream Source & Downstream Mainstream)。

### 2. 本機微型拓樸引擎與外部套件解耦 (Lightweight Micro Topology Engine & Decoupling)
* **業務痛點**:
  `RiverExploration` (WRA-Civ) 包含龐大的 3D 幾何、OSM 爬蟲與專書產製套件。若 `tw-gov-db` 強制依賴其 Library，在獨立容器或精簡環境中將引發依賴地獄與崩潰。
* **業務規格與實作機制**:
  - **資料層全量收納**: 將 WRA-Civ 1,380 筆水脈核心欄位同步快取至 `universal_keys.sqlite` 之 `river_registry`，確保離線與單兵環境自給自足。
  - **程式碼輕量適配**: G30 內部實裝純 Python 微型拓樸引擎 (`river_topology.py`)，自主實現上下游查詢與樹狀展開，不盲目拷貝外部程式碼。
  - **環境自適應與優雅降級**:
    - 提供 `--no-wra` 與 `DISABLE_WRA_CIV=1` 顯式禁用開關。
    - 外部有 `river_cli` 時支援動態擴充高階幾何；無外部套件時自動降級至本地獨立基石模式，保證 100% 穩定不掛死。

### 3. 水理、空間與機關跨基石聯防 (Hydro-Spatial-Agency Triad Linkage)
* **業務痛點**:
  水文是自然地理邊界，而政府治理是行政區劃邊界（如一條溪流跨越多個鄉鎮市區）。水利署各河川分署管轄範圍與地方公所防災責任難以精確對照整合。
* **業務規格與實作機制**:
  - 繼承 WRA-Civ 權威的「四階縣市歸屬仲裁」(`primary_county`)。
  - 對齊 **G20 (`admin_codes`)** 國家行政區碼，明確標註水脈地緣。
  - 對齊 **G30 (`master_agencies`)**，自動標註水利署一河局至十河局的管轄分署 OID。

### 4. 全政府水情測站智慧關聯與雙軌水理治理 (Universal Sensor Anchoring & Governance)
* **業務痛點**:
  氣象署雨量站、水利署水位站、環境部水質站各自獨立，沒有統一關聯至標準河川程式碼，且過去將雨量站強行直線歐幾里得距離投影至河床線上，違背實體水理。
* **業務規格與實作機制**:
  - 依據 `SPEC_STATION_RIVER_ALIGNMENT_GOVERNANCE.md` (v1.2.0) 確立水理雙軌原則：水位站身在何河 (`LOCATED_ON_RIVER`)、雨量站雨落何區 (`DRAINS_INTO_BASIN`)。
  - 維護 `universal_keys.sqlite` 內的 `station_registry` (已收納 1,095+ 官方全量測站，含 839 筆 `VERIFIED` 水位站與 243 筆 `WATERSHED_BASIN` 雨量站)。
  - 擴充 `basin_code`、`alignment_status` 與 `attributes_json`，內建三階歸位演演算法與防覆寫保護鎖。
  - 提供專屬採集清洗重建工具 `ingest_wra_stations.py` (支援 `--reset` 與 `--download-latest` 自動由開放資料平台重建)。

### 5. WRA-Civ 版本感知與冪等原子同步 (Version Drift & Atomic Sync)
* **業務痛點**:
  民間探勘與社群調查持續演進，WRA-Civ 會不定期發布新版水脈與更正拓樸。基石庫必須具備受控的同步與版本漂移防護。
* **業務規格與實作機制**:
  - 內建 `sync-rivers` 子命令，以 SHA-256 內容指紋偵測上游更新。
  - 採 SQLite 交易保護 (`BEGIN TRANSACTION ... COMMIT`) 進行冪等原子寫入 (Upsert)。
  - 具備軟刪除防護 (Soft-delete): 上游移除或重新編碼的水脈標記為 `DEPRECATED`，保留歷史資料關聯相容性。

---

## 📊 SQLite Schema 結構 (universal_keys.sqlite)

### 1. `river_registry` (全台灣水系與流域拓樸主檔表 - 增強版)
```sql
CREATE TABLE IF NOT EXISTS river_registry (
    river_code VARCHAR(32) PRIMARY KEY,      -- 6碼官方編號 (130000) 或民間延伸碼 (130000-C04)
    river_name VARCHAR(128) NOT NULL,        -- 河流/溪流正式名稱 (如 頭前溪、鹿寮坑溪)
    basin_name VARCHAR(64),                  -- 所屬大流域幹流名稱 (如 頭前溪水系)
    parent_code VARCHAR(32),                 -- 母水脈程式碼 (匯入之水脈)
    topology_path VARCHAR(256) NOT NULL,     -- WRA-Civ 拓樸親緣路徑 (如 0@130000@130000-C04)
    stream_order INTEGER DEFAULT 1,          -- 河階/支流層次 (幹流=1, 一級支流=2...)
    is_civilian BOOLEAN DEFAULT 0,           -- 0: 水利署官方公告, 1: 民間延伸野溪
    primary_county VARCHAR(32),              -- 仲裁歸屬縣市 (如 新竹縣)
    admin_code VARCHAR(8),                   -- 對齊 G20 國家行政區碼
    confluence_lon FLOAT,                    -- 匯流點經度
    confluence_lat FLOAT,                    -- 匯流點緯度
    status VARCHAR(16) DEFAULT 'ACTIVE',     -- 狀態 (ACTIVE 正常, DEPRECATED 已廢止/整併)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_river_name ON river_registry(river_name);
CREATE INDEX IF NOT EXISTS idx_river_topo ON river_registry(topology_path);
CREATE INDEX IF NOT EXISTS idx_river_basin ON river_registry(basin_name);
CREATE INDEX IF NOT EXISTS idx_river_county ON river_registry(primary_county);
```

### 2. `station_registry` (環境/氣象/水文測站主檔表 - 雙軌水理治理版)
```sql
CREATE TABLE IF NOT EXISTS station_registry (
    station_id VARCHAR(64) PRIMARY KEY,      -- 測站程式碼 (如 C0A980, 1140H02)
    station_name VARCHAR(128) NOT NULL,      -- 測站名稱
    station_type VARCHAR(32),                -- 類型 (WATER_LEVEL, RAINFALL, WATER_QUALITY, INUNDATION)
    agency_name VARCHAR(128),                -- 所屬機關 (經濟部水利署, 中央氣象署, 環境部, 地方水利局)
    river_code VARCHAR(32),                  -- 身在何河 (LOCATED_ON_RIVER, 水位站外鍵關聯 river_registry)
    basin_code VARCHAR(32),                  -- 雨落何區 (DRAINS_INTO_BASIN, 宏觀集水流域程式碼)
    admin_code VARCHAR(8),                   -- 所在行政區程式碼 (外鍵關聯 admin_codes)
    latitude FLOAT,                          -- 緯度 (WGS84)
    longitude FLOAT,                         -- 經度 (WGS84)
    alignment_status VARCHAR(24) DEFAULT 'UNASSIGNED', -- 狀態 (VERIFIED 🔒, WATERSHED_BASIN, AUTO_GEO, UNASSIGNED)
    attributes_json TEXT DEFAULT '{}',       -- 治理履歷本體 (含 relation_type, confidence_score, history_trail)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_station_river ON station_registry(river_code);
CREATE INDEX IF NOT EXISTS idx_station_basin ON station_registry(basin_code);
CREATE INDEX IF NOT EXISTS idx_station_type ON station_registry(station_type);
CREATE INDEX IF NOT EXISTS idx_station_align_status ON station_registry(alignment_status);
```

---

## 🧮 演演演演算法規格 (Algorithm Specifications)

### 1. 微型親緣拓樸路徑解析演演演演算法 (Topology Path Resolution)
* **親緣格式**: `0@BASIN@STREAM_1@STREAM_2@...`
* **祖先追溯 (Ancestors / Downstream Search)**:
  - 對 `topology_path` 進行 `@` 字串拆解，排除根結點 `0` 與當前節點，其餘元素即為由大幹流到直接母溪的直系祖先序列。時間複雜度 $O(1)$。
* **子孫展開 (Descendants / Upstream Search)**:
  - 利用 SQL B-Tree 前綴匹配：`SELECT * FROM river_registry WHERE topology_path LIKE ? AND river_code != ?`，傳入 `current_path + "@%"`。時間複雜度 $O(\log N)$。

### 2. Plugins 命名空間注水演演演演算法 (Plugin Hydration)
* 當讀取外部 WRA-Civ JSONL 時，主結構保持不可變性，僅於 `plugins.gov_db` 注入基石中繼資料：
  ```json
  "plugins": {
    "gov_db": {
      "g20_admin_code": "10004080",
      "g30_competent_agency": "經濟部水利署第二河川分署",
      "g30_agency_oid": "2.16.886.101.20003.20007.20015",
      "g50_monitoring_stations_count": 3
    }
  }
  ```
