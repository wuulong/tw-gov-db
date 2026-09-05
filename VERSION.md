# 🏷️ tw-gov-db (台灣政府開放資料通用基石對照庫) 版本演進與開發歷程看板 (VERSION.md)

* **目前最新版本**：`v0.2.1`
* **發布日期**：2026-08-22
* **歸檔路徑**：[VERSION.md](events-2026Q3/gov-db-in/tw-gov-db/VERSION.md)

---

## 📜 版本演進與 F-P-I-E-C 生命週期紀錄

### 🚀 `v0.2.1` (2026-08-22) - GOV-300 ↔ GOV-A19 跨部會全路徑對接整合測試與專書完工大里程碑
* **狀態**：🟢 `COMPLETED`
* **對接跨專案相容性矩陣 (Cross-Project Compatibility Matrix)**：
  - **跨部對接標的**：`tw-agro-db` (農業部 `GOV-A19`) **`v0.7.1`**
  - **對接驗證結果**：🟢 **100% PASS** (4 階整合對接測試與 P99 延遲 0.0095ms)
* **重點變更**：
  - **專書寫作完工**：完成第 4 章 Synergy 協同合約、第 5 章 7 大類別 Playbooks、第 6 章 SE-6D/SDM 與全附錄，重新打包 154KB 合訂本 `FULL_BOOK_TAIWAN_GOV_DB.md`。
  - **跨部會整合對接測試**：完成 `tests/test_gov_agro_integration.py`，實測驗證三層連線、OID 歸併、門牌地碼與氣象測站 20km 空間碰撞。
  - **雙向 Prompt 契約**：於 `[SPC-015]` / `[DSN-S09]` 寫入雙向 Prompt 契約協議，並維護 `book/04_synergy_contracts/prompts/PROMPT_TO_SUBMODULE_A19.md`。
  - **工具腳本**：新增 `combine_tw_gov_db_book.py` 打包腳本與 `bump_modified_docs_version.py` 自動版號更換腳本。
  - **語意校對**：通過 `sanitize_locale_terms.py` 全庫台灣繁體用語校對更正。

### 🏛️ `v0.2.0` (2026-08-22) - 全政府 1,103 筆快取企業機關、1,199 筆辦公日曆與郵遞區號引擎完工
* **狀態**：🟢 `COMPLETED`
* **重點變更**：
  - 完工 `master_agencies.sqlite` (4 大實體對照表) 與 `universal_keys.sqlite` (8 大通用基石表)。
  - 整合 1,103 筆全台灣上市/國營企業快照、1,199 筆政府辦公日曆與 3+3 碼郵遞區號反查引擎。
  - 完工 Core SDK 導航解析器 `DomainRegistryResolver` 與 `BaseDomainAdapter`。
