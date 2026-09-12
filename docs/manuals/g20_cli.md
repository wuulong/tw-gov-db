---
title: G20_CLI
section: 1
date: 2026-09-12
header: BMAD-PA User Commands
footer: CGS v2.4 Specification
---

# 📖 使用者手冊：`g20_cli.py` G20 空間地籍與地址基石 CLI 工具

`g20_cli.py` 是針對 `tw-gov-db` (`GOV-300`) 之 `g20_spatial_indexer` 模組所研發的高效空間與門牌處理工具，完全遵循 **CGS v2.4 (Pipeline-Native UNIX Standard)** 規範。提供全台灣門牌地址串流正規化、舊制縣市升格轉譯、門牌結構完整度指標 (AIS)、全國地籍段名段號解析與 3 碼/6 碼郵遞區號反查。

---

## 🚀 1. 命令列使用方式 (CLI Usage)

基本語法：
```bash
python events-2026Q3/gov-db-in/tw-gov-db/src/modules/g20_spatial_indexer/g20_cli.py [子命令] [選項]
# 或使用全域 pa 捷徑：
./pa g20 [子命令] [選項]
```

### 1. 門牌地址串流正規化與舊縣市升格轉譯 (`align-address`)
支援非貪婪中文正則剖析「縣市、鄉鎮市區、村里路街巷弄號」，自動將「桃園縣中壢市」轉譯為「桃園市中壢區」，並計算門牌完整度指標 (AIS 🟢 HIGH / 🟡 MEDIUM / 🔴 LOW)。

```bash
# 單一地址解析 (人類易讀格式)
./pa g20 align-address "桃園縣中壢市中正路1號"

# 單一地址輸出 JSON 格式
./pa g20 align-address "臺北市信義區信義路五段7號" -j

# UNIX 管道批次串流處理 (從 stdin 讀取)
printf "新竹縣竹北市光明六路10號\n台北縣板橋市中山路一段161號\n" | ./pa g20 align-address - -j
```

### 2. 全國地籍段名段號查詢與正則化 (`lookup-cadastral`)
將異質地籍段名（如「成功段」）與地號正則化為國家標準地籍程式碼 (`cadastral_id`，格式：`行政區碼_段碼_地號`)。

```bash
# 查詢特定地籍段
./pa g20 lookup-cadastral "成功段" -j

# 管道流式地籍比對
echo "文化段 0100" | ./pa g20 lookup-cadastral - -j
```

### 3. 郵遞區號與行政區劃反查 (`search-zipcode`)
透過 3 碼郵遞區號或縣市鄉鎮關鍵字，反查國家標準 6 碼行政區劃碼 (`admin_code`)。

```bash
# 依郵遞區號查詢
./pa g20 search-zipcode "302" -j

# 依鄉鎮區名稱查詢
./pa g20 search-zipcode "信義區" -j
```

### 4. 模組狀態檢查 (`status`)
檢視 `universal_keys.sqlite` 資料庫連線狀態與 `zipcode_registry` / `cadastral_registry` 筆數統計。

```bash
./pa g20 status -j
```

---

## 🔗 2. UNIX 管道串接範例 (UNIX Pipe Recipes)

### Recipe A: 農業部休閒農場門牌批量轉譯 (G20 ↔ GOV-A19)
```bash
# 將農業部休閒農場之文字門牌串流正規化，並萃取郵遞區號
./pa agro search "休閒農場" -j | \
  jq -r '.[].address' | \
  ./pa g20 align-address - -j | \
  jq '.[] | {cleaned_address: .normalized_address, zipcode: .zipcode, ais: .ais_score}'
```

### Recipe B: 跨時序空間地籍碰撞 (G20 ↔ G40)
```bash
# 比對特定重劃區地籍段號與年度辦公日曆
echo "成功段 0050" | ./pa g20 lookup-cadastral - -j | \
  jq -r '.[].admin_code' | \
  xargs ./pa g40 bucket "113年度" -j
```

---

## 🐍 3. Python API 調用 (Programmatic API)

```python
from modules.g20_spatial_indexer.g20_cli import parse_address_string

res = parse_address_string("桃園縣中壢市中正路1號")
print(res["normalized_address"]) # 桃園市中壢區中正路1號
print(res["zipcode"])            # 320
print(res["ais_level"])          # HIGH
```
