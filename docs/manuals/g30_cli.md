# g30_cli(1) -- 全台灣水系水文拓樸維度器控制台

## SYNOPSIS
`python src/modules/g30_hydrology_indexer/g30_cli.py` [*GLOBAL_FLAGS*] *COMMAND* [*ARGS...*]  
`python src/modules/g30_hydrology_indexer/g30_cli.py` `search` [*KEYWORD...*]  
`python src/modules/g30_hydrology_indexer/g30_cli.py` `trace` [*--direction down|up*] [*RIVER_CODE*]  
`python src/modules/g30_hydrology_indexer/g30_cli.py` `stations` [*--type rainfall|waterlevel|all*] [*RIVER_CODE*]  
`python src/modules/g30_hydrology_indexer/g30_cli.py` `hydrate` [*--no-wra*] [*--in-place*] [*FILE...*]  
`python src/modules/g30_hydrology_indexer/g30_cli.py` `sync-rivers` [*--upstream-jsonl PATH*] [*--force*]  
`python src/modules/g30_hydrology_indexer/g30_cli.py` `status`  

*(若於整合開發環境中，亦可使用本機快捷路由器 `./pa g30 ...`)*

## DESCRIPTION
**g30_cli.py** (G30) 是台灣全政府通用基石對照庫 (`tw-gov-db` / `GOV-300`) 的核心水文維度器模組，對應**基石三 (基石三 (Cornerstone 3: 水系與環境 Hydrology & River Topology): 水系與環境 Hydrology & River Topology)**。

本工具遵循 **CGS v2.4 (Pipeline-Native UNIX Standard)** 規範，並直接接軌台灣水利署與民間野溪延伸拓樸標準 **WRA-Civ (Water Resources Agency - Civilian Extended Topology)**：
1. **雙層編碼架構支援**：
   - 官方 6 碼權威編碼 (`is_civilian: 0`，如 `114000` 淡水河、`114022` 北勢溪、`114011` 三峽溪、`130000` 頭前溪主流、`151000` 濁水溪）。
   - 民間連字號延伸編碼 (`is_civilian: 1`，如 `130000-C04-C01` 代表頭前溪四級支流深山野溪）。
2. **微秒級親緣拓樸樹遍歷**：
   - 基於 `@` 分隔路徑 (`topology_path`) 實現純 SQL 前綴比對，百微秒內解析主流向下游（Ancestors / Downstream）或向源頭上游子樹（Descendants / Upstream）。
3. **外部跨部會資料流厚化 (Hydration)**：
   - 透過標準輸入輸出將全政府事件流、採購標案、水質測站資料注入 `plugins.gov_db.hydrology` 拓樸結構，而不污染各部會既有核心 Schema。
4. **自主無依賴優雅降級**：
   - 本地 `universal_keys.sqlite` 完整備份 1,380 筆純化台灣水脈資料與 1,095+ 跨部會水文測站。當外部環境缺少 `river_cli` 或指定 `--no-wra` 時，以純 Python 微拓樸引擎自主運作，絕不中斷服務。
5. **上游異動偵測與原子同步**：
   - 支援 `sync-rivers` 檢測上游 WRA-Civ JSONL 雜湊異動並執行事務性原子同步。

## COMMANDS
* `search` [*KEYWORD...*]:
  模糊搜尋水系名稱、主流或民間支流。
* `trace` [*--direction down|up*] [*RIVER_CODE*]:
  追蹤指定水脈的親緣拓樸路徑。預設 `down` 追溯流向出海口的主幹歷程（Ancestors）；`up` 查詢所有向源侵蝕的支流流域（Descendants）。
* `stations` [*--type rainfall|waterlevel|all*] [*RIVER_CODE*]:
  列出綁定在指定水系的雨量與水位水文監測站點。
* `hydrate` [*--no-wra*] [*--in-place*] [*FILE...*]:
  將外部 JSON/JSONL 資料串流注入水文拓樸屬性（於 `plugins.gov_db.hydrology` 欄位）。
* `sync-rivers` [*--upstream-jsonl PATH*] [*--force*]:
  從上游 WRA-Civ 拓樸註冊表 JSONL 執行增量與雜湊偵測同步至本機 `universal_keys.sqlite`。
* `status`:
  檢視 G30 模組就緒狀態、收錄水系筆數、官方/民間比例與測站數量。

## GLOBAL OPTIONS
* `-j`, `--json`:
  以單行緊湊 JSON 格式輸出，利於 jq 與 Unix Pipe 串流處理。
* `-q`, `--quiet`:
  靜音模式，抑制診斷與進度提示。
* `--pretty`:
  格式化縮排輸出 JSON 結構。
* `-h`, `--help`:
  顯示命令列說明檔案。

## ENVIRONMENT
* `DISABLE_WRA_CIV`: 若設定為 `1` 或 `true`，強制關閉外部 WRA-Civ CLI 呼叫，全面使用本機微拓樸引擎。
* `TW_GOV_DB_PATH`: 指定 `universal_keys.sqlite` 實體路徑。

## EXAMPLES
1. 查詢頭前溪主流資訊：
   ```bash
   python src/modules/g30_hydrology_indexer/g30_cli.py search "頭前溪" -j
   ```
2. 追溯油羅溪向下游至出海口的完整父節點拓樸鏈：
   ```bash
   python src/modules/g30_hydrology_indexer/g30_cli.py trace 130000-C04 --direction down -j
   ```
3. 追溯頭前溪水系向源頭的所有民間與官方支流子樹：
   ```bash
   python src/modules/g30_hydrology_indexer/g30_cli.py trace 130000 --direction up -j
   ```
4. 串流厚化水文資料至事件流：
   ```bash
   echo '{"event": "flood_alert", "river_code": "130000"}' | python src/modules/g30_hydrology_indexer/g30_cli.py hydrate -j
   ```
5. 檢視水文模組健康與註冊筆數：
   ```bash
   python src/modules/g30_hydrology_indexer/g30_cli.py status -j
   ```

*(備註：若在整合工作區根目錄，上述指令亦可簡寫為 `./pa g30 <command>`)*

## SEE ALSO
`g10_cli(1)`, `g20_cli(1)`, `g30_cli(1)`, `g40_cli(1)`, `g50_cli(1)`
