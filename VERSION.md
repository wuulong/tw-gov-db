# 🏷️ tw-gov-db (台灣政府開放資料通用基石對照庫) 版本演進與開發歷程看板 (VERSION.md)

* **目前最新版本**：`v0.3.0`
* **發布日期**：2026-09-13
* **歸檔路徑**：[VERSION.md](events-2026Q3/gov-db-in/tw-gov-db/VERSION.md)

---

## 📜 版本演進與 F-P-I-E-C 生命週期紀錄

### 🌊 `v0.3.0` (2026-09-13) - 方案 A 模組架構重組、WRA-Civ 外掛協同規格發布與五大理論基石對照整合大里程碑
* **狀態**：🟢 `COMPLETED`
* **對接跨專案相容性矩陣 (Cross-Project Compatibility Matrix)**：
  - **跨部會對接標的 1**：`tw-agro-db` (農業部 `GOV-A19`) **`v0.7.1`** ➔ 🟢 **100% PASS** (4 階整合對接測試通過)
  - **水文拓樸對接標的 2**：`RiverExploration` / **WRA-Civ 水系拓樸** **`v2.4`** ➔ 🟢 **100% PASS** (1,394 筆水脈雙向溯源與 `plugins.gov_db` 零污染注水)
* **重點變更**：
  1. **方案 A 權威模組架構重組 (Option A Realignment)**：
     - 將應用採集層定錨為 **`G01` (`g01_report_miner`)**（非基石通用應用層）。
     - 將五大理論基石嚴格對齊為 **`G10 ~ G50`**：
       - `G10` 機關組織與權責職掌 (`g10_mandate_indexer`)
       - `G20` 空間地籍與門牌郵碼 (`g20_spatial_indexer`)
       - `G30` 水系流域與水文測站 (`g30_hydrology_indexer`)
       - `G40` 法人統編與企業快取 (`g40_corporate_indexer`)
       - `G50` 時間時序與辦公農曆 (`g50_temporal_indexer`)
     - 全系統徹底清除 `g60` 遺留代號，`./pa` 路由器全面簡化為標準路由，無多餘歷史別名。
  2. **WRA-Civ 外掛協同規格書發布 (`[SYN-WRA-CIV-PLUGINS-001]`)**：
     - 正式確立 `plugins.gov_db` 官方中繼屬性規格（版本 `v1.0.1`）。
     - 嚴格遵守 WRA-Civ 核心親緣實體不可變性，所有基石注水 100% 隔離於 `plugins.gov_db` 命名空間。
     - 規格書落庫於 [SPEC_WRA_CIV_PLUGIN_GOV_DB.md](docs/specs/SPEC_WRA_CIV_PLUGIN_GOV_DB.md) 並同步抄送至 `RiverExploration/specs/SPEC_PLUGIN_GOV_DB.md`。
     - 全面支援標準公開命令 `python src/modules/g30_hydrology_indexer/g30_cli.py hydrate` 與 Python API Direct Import。
  3. **專書第三章目錄化深核重構 (`book/03_submodules/`)**：
     - 仿照 `tw-fsc-db` 深核架構，將第三章拆解為 7 個獨立檔案（`03_00` 通用架構指引至 `03_01`~`03_50` 獨立專篇）。
     - 全面深入拆解三大 UNIX Pipe 維度（非阻塞探測、跨部會多工接力、Pipe Purity 資料純淨分離）。
     - 重新整合對接全書 [FULL_BOOK_TAIWAN_GOV_DB.md](book/FULL_BOOK_TAIWAN_GOV_DB.md)（共 30 個章節，266.2 KB）。
  4. **全套單元測試與跨部會整合測試 100% 綠燈**：
     - 執行 `pytest tests/` 通過 32/32 個測試案例（涵蓋 `test_cgs_v24_pipeline`、`test_gov_agro_integration`、`test_g30`、`test_g40`、`test_g50` 等）。
  5. **台灣繁體在地語境零 Token 淨化**：
     - 全專案檔案與專書章節通過 `sanitize_locale_terms.py --fix` 自動校正。

---

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

---

### 🏛️ `v0.2.0` (2026-08-22) - 全政府 1,103 筆快取企業機關、1,199 筆辦公日曆與郵遞區號引擎完工
* **狀態**：🟢 `COMPLETED`
* **重點變更**：
  - 完工 `master_agencies.sqlite` (4 大實體對照表) 與 `universal_keys.sqlite` (8 大通用基石表)。
  - 整合 1,103 筆全台灣上市/國營企業快照、1,199 筆政府辦公日曆與 3+3 碼郵遞區號反查引擎。
  - 完工 Core SDK 導航解析器 `DomainRegistryResolver` 與 `BaseDomainAdapter`。
