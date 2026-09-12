# G30 全政府跨部會法規處務規程與虛擬圖譜模組 (g30_mandate_indexer) 業務與系統規格書

- **模組名稱**: `g30_mandate_indexer`
- **所屬專案 / 權威程式碼**: `tw-gov-db` / `GOV-300` (通用基石對照庫)
- **規範版本**: `v2.4` (CGS Pipeline-Native UNIX Standard)
- **基石定位**: 基石一 (Cornerstone 1: 權威機關 OID、處務規程與組織演進圖譜)

---

## 🏛️ 業務功能本位 4 大實戰情境 (4 Core Business Scenarios)

### 1. 法規文字全量文本解析與演進圖譜抽取 (Law-Text Genealogy Parser & Rating Taxonomy)
* **業務痛點**: 政府未提供全量 OID 演進歷史 Log。從全國法規資料庫 (law_db) 提取的組織改制資訊，可能僅包含中文名稱與生效日，缺乏 OID，若直接丟棄會損失資料；若誤標權威會造成 AI 幻覺。另外，四級與附屬機關（如第一至第十河川局）數量極其龐雜，若將所有細部機關逐筆刻入 DB，會造成資料庫膨脹與維護負擔。
* **業務規格與實作機制 (JIT 輕量化動態組織變異解析)**:
  - 全量掃描《行政院組織法》、《各部會組織法》與《條例廢止公告》。
  - **極簡骨幹與 JIT 變異說明機制 (JIT Genealogy Resolution Architecture)**：
    - **Macro 骨幹落庫**：資料庫 `agency_genealogy` 僅記錄抽象高階變異原則（如：`前身：經濟部水利署各河川局` ➔ `繼承：經濟部水利署各河川分署`，`112年9月26日`）。
    - **`description_rule` 變異說明欄位**：在 DB 中以結構化欄位記載變動說明（如：*「依據《經濟部水利署各河川分署辦事細則》(PCode: J0010063)，原各河川局第一至第十局於 112-09-26 統一改稱各河川分署」*）。
    - **執行期 JIT 動態下鑽**：在應用層執行期，當查詢到個體附屬機關（如「第二河川局」）時，系統查閱抽象變異規則並 JIT 提示改制資訊，需要細節時再動態透過 `law_cli` 或 OID 圖鑑下鑽，達成 DB 極致輕量化與零維護負擔。
  - 實裝 **雙維度評級與信心度 (Confidence Rating) 架構**：即使只有中文名稱，依然可以作為獨立條目落庫（標註 `TEXT_ONLY`, 信心度 `0.7`, 狀態 `NEEDS_PATCH`），待後續補齊 OID 後升級為 `FULL_MATCH` (`1.0`, `VERIFIED`)。

### 2. 現行內部組科處務規程與既有 `law_cli.py` 直連 (Entity Master Profile & Law CLI Bridge)
* **業務痛點**: 開放資料集標註發布機關（如「農業部農糧署」），但無法自動定位其內部主管組科與法定職掌。
* **業務規格與實作機制**:
  - 在 `master_agencies.sqlite` 建置 `agency_mandates` 實體表（含 `law_name`, `law_article`, `pcode` 欄位）。
  - 直接引用本機專案既有之 `law_cli.py` 兵器庫 (PCode 檢索) 實現 0MB 虛擬開銷連線，無縫檢索《處務規程》與《辦事細則》條文全文（如 PCode: `M0010061` 《農業部處務規程》）。

### 3. 開放資料集/關鍵字 AI 主管科室自動配對引擎 (Mandate Auto-Classifier & Metrics)
* **業務痛點**: 人工判定數萬筆開放資料集究竟屬於哪一個主管科室耗時費力且標準不一。
* **衍生業務指標與配對引擎**:
  - **職掌匹配信心度指標 (Mandate Confidence Score, MCS)**：依據文本相似度與處務規程關鍵字，計算 0.0~1.0 信心度。
  - **自動歸屬品質評級**: 🟢 HIGH (>=0.85 命中特定科室) / 🟡 MEDIUM (>=0.6 命中司局級) / 🔴 LOW (<0.6 待人工稽核)。

### 4. 異質發布單位別名對齊與權威 OID 歸併 (Publisher Alias Alignment)
* **業務情境**: 針對 data.gov.tw 上 6 萬筆資料集中出現的異質別名（如「行政院農業委員會農糧署」），透過正則與字串信心度 (0.8~1.0)，100% 歸併對齊到現行官方 OID (`master_agencies`)。

---

## 🧠 法規文本演進解析演演算法說明 (Law Genealogy Extraction Algorithm)

本模組的核心演演算法 **`LawGenealogyParser`** 負責從 `law_db` (全國法規資料庫) 文本中抽取組織改制事件，演演算法運作邏輯如下：

```
[全國法規資料庫 (law_db / law_cli.py)]
       │
       ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Step 1: 組織法規特徵篩選 (Law Filter)                       │
 │ • 鎖定標題含 "組織法", "組織條例", "處務規程" 或狀態為 "廢止"   │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Step 2: 正規表示法與語意範本提取 (Pattern Extraction)         │
 │ • 範本 A (廢止失效): r"(?P<old>.*組織條例)於.*(?P<new>.*組織法)通過生效後失效" │
 │ • 範本 B (升格改制): r"(?P<old>.*)於中華民國(?P<date>.*)升格為(?P<new>.*)"     │
 │ • 範本 C (廢止移撥): r"廢止(?P<old>.*)，業務由(?P<new>.*)承受"                │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ Step 3: OID 雙向對齊與評級分類 (OID Alignment & Rating)     │
 │ • 以 <old> / <new> 字串查詢 master_agencies 與 GDS.csv     │
 │   - 若兩端 OID 皆命中 ➔ completeness="FULL_MATCH", conf=1.0, status="VERIFIED"│
 │   - 若僅單邊命中     ➔ completeness="PARTIAL_MATCH", conf=0.85, status="PENDING_REVIEW"│
 │   - 若兩端均無 OID   ➔ completeness="TEXT_ONLY", conf=0.7, status="NEEDS_PATCH"│
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                 [寫入 master_agencies.sqlite]
```

---

## 📊 SQLite Schema 結構與通用表定質 (master_agencies.sqlite)

### `agency_genealogy` (歷史演進圖譜審核表)
```sql
CREATE TABLE IF NOT EXISTS agency_genealogy (
    genealogy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    predecessor_name VARCHAR(128) NOT NULL,   -- 前身機關名稱 (如 "行政院農業委員會")
    predecessor_oid VARCHAR(128),              -- 前身機關 OID (可為空)
    successor_name VARCHAR(128) NOT NULL,     -- 繼承機關名稱 (如 "農業部")
    successor_oid VARCHAR(128),                -- 繼承機關 OID (可為空)
    event_type VARCHAR(32) NOT NULL,           -- UPGRADE, MERGE, SPLIT, RENAME
    effective_date VARCHAR(16),                -- 生效日期 (如 "2023-08-01")
    law_name VARCHAR(128) NOT NULL,            -- 法規全稱 (如 "農業部組織法")
    law_article VARCHAR(32),                    -- 法規條次 (如 "第 1 條")
    pcode VARCHAR(16),                          -- 既有 law_cli 法規程式碼
    source_text TEXT,                          -- 文本分析原始摘要
    
    -- 完整度與審核狀態
    completeness_level VARCHAR(32) NOT NULL,   -- FULL_MATCH, TEXT_ONLY, PARTIAL_MATCH
    confidence_score FLOAT DEFAULT 0.5,        -- 0.0 ~ 1.0
    review_status VARCHAR(32) DEFAULT 'PENDING_REVIEW', -- PENDING_REVIEW, VERIFIED, NEEDS_PATCH, REJECTED
    
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMP,
    attributes_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🛠️ CGS v2.4 CLI 命令規格 (`g30_cli.py`)

- `g30_cli.py resolve-org [QUERY] [--stdin] [-j]`: **JIT 執行期輕量動態組織推導**，輸入歷史或舊版機關（如「第二河川局」、「南區工程處」），動態對位為現行權威機關與官方 OID。支援 `--stdin` UNIX 管道流式處理。
- `g30_cli.py backfill-oid [-j]`: 自動比對官方 6,937 筆 OID 字典，批次回填 `successor_oid` 至 `agency_genealogy` 資料表。
- `g30_cli.py parse-laws [--save] [-j]`: 執行 `LawGenealogyParser` 雙軌演算法全量解析法規與廢止令，抽取評級條目。
- `g30_cli.py alias [QUERY] [-j]`: 將異質發布單位別名對齊至權威 OID。
- `g30_cli.py match-mandate [QUERY] [--stdin] [-j]`: 傳入關鍵字或資料集名稱，自動配對主管組科與 MCS 信心度。
- `g30_cli.py genealogy [--status STATUS] [--pending] [--verified] [-j]`: 查詢演進對照表與完整度狀態（支援 `--status NEEDS_PATCH`）。
- `g30_cli.py patch-oid <ID> --oid <OID> [--target predecessor|successor]`: 為 `TEXT_ONLY` 條目補充填入 OID。
- `g30_cli.py patch [--id ID] [INPUT_JSON]`: 透過 JSON 修補或新增組織演進規則；支援 `--id` 更新現有規則欄位。
- `g30_cli.py verify <ID> [--reject]`: 審核核可或駁回條目。
- `g30_cli.py schema`: 輸出符合 Draft-2020-12 標準之 CGS v2.4 自我描述 JSON Schema。
- `g30_cli.py status [-j]`: 模組健康度與待補充/待審核統計。
