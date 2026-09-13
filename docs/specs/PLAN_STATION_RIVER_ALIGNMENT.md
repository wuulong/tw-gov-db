# 📡 全台跨部會水文測站水系歸位治理與資料工程全域實施計畫 (Implementation Plan & Todo Checklist)

本計畫對齊規格書 [`SPEC_STATION_RIVER_ALIGNMENT_GOVERNANCE.md`](file:///Users/wuulong/github/bmad-pa/events-2026Q3/gov-db-in/tw-gov-db/docs/specs/SPEC_STATION_RIVER_ALIGNMENT_GOVERNANCE.md) (v1.2.0)，旨在將中央（氣象署 CWA、水利署 WRA、環境部 MOENV、農村水保署 ARDTC）與地方政府（水利/工務局）約 2,500 ~ 3,000 座雨量、水位、水質與淹水感測測站，透過誠實的水理雙軌哲學（水位站身在何河、雨量站雨落何區）與三階演演算法管線，完整建立標準化歸位治理機制與資料落地。

---

## 總體執行看板 (Master Todo Checklist)

```text
[Phase 1] 資料表結構遷移與種子保護 (Schema Migration & Protection Lock)
  ├── [ ] 1.1 universal_keys.sqlite 資料表結構擴充 (basin_code, alignment_status, attributes_json)
  ├── [ ] 1.2 建立高效索引 (idx_station_align_status, idx_station_basin)
  └── [ ] 1.3 現存 5 筆種子測站標記為 VERIFIED (信心度 1.0，啟動防覆寫保護鎖)

[Phase 2] 全台跨部會測站清冊採集與標準化注入 (Multi-Agency Station Ingestion)
  ├── [ ] 2.1 中央氣象署 (CWA) 全台氣象/雨量測站清單 (~550 站) 採集與正規化
  ├── [ ] 2.2 經濟部水利署 (WRA) 全台防汛水位/雨量測站清單 (~700 站) 採集與正規化
  ├── [ ] 2.3 環境部 (MOENV) 重要河川水質監測站 (~300 站) 採集與正規化
  ├── [ ] 2.4 農村水保署 (ARDTC) 土石流/野溪專屬雨量站 (~150 站) 採集與正規化
  ├── [ ] 2.5 地方政府水利局 (LOCAL_GOV) 重點區排/淹水感測器 (~300+ 站試點) 採集與正規化
  └── [ ] 2.6 批量寫入 station_registry，初始狀態設為 UNASSIGNED (避免重複插入)

[Phase 3] 三階歸位演演算法引擎實裝 (Three-Tier Alignment Engine Implementation)
  ├── [ ] 3.1 階梯 1 (Tier 1)：官方權威清冊文本解析器 (Authoritative Text Extraction)
  │         - 比對 river_name / basin_name ➔ 直接標記 VERIFIED (confidence=1.0)
  ├── [ ] 3.2 階梯 2 (Tier 2)：Point-in-Polygon (PIP) 集水區面多邊形交集運算器
  │         - 載入全台 122 條主要水系集水區多邊形 (Catchment Polygons)
  │         - 射線法 (Ray Casting) 判定測站所屬 basin_code
  │         - 雨量站 ➔ 標記 WATERSHED_BASIN (confidence=0.85)
  │         - 水位站 ➔ 配合水系線段計算 Buffer (<300m ➔ AUTO_GEO, 歧義 ➔ CANDIDATE_AMBIGUOUS)
  └── [ ] 3.3 階梯 3 (Tier 3)：分水嶺山脊與邊界地理仲裁器 (Ridge & Boundary Arbiter)
            - 離島判斷 (澎湖/金門/馬祖/綠島/蘭嶼) ➔ OFFSHORE_ISLAND (OFFSHORE_NO_RIVER)
            - 邊界/分水嶺頂點判斷 ➔ ORPHAN_RIDGE (RIDGE_WATERSHED_DIVIDE)，保留雙邊候選

[Phase 4] CLI 工具鏈擴充與治理審計控制台 (CLI & Governance Audit Tools)
  ├── [ ] 4.1 g30_cli.py stations --audit 審計統計摘要命令 (輸出各狀態比例與統計表)
  ├── [ ] 4.2 g30_cli.py stations --status [STATUS] 條件篩選與 JSON 導出
  ├── [ ] 4.3 g30_cli.py verify-station [ID] 人工仲裁命令 (寫入 attributes_json.history_trail 並上鎖)
  └── [ ] 4.4 CGS v2.4 規範對齊 (更新 g30_cli.spec.md 與 manuals/g30_cli.md)

[Phase 5] 單元測試、整合測試與保護鎖驗證 (Testing & Safety Verification)
  ├── [ ] 5.1 資料表遷移與欄位完整性測試
  ├── [ ] 5.2 VERIFIED 防覆寫保護鎖測試 (演演算法執行時跳過 VERIFIED 記錄)
  ├── [ ] 5.3 三階演演算法單元測試 (Mock CWA, WRA, MOENV 測站)
  └── [ ] 5.4 執行全套 pytest tests/ (確保 32+ 測試全綠燈)

[Phase 6] 系統工程、專書與工作報告歸檔 (Documentation & Task Archiving)
  ├── [ ] 6.1 建立正式任務工作報告 workmgr/task-reports/TR_T260913-STATION-ALIGN01.md
  ├── [ ] 6.2 更新專案總任務清單 TASKS.md
  ├── [ ] 6.3 更新書籍第三章 03_30_g30_hydrology_indexer.md 增補測站水系歸位章節
  └── [ ] 6.4 執行 sanitize_locale_terms.py --fix 進行全域台灣語境淨化
```

---

## 各階段詳細規格與檢查點 (Detailed Phase Specifications)

### Phase 1: 資料表結構遷移與種子保護
- **目標檔案**：`events-2026Q3/gov-db-in/tw-gov-db/data/universal_keys.sqlite`
- **操作步驟**：
  1. 執行 SQLite DDL 新增 `basin_code VARCHAR(32)`, `alignment_status VARCHAR(24) DEFAULT 'UNASSIGNED'`, `attributes_json TEXT DEFAULT '{}'`。
  2. 建立索引：`idx_station_align_status`, `idx_station_basin`。
  3. 將現有的 5 筆種子資料（秀朗橋、新店、大漢溪等）更新為 `alignment_status = 'VERIFIED'`, `confidence_score = 1.0`。
- **檢查標準**：`PRAGMA table_info(station_registry)` 正確顯示新增欄位，且既有 5 筆資料之 `alignment_status` 均為 `VERIFIED`。

### Phase 2: 全台跨部會測站清冊採集與標準化注入
- **涵蓋機關與預期筆數**：
  1. **中央氣象署 (CWA)**：約 550 站（包含有人氣象站、無人自動氣象站、自動雨量站），類型標記為 `RAINFALL`。
  2. **經濟部水利署 (WRA)**：約 700 站（河川水位站、水庫水位站、防汛雨量站），類型標記為 `WATER_LEVEL` 或 `RAINFALL`。
  3. **環境部 (MOENV)**：約 300 站（全國地面水體水質監測站），類型標記為 `WATER_QUALITY`。
  4. **農村水保署 (ARDTC)**：約 150 站（土石流觀測站雨量計），類型標記為 `RAINFALL`。
  5. **地方政府 (LOCAL_GOV)**：新北、台北、台南、高雄等市區淹水感測器與區排站，類型標記為 `INUNDATION` 或 `WATER_LEVEL`。
- **檢查標準**：採集後透過單一正規化器注入 `station_registry`，總測站數達 2,000 筆以上，無重複 `station_id`。

### Phase 3: 三階歸位演演算法引擎實裝
- **核心程式模組**：`src/modules/g30_hydrology_indexer/station_aligner.py`
- **階梯分工**：
  - **Tier 1 (文本匹配)**：對 WRA / MOENV 自帶河川名稱者，直接對齊 `river_registry` 賦予 `river_code`，標記 `VERIFIED`。
  - **Tier 2 (集水區面交集 PIP)**：使用內建純 Python 射線法（Ray Casting）或幾何演演算法，對 CWA 雨量站計算所屬 122 大流域多邊形，標記 `WATERSHED_BASIN`。水位站則進一步比對距離線段。
  - **Tier 3 (邊界/分水嶺)**：離島測站標記 `OFFSHORE_ISLAND`；邊界爭議標記 `ORPHAN_RIDGE` 並保留 `candidate_rivers`。
- **保護鎖原則**：任何 `alignment_status == 'VERIFIED'` 的紀錄絕對不被演演算法更動。
- **檢查標準**：全量測站執行後，無任何測站殘留未處理的空白未知狀態，所有測站均具有明確狀態碼與對應的 `attributes_json`。

### Phase 4: CLI 工具鏈擴充與治理審計控制台
- **核心程式模組**：`src/modules/g30_hydrology_indexer/g30_cli.py`
- **新增命令**：
  - `g30_cli.py stations --audit`：輸出各狀態分佈統計（表格格式與百分比）。
  - `g30_cli.py stations --status ORPHAN_RIDGE -j`：輸出指定狀態的測站明細。
  - `g30_cli.py verify-station <station_id> --river <river_code>`：人工介入覆寫並落鎖。
- **檢查標準**：指令符合 CGS v2.4 規範，支援 `-j/--json`, `-q/--quiet`，`stdout` 與 `stderr` 分離。

### Phase 5: 測試與保護鎖驗證
- **測試檔案**：`tests/test_station_alignment.py`
- **測試重點**：
  - 驗證 `VERIFIED` 測站不會被批次運算覆寫。
  - 驗證雨量站落入集水區被正確標為 `WATERSHED_BASIN`。
  - 驗證水位站能正確識別距離與 `AUTO_GEO` / `CANDIDATE_AMBIGUOUS`。
  - 驗證 `history_trail` 稽核軌跡之寫入。
- **檢查標準**：`pytest tests/` 全部通過。

### Phase 6: 系統工程、專書與工作報告歸檔
- **檔案與報告**：
  - 在 `workmgr/task-reports/` 建立 `TR_T260913-STATION-ALIGN01.md`。
  - 在 `TASKS.md` 註冊任務。
  - 更新專書第三章水系維度器之章節。
  - 全域執行語境淨化確保符合繁體中文台灣語境規範。
