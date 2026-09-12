# G20 空間地籍與地址基石模組 (g20_spatial_indexer) 系統與業務規格書

- **模組名稱**: `g20_spatial_indexer`
- **專案 / 權威代碼**: `tw-gov-db` / `GOV-300` (通用基石對照庫)
- **規範版本**: `v2.4` (CGS Pipeline-Native UNIX Standard)
- **基石定位**: 基石二 (Cornerstone 2: 行政區劃、郵遞區號與地籍段號)

---

## 🏛️ 業務功能本位 4 大實戰情境 (4 Core Business Scenarios)

### 1. 全國行政區劃代碼 (Admin Code) 權威對照與升格消歧義
* **業務情境**: 提供 480 筆 6 碼國家標準行政區劃代碼（22 縣市 + 368 鄉鎮市區）對照。
* **歷史改制適配**: 自動識別舊制縣市（如「桃園縣中壢市」自動對齊至新制「桃園市中壢區」`3300200`，並於 `attributes_json` 標註升格歷程）。

### 2. 郵遞區號 (Zipcode) 與門牌正規化引擎 (Address Normalizer)
* **業務情境**: 微秒級解析純文字門牌（如「新竹縣竹北市光明六路123號」），自動抽出：
  - `zipcode`: 302
  - `admin_code`: 10004010 (竹北市)
  - `canonical_address`: 新竹縣竹北市光明六路123號
* **Pipeline 原生介面**: 支援自 `stdin` 輸入多行地址文字流，並即時輸出 JSON/TSV 串流。

### 3. 全國地籍段名段號 (Cadastral ID) 格式正規化
* **業務情境**: 將中文地籍描述（如「新竹縣竹北市縣政段100號」）正規化為權威對照鍵 `cadastral_id` (`10004010-00100`)。
* **跨部會對接**: 作為 `tw-moi-db` (`GOV-A13`) 實體 GIS 多邊形比對的主鍵輸入。

### 4. 高效記憶體對照與本機快取 (InMemory / Fast Lookup)
* **業務情境**: 模組啟動時自動快取 372 筆 3 碼郵遞區號與行政區劃表，提供毫秒級零 I/O 阻礙之反查 API。

---

## 📊 SQLite Schema 結構與通用表定質 (universal_keys.sqlite)

### `admin_codes` (行政區劃表)
- `admin_code` (TEXT PRIMARY KEY): 6 碼或 8 碼行政區劃碼。
- `county_name` (TEXT): 縣市名稱 (如 "新竹縣")。
- `town_name` (TEXT): 鄉鎮市區名稱 (如 "竹北市")。
- `attributes_json` (TEXT): 包含舊制歷史對照與改制年份。

### `zipcode_registry` (郵遞區號對照表)
- `zipcode` (TEXT PRIMARY KEY): 3 碼郵遞區號 (如 "302")。
- `county_name` (TEXT): 縣市名稱。
- `town_name` (TEXT): 鄉鎮市區名稱。
- `admin_code` (TEXT): 對應之行政區劃代碼。
- `attributes_json` (TEXT): 半結構化擴充資訊。

---

## 🛠️ CGS v2.4 CLI 命令規格 (`g20_cli.py`)

- `g20_cli.py align-address [--input FILE]`: 門牌地址串流正規化。
- `g20_cli.py lookup-cadastral [--query TEXT]`: 地籍號正規化查詢。
- `g20_cli.py search-zipcode [--query TEXT]`: 郵遞區號與行政區查詢。
- `g20_cli.py status`: 子模組健康檢查與快取數據盤點。
