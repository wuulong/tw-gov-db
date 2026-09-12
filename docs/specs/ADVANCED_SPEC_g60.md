# G60 高級延伸與跨模組協同規格書 (ADVANCED_SPEC_g60)

- **模組名稱**: `g60_corporate_indexer`
- **所屬專案**: `tw-gov-db` / `GOV-300` (全政府通用基石對照庫)
- **規範版本**: `CGS v2.4` (Pipeline-Native UNIX Standard)
- **關聯基石**: 基石四 (Cornerstone 4: 法人與企業 Corporate & NPO)

---

## 🚀 1. 設計哲學與 UNIX Pipe 原生哲學 (Pipeline-Native Philosophy)

G60 不僅是一個靜態資料查詢器，更是全政府管線（UNIX Pipeline）中處理「主體身分標籤」的神經濾網。

1. **非阻塞 Stdin 探測器 (Non-blocking Stdin Probe)**：
   - 採用 `select.select` 或 `sys.stdin.isatty()` 雙檢機制。
   - 優先讀取命令列引數；當無命令列引數且存在管道輸入時，以串流模式秒級處理，杜絕行程掛起。
2. **標準串流分離 (Clean Stream Separation)**：
   - `stdout`：僅輸出單行緊湊 JSON (Compact JSON) 或 Tab 分隔值 (TSV)。
   - `stderr`：輸出進度資訊、快取命中率與診斷日誌。
3. **離線優先與斷線自適應降級 (Offline-First Graceful Degradation)**：
   - 任何網路異常（如連線商業發展署 API 超時）不得導致 CLI 崩潰，自動標註 `cache_hit: false, source: "OFFLINE_VALIDATED"` 並回傳演演算法檢驗結果。

---

## 🔗 2. 5 大跨部會 UNIX Pipeline 實戰配方 (Pipeline Recipes)

### 配方一：政府電子採購標案文字串流 ➔ 統編萃取與驗證
* **情境**：從政府採購公告或 PDF 轉文字中，快速抽取所有合法統編。
* **管線指令**：
  ```bash
  cat tender_announcement.txt | ./pa g60 pipe --extract-tax-id | jq .
  ```
* **效果**：G60 自動以正則過濾出所有 8 碼數字候選者，通過 `ban_validator` 演演算法排除無效偽碼，輸出合法企業統編陣列。

### 配方二：農業部災損申報不規範名冊 ➔ 農會主檔消歧義標準化
* **情境**：農業部 (GOV-A19) 各鄉鎮災損統計寫著「板農」、「新埔農會」，需對齊正式官方編號。
* **管線指令**：
  ```bash
  echo -e "板農\n新埔農會\n吉安鄉農會超市" | ./pa g60 resolve -j | jq -r '.[] | [.input, .npo_id, .canonical_name] | @tsv'
  ```
* **效果**：輸出標準 TSV，精準對齊到 `新北市板橋區農會`、`新竹縣新埔鎮農會` 與 `花蓮縣吉安鄉農會`。

### 配方三：食安裁罰黑名單 (衛福部 A18) ➔ 統編反查與地緣分析 (G20)
* **情境**：從裁罰清單讀取統編，反查企業註冊地址並提取行政區程式碼對齊 G20。
* **管線指令**：
  ```bash
  ./pa meddb sanctions --limit 10 | jq -r '.[].tax_id' | ./pa g60 lookup | jq -r '.[].admin_code' | ./pa g20 admin
  ```
* **效果**：跨部會穿透：衛福部裁罰商 ➔ G60 統編登記行政區 ➔ G20 空間地緣分布。

### 配方四：金管會金融機構 (A21) ➔ 統編合法性快篩
* **情境**：驗證特許金融機構資料庫中 2,609 家法人之統一編號是否 100% 符合財政部規範。
* **管線指令**：
  ```bash
  ./pa fsc institutions -j | jq -r '.[].tax_id' | ./pa g60 check --strict
  ```
* **效果**：標註符合舊制或新制規範之機構比率。

### 配方五：跨模組聯合主體快照 (Master Identity Fingerprint)
* **情境**：給定任一主體名稱或程式碼，同時整合 G30（主管機關）、G60（法人主檔）、G20（地緣）。
* **管線指令**：
  ```bash
  ./pa g60 lookup 22570177 --with-agency
  ```

---

## 🛡️ 3. 容錯機制與新舊制切換原則

| 情境 | 處理策略 |
| :--- | :--- |
| **8 碼為空或長度不符** | 直接拋出 `INVALID_FORMAT`，不進入加權計算。 |
| **2023 新制特例** | 標註 `valid_by_current=true, valid_by_legacy=false`，利於稽核追蹤。 |
| **第七位為 7 的特例號碼** | 標註 `has_special_rule_7=true`，並列出兩種 Checksum 分支計算過程。 |
| **GCIS API 離線/超時** | 超時限制 3 秒；離線時回退至本機演演算法與 Seed 快取，不阻斷管線。 |
