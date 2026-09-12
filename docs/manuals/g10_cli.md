---
title: G10_CLI
section: 1
date: 2026-09-12
header: BMAD-PA User Commands
footer: CGS v2.4 Specification
---

# 📖 使用者手冊：`g10_cli.py` G10 政府研究報告探勘與典藏 CLI 工具

`g10_cli.py` 是針對 `tw-gov-db` (`GOV-300`) 之 `g10_report_miner` 模組所研發的高效研究報告探勘工具，完全遵循 **CGS v2.4 (Pipeline-Native UNIX Standard)** 規範。支援全量 GRB 57.6萬筆研究計畫多維檢索、按需採集 PDF/CSV、開放資料總表探勘與國家圖書館 GPN 案號碰撞對位。

---

## 🚀 1. 命令列使用方式 (CLI Usage)

基本語法：
```bash
python events-2026Q3/gov-db-in/tw-gov-db/src/modules/g10_report_miner/g10_cli.py [子命令] [選項]
# 或使用全域 pa 捷徑：
./pa g10 [子命令] [選項]
```

### 1. GRB 57.6 萬筆政府研究計畫智慧檢索 (`search-grb`)
支援計畫名稱關鍵字 (`--kw`)、主持人姓名 (`--pi`) 檢索，支援管道輸入與單行緊湊 JSON 輸出。

```bash
# 依關鍵字查詢前 5 筆
./pa g10 search-grb -k "石門水庫" -n 5 -j

# 依計畫主持人查詢
./pa g10 search-grb -p "王大明" -n 3

# 管道流式關鍵字檢索
echo "智慧農業" | ./pa g10 search-grb -j
```

### 2. 機制 A 碰撞對位：GRB 案號對位國家圖書館 GPN (`match-gpn`)
將 GRB 研究計畫案號與國圖 GPN 下載服務對位，取得正式政府出版品 GPN 與全文可達性。

```bash
# 查詢特定 GRB 案號對應 GPN
./pa g10 match-gpn "PG10901-0123" -j

# 管道流式案號對位
cat projkeys.txt | ./pa g10 match-gpn -j
```

### 3. Open Data 總表探勘與註冊 (`ingest-catalog`)
線上下載並解析政府開放資料總表，自動歸並行布機關至權威 OID。

```bash
./pa g10 ingest-catalog "https://data.gov.tw/dataset/..." -j
```

### 4. 二階段按需採集下載實體報告 (`fetch`)
給定報告 UID 串流，自動從快取或遠端下載實體 PDF/CSV 報告檔案至本機存放庫。

```bash
./pa g10 fetch "UID_12345" -j
```

### 5. 模組健康度與狀態看板 (`status`)
查詢 G10 報告索引庫總筆數、快取命中率與代號系統矩陣。

```bash
./pa g10 status -j
```

---

## 🔗 2. UNIX 管道串接範例 (UNIX Pipe Recipes)

### Recipe A: 研究計畫履約期與法定工作日計算 (G10 ↔ G40)
```bash
./pa g10 search-grb -k "水利" -n 1 -j | \
  jq -r '.results[0] | "\(.start_date) \(.end_date)"' | \
  xargs ./pa g40 range -j | jq '{workdays: .total_working_days, holidays: .total_holidays}'
```

### Recipe B: 計畫發布機關歷史改制回溯 (G10 ↔ G30)
```bash
./pa g10 search-grb -k "農田水利" -n 1 -j | \
  jq -r '.results[0].agency_name' | \
  ./pa g30 resolve-org --stdin -j
```

---

## 🐍 3. Python API 調用 (Programmatic API)

```python
from modules.g10_report_miner.g10_core import search_grb_projects

res = search_grb_projects(kw="石門水庫", limit=5)
print(f"找到 {res['total']} 筆計畫，首筆標題: {res['results'][0]['title']}")
```
