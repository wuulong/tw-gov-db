# G20 空間地籍與地址基石模組 (g20_spatial_indexer) 業務與系統規格書 (SPECIFICATION.md)

- **模組名稱**: `g20_spatial_indexer`
- **所屬專案 / 權威程式碼**: `tw-gov-db` / `GOV-300` (通用基石對照庫)
- **規範版本**: `v2.4` (CGS Pipeline-Native UNIX Standard)
- **基石定位**: 基石二 (Cornerstone 2: 行政區劃、郵遞區號、地籍號與門牌正規化)

---

## 🏛️ 業務功能本位 4 大實戰情境 (4 Core Business Scenarios)

### 1. 權威行政區劃對照與歷史升格消歧義 (Entity Master Profile & Disambiguation)
* **業務痛點**: 跨部會開放資料常出現舊行政區劃名稱（如「桃園縣中壢市」、「臺南縣新營市」、「高雄縣鳳山市」），傳統 SQL 比對直接失效。
* **業務規格與實作機制**:
  - 提供 480 筆 6 碼/8 碼國家標準行政區劃程式碼 (Admin Code) 權威主檔案對照。
  - 內建**歷史升格與改制消歧義引擎**：自動將「桃園縣中壢市」轉譯為標準「桃園市中壢區」(`68000020`)，並於 `attributes_json` 標註改制年份 (2014) 與舊稱紀錄，確保 100% 機關歷史資料連鎖。

### 2. 領域衍生指標：空間涵蓋度與門牌品質風險防禦 (Domain Metrics & Quality Alerts)
* **業務痛點**: 開放資料地址文字極度髒亂（含全半形空格、贅字、異常號碼），導致 GIS 計算與物流/統計癱瘓。
* **衍生業務指標與防禦檢驗**:
  - **門牌結構完整度指標 (Address Integrity Score, AIS)**：評估門牌是否具備「縣市 + 鄉鎮市區 + 路段 + 門牌號」，輸出品質燈號（🟢 完整定址 / 🟡 缺縣市預設匹配 / 🔴 無法定位）。
  - **極值與髒字串防爆清洗**: 自動濾除「路邊」、「無門牌」、「旁邊」等非標準字串，保留 `canonical_address` 乾淨定址。

### 3. 複合式空間聚合檢視表 (Analytical Views & Insight Queries)
* **業務痛點**: 業務分析師與 AI Agent 每次都需要自行撰寫複雜的多表 JOIN 來同時取得郵遞區號、縣市、鄉鎮區與行政程式碼。
* **標準檢視 (SQL Views)**:
  - `v_g20_admin_zipcode_master`: 聚合行政區劃程式碼、郵遞區號、縣市別、鄉鎮市區別與熱點標籤。
  - `v_g20_address_quality_audit`: 門牌正規化品質稽核檢視表，標示需要人工介入校正之模糊門牌。

### 4. 高效記憶體對照與 Pipeline 串流解析 (InMemory Fast Lookup & UNIX Pipeline)
* **業務情境**: 支援從 `stdin` 輸入數萬行地址流，利用記憶體內 372 筆 3 碼郵遞區號對照快取，實現微秒級無 I/O 阻塞之門牌正規化 JSON/TSV 串流輸出。

---

## 📊 SQLite Schema 結構與通用表定質 (universal_keys.sqlite)

### `admin_codes` (行政區劃權威表)
```sql
CREATE TABLE IF NOT EXISTS admin_codes (
    admin_code TEXT PRIMARY KEY,    -- 6碼/8碼行政區劃碼 (如 "68000020")
    county_name TEXT NOT NULL,       -- 權威縣市名 (如 "桃園市")
    town_name TEXT NOT NULL,         -- 權威鄉鎮市區名 (如 "中壢區")
    attributes_json TEXT            -- 半結構化歷史修訂與別名
);
```

### `zipcode_registry` (郵遞區號權威表)
```sql
CREATE TABLE IF NOT EXISTS zipcode_registry (
    zipcode TEXT PRIMARY KEY,       -- 3碼郵遞區號 (如 "320")
    county_name TEXT NOT NULL,
    town_name TEXT NOT NULL,
    admin_code TEXT NOT NULL,       -- 外鍵關聯至 admin_codes
    attributes_json TEXT
);
```

---

## 🛠️ CGS v2.4 CLI 命令規格 (`g20_cli.py`)

- `g20_cli.py align-address [--input FILE] [-j]`: 門牌地址串流正規化與 Zipcode 對齊。
- `g20_cli.py lookup-cadastral [--query TEXT] [-j]`: 地籍號與段名正規化查詢。
- `g20_cli.py search-zipcode [--query TEXT] [-j]`: 郵遞區號與行政區查詢。
- `g20_cli.py status [-j]`: 子模組健康檢查與快取資料盤點。
