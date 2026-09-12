# G30 全政府跨部會法規處務規程與虛擬圖譜模組 高級延伸與跨部會協同規格書 (ADVANCED_SPEC.md)

- **模組名稱**: `g30_mandate_indexer`
- **所屬專案**: `tw-gov-db` (`GOV-300` 全政府通用基石對照庫)
- **核心目標**: 定義 G30 處務規程與組織演進圖譜如何穿透同專案其他模組（G10 採購、G20 地籍地址），並直接透過專案既有 `law_cli.py` 兵器庫對接全國法規資料庫。

---

## 🔗 1. 同專案 (GOV-300) 跨模組業務穿透 (Intra-Project Synergy)

### G30 ↔ G10 (政府採購與決標履歷模組)
* **協同情境**: 採購主辦單位與法定處務規程之「越權採購與法定職掌異常稽核」。
* **業務邏輯**:
  - 讀取 G10 採購案之招標機關與標案名稱（如「水質淨化工程採購」）。
  - 發動 G30 `match-mandate` 比對該採購機關之內部處務規程，驗證該採購案是否屬於該單位（如「水利署水質管理組」）之法定掌理事項。若無法配對，標示「🟢 法定合規」或「🟡 跨組科代理採購」警示。

### G30 ↔ G20 (空間地籍與地址基石模組)
* **協同情境**: 機關組改前後駐地地址變更與行政區劃對照。
* **業務邏輯**:
  - 當 G30 的 `agency_genealogy` 記錄機關組改或遷址事件時，自動呼叫 G20 `align-address` 正規化其新舊地址與 6 碼 `admin_code`，維護全政府機關駐地空間圖譜。

---

## 🌐 2. 跨部會外聯協作與既有 CLI 兵器庫直連 (Synergy Scope)

### G30 ↔ 專案既有 `law_cli.py` (scripts/law_db/law_cli.py)
* **協同介面**: `LawCliBridge` ↔ `scripts/law_db/law_cli.py`
* **業務邏輯**:
  - G30 核心直接 import 並發動既有 `law_cli.py` 的 PCode 與條文搜尋 API（如 PCode `M0010061` 《農業部處務規程》）。G30 本機僅保存處務規程與組科對照鍵（0MB 開銷），當 AI Agent 需要調閱詳細法規條文全文時，直接調用 `law_cli.py` 獲取權威法規條文。

### G30 ↔ tw-agro-db (`GOV-A19` 農業部主題專案)
* **協同介面**: `agency_genealogy` (VERIFIED 審核鏈) ↔ `domain_agro_db.mandates`
* **業務邏輯**:
  - 當查詢 2023 年 8 月以前發布的舊農委會資料集時，G30 `genealogy` 自動提供「行政院農業委員會 ➔ 農業部」的 `VERIFIED` 權威改制鏈，引導 `tw-agro-db` 將舊資料集平滑連鎖至現行農業部 12 大垂直子模組。

---

## 📐 3. 前瞻協作介面與數據契約 (Synergy Interface Contracts)

```sql
-- 預先定義跨部會組織處務規程與採購職掌稽核視圖 SQL 契約 [FUTURE]
CREATE VIEW IF NOT EXISTS v_g30_procurement_mandate_audit AS
SELECT 
    g10.tender_id,
    g10.tender_title,
    g10.org_oid,
    g30.unit_name AS matched_unit,
    g30.law_article,
    g30.confidence_score AS mcs_score
FROM domain_g10_tenders g10
LEFT JOIN agency_mandates g30 ON g10.org_oid = g30.agency_oid
WHERE g30.keywords_json LIKE '%' || g10.category_keyword || '%';
```
