# G20 空間地籍與地址基石模組 高級延伸與跨部會協同規格書 (ADVANCED_SPEC.md)

- **模組名稱**: `g20_spatial_indexer`
- **所屬專案**: `tw-gov-db` (`GOV-300` 全政府通用基石對照庫)
- **核心目標**: 定義 G20 空間地籍與地址基石如何穿透同專案其他基石模組（G10 採購、G30 處務規程），並跨部會對接農業部 (`GOV-A19`)、內政部 (`GOV-A13`)、金管會 (`GOV-A21`) 與司法裁判庫。

---

## 🔗 1. 同專案 (GOV-300) 跨模組業務穿透 (Intra-Project Synergy)

### G20 ↔ G10 (政府採購與決標履歷模組)
* **協同情境**: 採購案履約地點與廠商註冊地址之「空間集中度與異地履約異常檢測」。
* **業務邏輯**:
  - 利用 G20 將 G10 中全台數百萬筆採購決標履約地址進行 `align-address` 正規化，計算各採購機關（如新竹縣政府）的「在地履約比率」。
  - 勾稽廠商公司註冊地（G20 `admin_code`）與決標履約地，自動標註「跨區遠距離高風險履約」異常警示。

---

## 🌐 2. 跨部會外聯協作與前瞻架構 (`[FUTURE]` Synergy Scope)

### G20 ↔ tw-moi-db (`GOV-A13` 內政部主題權威庫)
* **協同介面**: `cadastral_id` ↔ `TGOS_Spatial_Polygon`
* **業務邏輯**:
  - G20 提供輕量級 `cadastral_id` (`10004010-00100`) 與文字地址正規化服務；`tw-moi-db` 接手進行 7,748 全國村里實體邊界多邊形 (SHP) 疊加與國土利用分區違規比對。

### G20 ↔ tw-agro-db (`GOV-A19` 農業部主題專案)
* **協同介面**: `zipcode_registry` ↔ `farmers_association_registry` (342 農會)
* **業務邏輯**:
  - 將農業部全台 342 家農會與信用部辦事處地址，透過 G20 對齊至 6 碼 `admin_code` 與 `river_id` 水系，計算寒害/乾旱發生時，受災農會信用部放款曝險與行政區劃災情涵蓋率。

### G20 ↔ tw-fsc-db (`GOV-A21` 金管會主題專案)
* **協同介面**: `admin_code` ↔ `bank_branch_locations` (金融機構分支機構)
* **業務邏輯**:
  - 統計全台 368 鄉鎮市區之「本國銀行分行設點密度」，即時產出全台「金融普惠邊陲區（無銀行分行鄉鎮）」警示檢視。

---

## 📐 3. 前瞻協作介面與資料契約 (Synergy Interface Contracts)

```sql
-- 預先定義跨部會空間勾稽檢視 SQL 契約 [FUTURE]
CREATE VIEW IF NOT EXISTS v_g20_agro_moi_spatial_cross_synergy AS
SELECT 
    g.admin_code,
    g.county_name,
    g.town_name,
    g.zipcode,
    COUNT(DISTINCT fa.farmer_assoc_id) AS farmers_assoc_count,
    COUNT(DISTINCT bb.branch_id) AS bank_branch_count
FROM zipcode_registry g
LEFT JOIN domain_agro_db.farmer_associations fa ON g.admin_code = fa.admin_code
LEFT JOIN domain_fsc_db.bank_branches bb ON g.admin_code = bb.admin_code
GROUP BY g.admin_code, g.county_name, g.town_name, g.zipcode;
```
