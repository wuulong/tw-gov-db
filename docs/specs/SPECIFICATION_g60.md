# G60 全政府法人、企業與農漁會維度器模組 (g60_corporate_indexer) 業務與系統規格書

- **模組名稱**: `g60_corporate_indexer`
- **所屬專案 / 權威代號**: `tw-gov-db` / `GOV-300` (全政府通用基石對照庫)
- **規範版本**: `v2.4` (CGS Pipeline-Native UNIX Standard)
- **基石定位**: 基石四 (Cornerstone 4: 法人與企業 Corporate & NPO)
- **對齊標準**: 財政部稅籍登記規範、經濟部商業發展署商工登記標準、農業部農漁會組織法規

---

## 🏛️ 業務功能本位 4 大核心情境 (4 Core Business Scenarios)

### 1. 全國 8 碼營利事業統一編號驗證 (Universal BAN Validator)
* **業務痛點**:
  跨部會申報名單、投標履歷、食安稽查名冊中，經常存在筆誤、缺碼、或偽造的 8 碼統一編號（Business Accounting Number, BAN）。傳統比對若直接發動外部 HTTP 請求將造成嚴重網路延遲與伺服器負荷。
* **業務規格與實作機制**:
  - 提供 100% 純 Python、微秒級零依賴的邏輯檢核演演算法。
  - **雙軌制度完美相容**:
    - **舊制規範（2023 年 3 月以前）**: 權重 `[1, 2, 1, 2, 1, 2, 4, 1]`，各乘積取各位數和後，總和需整除 10。若第 7 位為 7，支援雙重分支判定。
    - **新制規範（財政部 2023 年 4 月實施）**: 因應號碼資源有限，放寬判定規則，總和可整除 5 或 10 均判定有效。
  - **串流管線過濾 (Stream Filtering)**: 支援從標準輸入讀取大量字串或名冊，即時篩選出合法統編。

### 2. 全國農會、漁會與非營利法人消歧義對齊 (NPO & Farmers Association Resolver)
* **業務痛點**:
  農業部、農糧署與地方政府資料中，常以俗稱或非官方簡稱標註農漁會（如「新埔農會」、「板農」、「吉安農會超市」），導致無法與基石地理庫（G20）或法規庫（G30）正確關聯。
* **業務規格與實作機制**:
  - 收錄全台 302 家各級農會（全國農會、直轄市/縣市農會、基層鄉鎮市區農會）與 40 家漁會之權威名冊。
  - 提供名稱正規化管線：自動剝除分支機構綴詞（「信用部」、「推廣部」、「生鮮超市」），結合 G20 空間行政區推導出完整官方全名（如 `新埔農會` ➔ `新竹縣新埔鎮農會`）。
  - 對齊農漁會統一識別程式碼與稅籍扣繳統編。

### 3. 企業資料旁路透傳快取 (Pass-Through Cache Layer)
* **業務痛點**:
  全台立案營利事業超過 160 萬家，若全量離線儲存將使 SQLite 超過 1GB，失去隨插即用輕量優勢；若完全依賴雲端 API，則斷線或無 API Key 時系統停擺。
* **業務規格與實作機制**:
  - 採取「本機快取優先 + 旁路透傳快取 (Pass-Through Cache)」架構。
  - 本機預載精選上市櫃公司、國營事業與重要合作社作為權威種子（Seed Cache）。
  - 當查詢未命中且具備連線能力時，可選擇發動經濟部商業發展署開放 API 穿透抓取，並寫回本地 `corporate_registry` 資料表。

### 4. 跨部會主體身分穿透與權責機關推導 (Cross-Agency Identity Linkage)
* **業務痛點**:
  取得廠商或法人名稱時，無法立即得知其「業務目的主管機關」（例如判斷農會主管機關為農業部，公司登記為經濟部商業發展署，合作社為內政部），難以進行法規權責對齊（G30）。
* **業務規格與實作機制**:
  - G60 內建法人型態特徵分類器，自動分析組織後綴與程式碼特徵，標註其推定主管機關程式碼（對應 G30 `master_agencies`）。

---

## 📊 SQLite Schema 結構 (universal_keys.sqlite)

### 1. `corporate_registry` (法人與企業旁路透傳快取表)
```sql
CREATE TABLE IF NOT EXISTS corporate_registry (
    tax_id VARCHAR(8) PRIMARY KEY,      -- 8碼統一編號
    company_name VARCHAR(256) NOT NULL, -- 公司/商號名稱
    registered_address VARCHAR(256),    -- 登記地址
    admin_code VARCHAR(8),              -- 所屬行政區程式碼 (對齊 G20 admin_codes)
    status VARCHAR(32) DEFAULT 'ACTIVE',-- 營業狀態 (ACTIVE, DISSOLVED, SUSPENDED)
    source VARCHAR(32) DEFAULT 'SEED',  -- 資料來源 (SEED, GCIS_API, LOCAL_INPUT)
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_corp_company_name ON corporate_registry(company_name);
CREATE INDEX IF NOT EXISTS idx_corp_admin_code ON corporate_registry(admin_code);
```

### 2. `npo_registry` (農會、漁會與非營利組織法人主檔)
```sql
CREATE TABLE IF NOT EXISTS npo_registry (
    npo_id VARCHAR(32) PRIMARY KEY,     -- 組織機構程式碼或扣繳統編
    npo_name VARCHAR(256) NOT NULL,     -- 官方正式名稱
    short_name VARCHAR(64),             -- 常見通俗簡稱 (如 板農, 新埔農會)
    npo_type VARCHAR(32) NOT NULL,      -- 類型 (FARMERS_ASSOC, FISHERY_ASSOC, COOPERATIVE, FOUNDATION, NGO)
    level VARCHAR(16),                  -- 層級 (NATIONAL, PROVINCIAL, COUNTY, DISTRICT)
    city_name VARCHAR(32),              -- 所在縣市 (對齊 G20)
    admin_code VARCHAR(8),              -- 鄉鎮市區行政程式碼 (對齊 G20)
    address VARCHAR(256),               -- 登記地址
    parent_id VARCHAR(32),              -- 上級輔導農會程式碼 (如全國農會或縣市農會)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_npo_name ON npo_registry(npo_name);
CREATE INDEX IF NOT EXISTS idx_npo_short_name ON npo_registry(short_name);
CREATE INDEX IF NOT EXISTS idx_npo_type ON npo_registry(npo_type);
CREATE INDEX IF NOT EXISTS idx_npo_admin_code ON npo_registry(admin_code);
```

---

## 🧮 演演算法規格 (Algorithm Specifications)

### 1. 台灣 8 碼統一編號驗證 (BAN Validation Algorithm)
* **輸入**: 任意字串或 8 位數字。
* **前處理**: 去除空格、破折號，驗證格式是否為 8 位純數字。
* **權重矩陣**: $W = [1, 2, 1, 2, 1, 2, 4, 1]$
* **演演算法步驟**:
  1. 各位乘積 $P_i = D_i 	imes W_i$
  2. 計算乘積各位數和 $S_i = \lfloor P_i / 10 
floor + (P_i mod 10)$
  3. 初步加總 $S = \sum_{i=1}^{8} S_i$
  4. **舊制 (Legacy) 檢驗**:
     - 若 $D_7 
eq 7$: 合格條件為 $S mod 10 == 0$。
     - 若 $D_7 == 7$: $P_7 = 28$ ($S_7 = 10$)。若以 $S_7 = 1$ 計演算法（即 $S - 10 + 1 = S - 9$），則當 $S mod 10 == 0$ 或 $(S - 9) mod 10 == 0$（等價於 $S mod 10 == 9$）時合格。
  5. **新制 (2023 財政部規範) 檢驗**:
     - 規則放寬：$S mod 5 == 0$ 或 $S mod 10 == 0$。若 $D_7 == 7$，同樣檢驗替代總和是否能被 5 整除。
* **輸出**:
  ```json
  {
    "tax_id": "04595257",
    "is_valid": true,
    "valid_by_legacy": true,
    "valid_by_current": true,
    "has_special_rule_7": false,
    "checksum": 40
  }
  ```

### 2. 農漁會消歧義規則 (NPO Disambiguation Heuristic)
1. **精確比對 (Exact Match)**：比對 `npo_name` 與 `short_name`。
2. **後綴剝除比對 (Suffix Stripping)**：
   - 剝除 `["信用部", "推廣部", "供銷部", "保險部", "超市", "直銷站", "本部", "辦事處"]` 後再次比對。
3. **行政區外推比對 (Geo-Prefix Inference)**：
   - 若使用者輸入「新埔農會」，比對 G20 行政區典「新埔鎮」屬於「新竹縣」，合成候選「新竹縣新埔鎮農會」比對。
