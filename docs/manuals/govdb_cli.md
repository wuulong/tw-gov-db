# 📖 使用者手冊：`govdb_cli.py` 底座 DB 存取工具

`govdb_cli.py` 是針對 `master_agencies.sqlite` 提供的高效檢索 CLI 與 Python API 工具。雙向相容於「人類命令列查詢」與「AI 代理程式 JSON 資料調用」。

---

## 🚀 1. 命令列使用方式 (CLI Usage)

基本語法：
```bash
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py [子命令] [選項]
```

### 1. 搜尋機關主檔 (`search`)
搜尋包含指定關鍵字（名稱、OID 或機關代號）的機關。

```bash
# 人類視覺化輸出
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py search 經濟部

# AI JSON 輸出
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py search 農業部 --json
```

### 2. 檢索機關組織樹 (`tree`)
獲取指定機關的上級與下屬機關組織結構。

```bash
# 人類視覺化輸出
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py tree 內政部

# AI JSON 輸出
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py tree 2.16.886.101.20003.20001 --json
```

### 3. 查詢發布單位別名對齊 (`alias`)
查詢開放資料平台發布單位對齊至權威 OID 的映射記錄。

```bash
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py alias 農業部 --json
```

### 4. 檢視全資料庫物件與 Table/View 筆數 (`status`)
動態掃描所有資料庫 (`master_agencies.sqlite`, `universal_keys.sqlite`) 內所有 Table 與 View 的筆數。

```bash
# 人類視覺化列表
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py status

# 別名透傳
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py tables
/usr/bin/python3 tw-gov-db/scripts/govdb_cli.py views -j
```

---

## 🐍 2. Python API 調用 (Programmatic API)

在其他程式或代理程式腳本中可直接 import 呼叫：

```python
from scripts.govdb_cli import search_agencies, get_agency_tree, get_db_status

# 1. 搜尋機關
results = search_agencies("水利署", limit=5)

# 2. 獲取全庫 Table/View 統計
status_info = get_db_status()
```
print(results)

# 獲取組織樹
tree = get_agency_tree("內政部警政署")
print(tree["children"])
```
