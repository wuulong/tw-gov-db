# G30 高級延伸與跨模組協同規格書 (ADVANCED_SPEC_g50)

- **模組名稱**: `g30_hydrology_indexer`
- **所屬專案**: `tw-gov-db` / `GOV-300` (全政府通用基石對照庫)
- **規範版本**: `CGS v2.4` (Pipeline-Native UNIX Standard)
- **關聯基石**: 基石三 (Cornerstone 3: 水系與環境 Hydrology & Environmental Sensors)
- **上游核心**: WRA-Civ (1,397+ 筆水脈拓樸與 3D 幾何)

---

## 🚀 1. 設計哲學與 UNIX Pipe 原生哲學 (Pipeline-Native Philosophy)

G30 在水文流域治理中扮演「水理與行政基石的轉譯中樞」。

1. **零磁碟碰撞與純串流過濾 (Zero-Disk Impact Streaming)**：
   - 支援從標準輸入接收 WRA-Civ 的 `jsonl` 串流，在記憶體管道中進行跨基石注水（Hydration），絕不頻繁寫入硬碟或造成 Context Token 浪費。
2. **非阻塞 Stdin 探針與超時緩衝**：
   - 採用 `select.select` 0.3 秒緩衝機制，完美相容多行程管道鏈式啟動時間差，杜絕終端掛死 (Hang)。
3. **優雅降級與環境自適應 (Graceful Degradation)**：
   - 啟動時動態探測是否有 `RiverExploration/scripts/river_cli.py`。
   - 若探測成功且未禁用，啟動「WRA-Civ 拓樸增強模式 (Enhanced Mode)」；
   - 若探測失敗或下達 `--no-wra`，自動降級至「本機獨立基石模式 (Standalone Base Mode)」，僅查詢 `universal_keys.sqlite` 本地快取，絕不拋出未捕獲異常。

---

## 🔗 2. 5 大跨部會 UNIX Pipeline 實戰配方 (Pipeline Recipes)

### 配方一：水系檢索 ➔ 官方基石注水 ➔ 行政區地緣統計 (G20 + G30)
* **情境**：搜尋頭前溪水系全量水脈，動態注入 G20 行政區劃與 G30 管轄分署，並進行地緣聚合。
* **管線指令**：
  ```bash
  python3 events/AIBooks/RiverExploration/scripts/river_cli.py search -b "頭前溪" -f jsonl |     ./pa g50 hydrate -i - |     jq -r '.plugins.gov_db | [.g20_district, .g30_competent_agency] | @tsv' | sort | uniq -c
  ```

### 配方二：野溪祖先沿線追溯 ➔ 沿岸水利署水情測站聯防
* **情境**：給定山區野溪（如鹿寮坑溪 `130000-C04`），沿 `@` 向上/向下切片出所有親緣水脈，管道傳入 G30 自動抽出沿線所有雨量站與水位測站。
* **管線指令**：
  ```bash
  ./pa g50 trace "130000-C04" --downstream -j | ./pa g50 stations -i - | jq .
  ```

### 配方三：颱風豪雨時序 (G40) ➔ 水位暴漲警戒水脈 ➔ 影響灌區農會 (G60)
* **情境**：結合 G40 歷史颱風停班停課事件，沿著水系拓樸反推受影響的支流，並經由 G30 對齊農田水利署灌區農會。
* **管線指令**：
  ```bash
  ./pa g40 check 2024-07-25 -j | ./pa g50 risk-basins --level HIGH -j | ./pa g60 resolve -i -
  ```

### 配方四：高程落差運算 ➔ 淹水潛勢與地籍門牌對位 (G20)
* **情境**：計算野溪匯流點高程落差，過濾低窪衝擊區，秒級轉入 G20 反查門牌地號。
* **管線指令**：
  ```bash
  ./pa g50 search -c "新竹縣" --max-elevation 30 -j | ./pa g20 cadastral -i -
  ```

### 配方五：WRA-Civ 上游水脈版本同步與差異審計
* **情境**：當 WRA-Civ 發布新版資料時，執行原子同步與差異報告。
* **管線指令**：
  ```bash
  ./pa g50 sync-rivers --check -j
  ```

---

## 🔄 3. 版本同步演演演算法與防護機制 (sync-rivers)

1. **SHA-256 內容指紋探測**:
   - 計算上游 JSONL 之 Hash，若與 `spec_version_registry` 記錄相同則直接略過。
2. **SQLite 交易原子性**:
   - `BEGIN TRANSACTION` 批次寫入 `INSERT OR REPLACE INTO river_registry`，確保中斷不壞庫。
3. **軟刪除防護 (Soft-delete)**:
   - 比對舊庫程式碼，若上游已移除，標記為 `status = 'DEPRECATED'`，維持歷史查詢向下相容性。
