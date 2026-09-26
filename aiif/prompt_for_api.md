# tw-gov-db: API / CLI 調用協同契約 Prompt (AI Agent Cheat Sheet)

> **調用主體**：Antigravity、Cursor、Claude Code、部會子專案 (`tw-agro-db`, `tw-med-db` 等)、外部 Agent、Shell 管道。  
> **遵守規格**：CGS v2.4 (Pipeline-Native, Token-Saving, Clean JSON, Master-Sub Router)。  
> **專案代號**：`GOV-300` (母專案簡碼: `govdb`, `gov`)。

---

## 1. 核心 CLI 工具進入點

```bash
# 途徑 A：總控 CLI (專案根路徑: events-2026Q3/gov-db-in/tw-gov-db)
python scripts/govdb_cli.py <subcommand> [flags]

# 途徑 B：六大模組獨立 CLI 入口
python src/modules/g01_report_miner/g01_cli.py <subcommand> [flags]
python src/modules/g10_mandate_indexer/g10_cli.py <subcommand> [flags]
python src/modules/g20_spatial_indexer/g20_cli.py <subcommand> [flags]
python src/modules/g30_hydrology_indexer/g30_cli.py <subcommand> [flags]
python src/modules/g40_corporate_indexer/g40_cli.py <subcommand> [flags]
python src/modules/g50_temporal_indexer/g50_cli.py <subcommand> [flags]
```

---

## 2. 常用子命令速查表

### 2.1 全域查詢中樞 (`govdb_cli.py`)
1. **`status`**：動態掃描所有基石資料庫 Table/View 筆數統計看板。
2. **`stat`**：顯示各資料庫對齊率與健康度指標。
3. **`search <query>`**：搜尋機關主檔 (關鍵字/OID/機關代號，支援 Unix Pipe)。
4. **`tree <target>`**：展開指定機關之上下級組織樹階層。
5. **`alias <publisher>`**：查詢開放資料發布單位別名與官方 OID 映射。
6. **`domains`**：檢視全政府已展開之部會子專案清單與狀態。

### 2.2 六大維度模組專案指令

* **`G01` 政府研究報告探勘 (`g01_cli.py`)**：
  - **`status`**：檢視 GRB/GPN 報告索引庫筆數、快取狀態與總表地圖。
  - **`catalogs`**：查詢已註冊與驗證之 Open Data 總表清冊。
  - **`ingest-catalog --oid <OID> --url <URL>`**：線上下載、剖析並註冊 Open Data 總表。
  - **`fetch <report_uid>`**：二階段按需採集下載實體報告 PDF/CSV（支援 Pipe 傳入 UID）。

* **`G10` 機關法規職掌與組織演進 (`g10_cli.py`)**：
  - **`resolve-org <org_name>`**：動態將舊制/歷史機關名稱解析為最新存續機關（如「第二河川局」➔「經濟部水利署第二河川分署」）。
  - **`alias <publisher>`**：開放資料發布單位別名對齊官方 OID。
  - **`match-mandate <query>`**：依據業務關鍵字配對法規條文與法定掌理事項。
  - **`genealogy`**：查詢機關改制演進圖譜與審核狀態。

* **`G20` 空間地籍與地址基石 (`g20_cli.py`)**：
  - **`align-address <address>`**：台灣地址字串正規化解析，支援歷史舊縣市升格清洗並帶出 3 碼/6 碼行政區劃與郵遞區號。
  - **`search-zipcode <query>`**：郵遞區號與縣市鄉鎮區代碼查詢。
  - **`lookup-cadastral <query>`**：地籍段名段號反查。
  - **`status`**：檢視 G20 空間索引器資料庫與筆數。

* **`G30` 水系流域與水情測站 (`g30_cli.py`)**：
  - **`search <keyword>`**：多維度檢索全台水脈（支援流域 `-b`、縣市 `-c`、官方公告 `--official-only`）。
  - **`trace <river>`**：水脈上下游拓樸親緣追溯（`--upstream` 展開支流樹，`--downstream` 追溯至出海口）。
  - **`stations <river>`**：查詢指定水脈沿線關聯之水情/雨量測站。
  - **`sync-rivers`**：同步 WRA-Civ 水脈資料庫並保持拓樸純化。
  - **`status`**：顯示水脈庫 (1,377 條) 與測站庫 (1,100 站) 看板。

* **`G40` 法人統編與農漁會 (`g40_cli.py`)**：
  - **`check <tax_id>`**：8 碼統一編號新舊邏輯雙軌驗證。
  - **`extract <text>`**：自長文本串流中萃取合法統一編號（支援 Pipe）。
  - **`lookup <tax_id|name>`**：查詢法人主檔（本機 Seed 快取優先，未命中時透傳 API）。
  - **`resolve <npo_name>`**：全台農會、漁會與非營利組織消歧義解析。

* **`G50` 時間日曆與節氣 (`g50_cli.py`)**：
  - **`clean-date <date_str>`**：民國年/西元年、異質符號或季度（如 `113/08/22`, `113Q3`）轉碼為標準 ISO-8601。
  - **`check <date>`**：依行政院人事行政總處日曆判定放假日、例假日或補班日。
  - **`range <start> <end> [--working-days-only]`**：展開日期區間並統計工作天數。
  - **`lunar <date>`**：國曆農曆互轉與二十四節氣計算。

---

## 3. 標準輸出調用規範 (`--json / -j`)

* **機器/Agent 消費 (強制推薦)**：傳入 `--json`（或 `-j`），保證 stdout 輸出純淨單行或緊湊 JSON，零 ANSI 碼與雜訊。
* **日誌分流保證**：所有除錯、診斷與進度提示一律自動分流至 `stderr`，絕對不干擾 Unix Pipe。

---

## 4. Pipeline 管道串聯實戰範例 (Unix Pipe Cookbook)

### 場景 A：地址清洗 ➔ 郵遞區號反查 (零暫存檔)
```bash
echo "台北縣板橋市府中路30號" | python src/modules/g20_spatial_indexer/g20_cli.py align-address - -j | jq .
```

### 場景 B：異質民國年清洗 ➔ 政府工作日判定
```bash
echo "113/10/10" | python src/modules/g50_temporal_indexer/g50_cli.py clean-date --stdin -j | \
  jq -r .iso_date | python src/modules/g50_temporal_indexer/g50_cli.py check --stdin -j
```

### 場景 C：水脈拓樸追溯 ➔ 關聯測站檢索
```bash
python src/modules/g30_hydrology_indexer/g30_cli.py trace "新店溪" --downstream -j | \
  jq -r '.downstream_path[0]' | python src/modules/g30_hydrology_indexer/g30_cli.py stations - -j
```

---

## 5. 跨程式語言呼叫範例 (Python Direct Import & Subprocess)

### 途徑 1：Core SDK 直接 Import 呼叫 (微秒級，零 Subprocess 開銷)
```python
from src.core.base_adapter import BaseDomainAdapter

adapter = BaseDomainAdapter(root_agency_oid="2.16.886.101")
# 將發布者別名對齊至官方權威 OID
canonical_oid = adapter.align_publisher_oid("水利署")
print(canonical_oid)
```

### 途徑 2：Subprocess 呼叫模組 CLI
```python
import subprocess, json

proc = subprocess.run(
    ["python", "src/modules/g50_temporal_indexer/g50_cli.py", "clean-date", "113-08-22", "-j"],
    capture_output=True, text=True, check=True
)
date_info = json.loads(proc.stdout)
print(f"標準化日期: {date_info.get('iso_date')}")
```
