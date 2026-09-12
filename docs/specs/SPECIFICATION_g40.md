# G40 全政府時間、辦公日曆與時序維度器模組 (g40_temporal_indexer) 業務與系統規格書

- **模組名稱**: `g40_temporal_indexer`
- **所屬專案 / 權威代號**: `tw-gov-db` / `GOV-300` (全政府通用基石對照庫)
- **規範版本**: `v2.4` (CGS Pipeline-Native UNIX Standard)
- **基石定位**: 基石五 (Cornerstone 5: 時間與時序 Temporal & Calendar)
- **對齊標準**: `Schema.org/DateTime`, `Schema.org/Event`, `schema.gov.tw`

---

## 🏛️ 業務功能本位 4 大核心情境 (4 Core Business Scenarios)

### 1. 全政府異質民國年/西元年極速管線清洗 (Universal Date Normalizer)
* **業務痛點**:
  台灣跨部會開放資料（如農業災損、採購公告、裁判日期、統計報表）充斥 10 餘種異質日期文字：
  - `113/08/22`, `113-08-22`, `113.8.22`, `1130822`
  - `民國113年8月22日`, `113年08月`
  - `113Q3`, `113年第3季`, `113上` (半年度)
  導致 SQL 無法排序、GraphRAG 無法建立時間軸、資料庫 `JOIN` 失敗。
* **業務規格與實作機制**:
  - 提供 100% 零 Token 本機正則解析引擎。
  - 支援從 `stdin` 讀取串流或 JSON 陣列，即時輸出標準 ISO-8601 CST 字串 (`YYYY-MM-DD` 或 `YYYY-MM-DDTHH:MM:SS+08:00`) 與對應的西元年/民國年/季度結構化物件。

### 2. 行政院核定辦公日曆、營業日與天災假判定 (Working Day & Holiday Checker)
* **業務痛點**:
  金融市場（股市結算）、物流配送、政府履約期限計算，均需要精準判定「特定日期是否為上班日/營業日」。若遇到颱風假或彈性補班日，常引發違約或計日糾紛。
* **業務規格與實作機制**:
  - 內建並維護 `universal_keys.sqlite` 中的 `calendar_registry` 權威表。
  - 支援快速判定：
    - `is_holiday`: 是否放假 (True/False)
    - `holiday_category`: 放假類別 (`WEEKEND`, `NATIONAL_HOLIDAY`, `TYPHOON_LEAVE`, `MAKE_UP_WORKDAY`)
    - `is_working_day`: 是否為法定上班/營業日 (True/False)

### 3. 政府會計年度與時序分桶統計器 (Fiscal Year & Temporal Bucketing)
* **業務痛點**:
  政府預算與統計報表皆以「會計年度 (Fiscal Year)」與「季度 (Quarter)」為單位，但在跨部會對齊時，缺乏快速展開特定年度所有上班日或季度起訖日期的工具。
* **業務規格與實作機制**:
  - 提供 `temporal-buckets` 子命令，輸入「113年度」或「2024Q3」，自動展開該區間之起訖日期、總天數、實際工作日數、國定假日清單。

### 4. 歷史天災停班停課事件時空關聯 (Typhoon & Disaster Temporal Anchor)
* **業務情境**:
  將歷史重大颱風/水災的停班停課日期，與 G20 空間水系測站（雨量站）及農業部 (GOV-A19) 災損申報時間進行時空重疊分析。

### 5. 農曆陰陽曆雙向轉換、節氣與台灣傳統節日 (Lunar & 24 Solar Terms Engine)
* **業務痛點**:
  台灣法定三大節（春節、端午、中秋）以及全台農漁畜產批發市場（逢初一、十五、初二、十六牙祭）休市排程皆依循農曆；農作氣候物候監測依賴「二十四節氣」。一般西曆資料庫無法建立此時序脈絡。
* **業務規格與實作機制**:
  - 內建純 Python 微秒級解算模組 `lunar_engine.py` (涵蓋 1900～2100 年)。
  - 支援功能：
    - 西曆 ➔ 農曆轉換 (包含天干地支歲次、十二生肖、月份大小、傳統節日)。
    - 農曆 ➔ 西曆反向解算 (支援 `--leap` 閏月精確定位)。
    - 二十四節氣常數演算法計算 (如立春、清明、冬至精確國曆日期)。
    - 文字日期清洗自動辨識中文農曆 (如「農曆113年五月初五」自動轉譯為 ISO-8601 `2024-06-10`)。

---

## 📊 SQLite Schema 結構 (universal_keys.sqlite)

### `calendar_registry` (行政機關辦公日曆表)
```sql
CREATE TABLE IF NOT EXISTS calendar_registry (
    date_str VARCHAR(10) PRIMARY KEY,   -- 日期 (YYYY-MM-DD)
    year INTEGER NOT NULL,              -- 西元年 (如 2024)
    minguo_year INTEGER NOT NULL,       -- 民國年 (如 113)
    month INTEGER NOT NULL,             -- 月份 (1~12)
    day INTEGER NOT NULL,               -- 日期 (1~31)
    day_of_week INTEGER NOT NULL,       -- 星期 (1=週一 ... 7=週日)
    is_holiday BOOLEAN NOT NULL,        -- 是否為放假/例假日 (1 是, 0 否)
    is_working_day BOOLEAN NOT NULL,    -- 是否為法定上班/營業日 (1 是, 0 否)
    holiday_category VARCHAR(64),       -- 節日類型 (放假之紀念日及節日, 補行上班日, 調整放假日等)
    description VARCHAR(256),           -- 節日名稱或說明 (如 春節, 端午節, 補行上班)
    attributes_json TEXT,               -- [SPC-006] 包含各縣市停班停課特徵
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_calendar_year ON calendar_registry(year);
CREATE INDEX IF NOT EXISTS idx_calendar_minguo ON calendar_registry(minguo_year);
CREATE INDEX IF NOT EXISTS idx_calendar_working ON calendar_registry(is_working_day);
```

---

## 🛠️ CGS v2.4 CLI 命令規格 (`g40_cli.py`)

- `g40_cli.py clean-date [DATE_STR] [--stdin] [-j]`: 異質日期/民國年/中文農曆極速轉換為標準 ISO-8601 與結構化物件。
- `g40_cli.py check [DATE_STR] [--stdin] [-j]`: 查詢特定日期之辦公日曆屬性 (是否上班、假日類型、節日說明)，並自動附加農曆歲次、生肖與節氣。
- `g40_cli.py range [START_DATE] [END_DATE] [--working-days-only] [-j]`: 展開指定區間之日期序列與統計天數。
- `g40_cli.py bucket [FISCAL_YEAR_OR_QUARTER] [-j]`: 展開會計年度 (如 113) 或季度 (如 2024Q3) 之時間範圍與工作日統計。
- `g40_cli.py lunar [SOLAR_DATE] [--to-solar LUNAR_DATE] [--leap] [--terms] [--year YEAR] [-j]`: 進行公曆農曆雙向轉換、生肖干支、傳統節日與 24 節氣查詢。
- `g40_cli.py init-calendar`: 根據雙北/人事行政總處開放資料，初始化與厚化 `calendar_registry` (1,801 筆，2013-2028 年)。
- `g40_cli.py schema`: 輸出符合 Draft-2020-12 標準之自我描述 JSON Schema。
- `g40_cli.py status [-j]`: 模組健康度、涵蓋年份範圍與總筆數統計。
