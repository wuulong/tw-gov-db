---
title: G40_CLI
section: 1
date: 2026-09-12
header: BMAD-PA User Commands
footer: CGS v2.4 Specification
---

# 📖 使用者手冊：`g40_cli.py` G40 全政府時間、辦公日曆與時序維度器 CLI 工具

`g40_cli.py` 是針對 `tw-gov-db` (`GOV-300`) 之 `g40_temporal_indexer` 模組所研發的高效 CLI 工具，完全遵循 **CGS v2.4 (Pipeline-Native UNIX Standard)** 規範。提供全政府異質日期清洗、人事行政總處/地方政府辦公行事曆法定出勤判定、跨度工作天計算、季度/會計年度時序維度展開、純 Python 緊湊農曆（1900-2100 年雙向轉換、生肖、天干地支）、二十四節氣天文常數計算與 UNIX Pipe 流式串接。

---

## 🚀 1. 命令列使用方式 (CLI Usage)

基本語法：
```bash
python events-2026Q3/gov-db-in/tw-gov-db/src/modules/g40_temporal_indexer/g40_cli.py [子命令] [選項]
# 或使用全域 pa 捷徑：
./pa g40 [子命令] [選項]
```

### 1. 異質日期正規化 (`clean-date`)
支援繁體中文民國格式、斜線、小數點、連字號、緊湊碼 (7/8 碼)、季度與會計年度，統一轉換為標準 ISO-8601 與西元/民國對照。

```bash
# 民國年月日中文解析
./pa g40 clean-date "民國113年8月22日" -j

# 季度解析
./pa g40 clean-date "113Q3" -j

# 會計年度解析
./pa g40 clean-date "113年度" -j

# UNIX 管道批次流式處理 (--stdin)
printf "113/08/22\n112-10-10\n113Q1\n" | ./pa g40 clean-date -i -j
```

### 2. 政府法定工作日與假期屬性查詢 (`check`)
直連 `universal_keys.sqlite` 之 `calendar_registry` 資料表，查詢特定日期是否放假、是否為補行上班日、假別類別與法規事由。

```bash
# 查詢 2024 春節補行上班日 (週六出勤)
./pa g40 check "2024-02-17" -j

# 查詢民國日期除夕
./pa g40 check "113/02/09" -j

# 管道流式過濾工作日
cat dates.txt | ./pa g40 check -i -j | jq '.[] | select(.is_working_day == true)'
```

### 3. 時序區間工作日與放假日統計 (`range`)
計算兩日期區間內法定日曆天、法定工作天與放假/例假日天數，支援 `--working-days-only` 過濾。

```bash
# 統計 2024 春節前後工作日與放假日
./pa g40 range "2024-02-08" "2024-02-15" -j

# 僅取出工作日清單
./pa g40 range "2024-02-01" "2024-02-28" --working-days-only -j
```

### 4. 會計年度與季度時序區間展開 (`bucket`)
將政府標案、統計季報或會計年度展開為完整的日曆邊界與包含之工作日序列。

```bash
# 展開 2024 第三季 (2024-07-01 ~ 2024-09-30)
./pa g40 bucket "2024Q3" -j

# 展開民國 113 年度
./pa g40 bucket "113年度" -j
```

### 5. 農曆轉換、生肖、干支與二十四節氣 (`lunar`)
純 Python 零外部依賴微秒級天文解算，支援西曆轉農曆、農曆轉西曆、天干地支生肖、傳統節日與 24 節氣查詢。

```bash
# 西曆轉農曆 (春節初一)
./pa g40 lunar 2024-02-10 -j

# 農曆轉西曆 (端午節反查)
./pa g40 lunar --to-solar 113-05-05 -j

# 查詢指定年份二十四節氣公曆對照表
./pa g40 lunar --terms --year 2024 -j

# 管道串接清洗文字農曆日期
echo "農曆113年五月初五" | ./pa g40 clean-date -i -j
```

### 6. 辦公行事曆資料庫初始化與狀態 (`init-calendar`, `status`)
```bash
# 匯入雙北開放資料政府行事曆至 SQLite
./pa g40 init-calendar -j

# 查看 G40 日曆庫健康度與涵蓋年份
./pa g40 status -j
```

---

## 🔗 2. UNIX 管道串接範例 (UNIX Pipe Recipes)

### Recipe A: 政府標案履約天數計算 (G40 ↔ G10)
```bash
# 自政府標案 GRB 提取簽約與驗收日期，計算實際履約法定工作天
./pa g10 search "石門水庫" -j | \
  jq -r '.results[0] | "\(.start_date) \(.end_date)"' | \
  xargs ./pa g40 range -j | jq '{working_days: .total_working_days, holidays: .total_holidays}'
```

### Recipe B: 農業休市與天災出勤判定 (G40 ↔ GOV-A19)
```bash
# 串接農產品交易日期，校驗是否為法定補班或例假日
./pa agro query-crop "香蕉" -j | \
  jq -r '.[].transaction_date' | \
  ./pa g40 check -i -j | \
  jq '.[] | select(.is_holiday == true)'
```

---

## 🐍 3. Python API 調用 (Programmatic API)

在其他部會子專案或 AI Agent 腳本中可直接 import 呼叫：

```python
from modules.g40_temporal_indexer.g40_cli import clean_date_string

# 1. 異質日期清洗
info = clean_date_string("113/08/22")
print(info["date_str"])    # 2024-08-22
print(info["minguo_year"]) # 113

# 2. 季度展開
q_info = clean_date_string("113Q3")
print(q_info["start_date"]) # 2024-07-01
print(q_info["end_date"])   # 2024-09-30
```
