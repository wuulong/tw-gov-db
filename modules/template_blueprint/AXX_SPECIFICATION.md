# 📘 AXX 基礎業務規格書 (AXX_SPECIFICATION.md)

* **專案代號**：`GOV-AXX`
* **部會名稱**：`[DOMAIN_NAME]`
* **受控版本**：`v0.2.1`

---

## 1. 業務範疇與核心資料集 (Business Scope & Datasets)

* **資料源 1**：`[DATASET_1_NAME]` (發布機關: `[PUBLISHER_NAME]`)
* **資料源 2**：`[DATASET_2_NAME]` (發布機關: `[PUBLISHER_NAME]`)

---

## 2. 五大通用基石對齊對照整合表 (Baseline Alignment)

| 通用基石 | 子模組引用欄位 | 對齊 GOV-300 實體表 | 業務對照整合目標 |
| :--- | :--- | :--- | :--- |
| **基石一：組織 OID** | `publisher_raw` | `master_agencies` / `publisher_aliases` | 自動歸並行布者至權威 OID |
| **基石二：空間地籍** | `address_raw` / `cadastral_id` | `admin_codes` / `zipcode_registry` | 文字地址反查 6 碼門牌與地籍段號 |
| **基石三：水系氣象** | `station_id` / `river_id` | `station_registry` / `river_registry` | 氣象與水文空間碰撞 |
| **基石四：法人企業** | `tax_id` | `corporate_registry` / `npo_registry` | 企業統編與法人登記對照整合 |
| **基石五：時間時序** | `date_raw` | `calendar_registry` / `clean_datetime` | 舊民國年轉 ISO-8601 與辦公日曆對齊 |

---

## 3. SQLite DDL 規格宣告

詳見本模組 [schema.sql](schema.sql)。
