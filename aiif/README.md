# tw-gov-db (GOV-300 全台灣政府通用基石對照庫) 跨專案 AI 協同接駁總覽

> **遵守規格**：PGS v3.2 (專案治理規格書) & CGS v2.4 (CLI 治理規範)  
> **專案代號**：`GOV-300` (方案 A 權威行政院機關代碼 `300000000A`，總母專案: `tw-gov-db`, `govdb`, `gov`)  
> **核心使命**：作為全台灣政府開放資料 (data.gov.tw) 與各部會專案之「通用對照基石 (Mother Core Infrastructure)」，消弭部會資料孤島、發布單位別名歧義、異質民國年格式與地理空間代碼斷層。

---

## 1. 專案定位與角色

`tw-gov-db` 是台灣政府資料治理與語意實體對照的大一統基礎建設：
- **全域母專案 (Mother Core Infrastructure)**：為全生態系提供 5 大維度通用基石（組織 OID、空間地址地籍、水系測站、企業統編與農漁會、政府辦公日曆與節氣）。
- **部會子專案語意基底**：對接農業部 (`GOV-A19` `tw-agro-db`)、衛福部 (`GOV-A18` `tw-med-db`)、內政部 (`GOV-A13`)、經濟部 (`GOV-A09`) 等領域庫，保證全政府實體代碼一致性與零幻覺 Grounding。

---

## 2. 🏛️ 六大模組 (G01, G10 ~ G50) 子庫與能力全覽

底層主要託管於兩個核心 SQLite 實體資料庫（`master_agencies.sqlite` 與 `universal_keys.sqlite`，以及報告典藏庫 `report_index.sqlite`）。外部 Agent 可依業務維度直接定位子模組：

| 模組代號 | 模組名稱 | 核心資料庫與實體表 (含規模) | 核心功能與資料源 |
| :---: | :--- | :--- | :--- |
| **`G01`** | `g01_report_miner` | `report_index.sqlite`<br>(`report_index`, `grb_projects`, `sys_master_catalog_registry`) | 政府研究報告探勘與二階段按需採集，涵蓋 GRB 57.6 萬筆計畫、國圖 GPN 與開放資料總表 |
| **`G10`** | `g10_mandate_indexer` | `master_agencies.sqlite`<br>(`agency_genealogy`: 214 筆, `agency_mandates`: 4 筆, `publisher_aliases`: 708 筆, `master_agencies`: 7,956 筆 OID) | 跨部會組織法規、處務規程、歷史機關沿革追溯（如改制前後對位）、發布者別名 OID 對齊 |
| **`G20`** | `g20_spatial_indexer` | `universal_keys.sqlite`<br>(`admin_codes`: 119~480 筆, `zipcode_registry`: 117~372 筆, `cadastral_registry`: 22 筆) | 全國 6 碼標準行政區劃代碼、3/6 碼郵遞區號反查、舊制縣市升格清洗、門牌地址正規化與地籍號索引 |
| **`G30`** | `g30_hydrology_indexer` | `universal_keys.sqlite`<br>(`river_registry`: 1,377 筆, `station_registry`: 1,100 筆) | 全台 1,380 筆 WRA-Civ 水文拓樸微秒級追溯、上下游親緣展開、水利署與氣象署水情測站水理關聯 |
| **`G40`** | `g40_corporate_indexer` | `universal_keys.sqlite`<br>(`corporate_registry`: 1,103 筆 Seed, `npo_registry`: 23,218 筆) | 8 碼統一編號新舊制雙軌校驗、長文本統編過濾、全台農漁會拓樸消歧義、GCIS 旁路快取 (Pass-Through) |
| **`G50`** | `g50_temporal_indexer` | `universal_keys.sqlite`<br>(`calendar_registry`: 1,801 筆 2018-2026 日曆) | 異質民國年/西元年極速清洗轉碼 ISO-8601、行政院核定辦公日曆、法定工作日計算、陰陽曆與二十四節氣轉換 |

---

## 3. 協同接駁契約索引 (Minimal Viable Context)

外部 AI Agent 或跨專案調用時，**嚴禁耗費大量 Token 暴力掃描全庫私有原始碼**，請依據需求直接精準讀取對應接駁檔案：

* 🚀 **呼叫 CLI/API 進行機關、地址、水文、統編或日曆轉換** ➔ 請讀取：[prompt_for_api.md](prompt_for_api.md)
* 🗄️ **掛載 (ATTACH) 或直接唯讀查詢 SQLite 實體資料庫** ➔ 請讀取：[prompt_for_db.md](prompt_for_db.md)

---

## 4. 資料主權與安全邊界宣告

1. **純客觀公共基準，零個人隱私**：本專案僅收錄政府機關法定編碼、官方地理水文、公開法人與公開日曆，不儲存任何個人隱私資訊。
2. **安全唯讀與防禦**：外部 Agent 僅享有 **唯讀查詢權 (mode=ro)**，嚴禁任意更動底層通用基石資料庫。
3. **四階路徑解析保證**：支援顯式參數、環境變數 (`GOV_DB_DIR`, `GOV_DB_SHARED_DIR`)、外接磁碟 (`/Volumes/D2024`) 與本地 fallback，確保跨環境不中斷。
