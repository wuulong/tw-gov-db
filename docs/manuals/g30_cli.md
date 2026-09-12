---
title: G30_CLI
section: 1
date: 2026-09-12
header: BMAD-PA User Commands
footer: CGS v2.4 Specification
---

# 📖 使用者手冊：`g30_cli.py` G30 全政府法規處務規程與虛擬圖譜 CLI 工具

`g30_cli.py` 是針對 `tw-gov-db` (`GOV-300`) 之 `g30_mandate_indexer` 模組所研發的高效 CLI 工具，完全遵循 **CGS v2.4 (Pipeline-Native UNIX Standard)** 規範。支援跨部會歷史機關動態對位、組科職掌配對、OID 字典批次回填與法規採礦管線。

---

## 🚀 1. 命令列使用方式 (CLI Usage)

基本語法：
```bash
python events-2026Q3/gov-db-in/tw-gov-db/src/modules/g30_mandate_indexer/g30_cli.py [子命令] [選項]
```

### 1. JIT 執行期輕量動態組織推導 (`resolve-org`)
支援精準歷史機關比對與跨部會巨觀推導（如「第二河川局」➔「經濟部水利署第二河川分署」），並自動附帶現行官方 OID。

```bash
# 單一查詢 (人類易讀格式)
python g30_cli.py resolve-org "第二河川局"

# JSON 輸出格式
python g30_cli.py resolve-org "南區工程處" -j

# UNIX 管道批次流式處理 (--stdin)
printf "第二河川局\n南區工程處\n新竹林區管理處\n" | python g30_cli.py resolve-org --stdin -j
```

### 2. 官方 OID 批次回填落地 (`backfill-oid`)
自動遍歷 `agency_genealogy` 資料表，以官方 6,937 筆 OID 字典為已確認繼承機關回填權威 `successor_oid`。

```bash
python g30_cli.py backfill-oid -j
```

### 3. 法規文本改制演進採礦 (`parse-laws`)
雙軌直連 `law_cli genealogy`，全量解析全國法規資料庫組織法規與廢止公告，抽取改制事件。

```bash
# 僅輸出評級結果
python g30_cli.py parse-laws -j

# 解析並寫入 SQLite 資料庫
python g30_cli.py parse-laws --save -j
```

### 4. 業務關鍵字與組科職掌配對 (`match-mandate`)
根據處務規程組科法定職掌，自動配對開放資料集或業務關鍵字的主管科室與法規 PCode。

```bash
python g30_cli.py match-mandate "農水路工程改善" -j
```

### 5. 歷史演進圖譜查詢與人工修補 (`genealogy`, `patch`, `patch-oid`)
```bash
# 查詢待修補條目
python g30_cli.py genealogy --status NEEDS_PATCH -j

# 透過 ID 更新既有規則
python g30_cli.py patch --id 239 '{"successor_name": "交通部高速公路局各區養護工程分局"}'

# 補充特定條目 OID
python g30_cli.py patch-oid 46 --oid "2.16.886.101.20003.20069.20001"
```

### 6. 自我描述 JSON Schema (`schema`)
輸出符合 Draft-2020-12 標準之規格描述：
```bash
python g30_cli.py schema
```

---

## 🐍 2. Python API 調用 (Programmatic API)

在其他部會子專案或 AI Agent 腳本中可直接 import 呼叫：

```python
import sqlite3
from modules.g30_mandate_indexer.g30_cli import resolve_single_org, get_canonical_oid

conn = sqlite3.connect("events-2026Q3/gov-db-in/tw-gov-db/data/master_agencies.sqlite")
cursor = conn.cursor()

# 1. JIT 動態組織解析
res = resolve_single_org("第二河川局", cursor)
print(res["successor"])     # 經濟部水利署第二河川分署
print(res["successor_oid"]) # 2.16.886.101.20003.20007.20014.20025

# 2. 官方權威 OID 查詢
oid = get_canonical_oid("農業部")
print(oid)                  # 2.16.886.101.20003.20064
```
