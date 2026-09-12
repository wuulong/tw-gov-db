# g60_cli(1) -- 全政府法人、企業與農漁會維度器控制台

## SYNOPSIS
`./pa g60` [*GLOBAL_FLAGS*] *COMMAND* [*ARGS...*]  
`./pa g60` `check` [*--strict*] [*--new-only*] [*TAX_ID...*]  
`./pa g60` `lookup` [*--tsv*] [*--no-remote*] [*QUERY...*]  
`./pa g60` `resolve` [*NPO_NAME...*]  
`./pa g60` `pipe` [*--extract-tax-id*]  
`./pa g60` `status`  

## DESCRIPTION
**g60_cli.py** (G60) 是台灣全政府通用基石對照庫 (`tw-gov-db` / `GOV-300`) 的核心維度器模組，對應**基石四 (Cornerstone 4: 法人與企業 Corporate & NPO)**。

本工具遵循 **CGS v2.4 (Pipeline-Native UNIX Standard)** 規範，提供：
1. **純 Python 雙軌統一編號驗證**：加權除 10 舊制、第 7 位數為 7 特例、以及 2023 年 4 月財政部除 5/10 新制雙重規則。
2. **長文本串流統編萃取濾網**：自長文本、公告、PDF 轉文字中自動抽離合法統編，自動剔除日期偽碼。
3. **全台各級農會與漁會拓樸消歧義**：自動剝除分支機構綴詞（信用部、生鮮超市），將不規範簡稱對齊至官方正式全名與組織代碼。
4. **企業法人 Pass-Through 快取查詢**：本機 `corporate_registry` 快取優先，支援離線驗證與遠端旁路透傳。

## COMMANDS
* `check` [*TAX_ID...*]:
  驗證 8 碼統一編號。支援命令列傳參或從 `stdin` 串流批量讀入。可指定 `--strict` (僅舊制) 或 `--new-only` (僅新制)。
* `lookup` [*QUERY...*]:
  查詢企業或法人主檔資料。支援統編反查與名稱模糊搜尋。
* `resolve` [*NAME...*]:
  將不規範的農會、漁會或非營利組織名稱消歧義為標準官方全名（如「板農」➔「新北市板橋區農會」）。
* `pipe`:
  UNIX 串流文字濾網，自動自標準輸入文字中檢測並萃取出所有合法 8 碼統編。
* `status`:
  檢視 G60 模組就緒狀態、快取企業筆數與農漁會名冊數量。

## GLOBAL OPTIONS
* `-j`, `--json`:
  以單行緊湊 JSON 格式輸出，利於 jq 串流處理。
* `-q`, `--quiet`:
  極簡模式，僅輸出代碼或驗證通過之統編。
* `-v`, `--verbose`:
  輸出詳細驗證過程與除錯資訊至 `stderr`。
* `--db` *PATH*:
  指定 universal_keys.sqlite 資料庫路徑。
* `--version`:
  顯示模組版本與 CGS 規範版號。
* `--schema`:
  輸出 CLI 自我描述之 JSON Schema。

## EXAMPLES
### 檢核 8 碼統一編號
```bash
./pa g60 check 04595257 16525386 12345678 -j
```

### 從採購標案長文本中萃取合法統編
```bash
cat tender.txt | ./pa g60 pipe | jq .
```

### 農漁會簡稱消歧義標準化
```bash
./pa g60 resolve "新埔農會生鮮超市" "板農" -j
```

### 批量統編反查並輸出 TSV
```bash
cat tax_ids.txt | ./pa g60 lookup --tsv
```

## AUTHOR
Developed for Taiwan Government Open Data Backbone (tw-gov-db / GOV-300).
