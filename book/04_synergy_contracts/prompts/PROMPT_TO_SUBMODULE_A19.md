# 🚀 任務指示：GOV-A19 (tw-agro-db) ↔ GOV-300 (tw-gov-db) 跨部會對接與 Synergy 維護

你現在是 **`tw-agro-db` (`GOV-A19` 農業部主題資料庫)** 的 Agentic AI 開發專家。

---

## 📍 母專案相對路徑指引 (Mother Repo Path Guidance)
本專案與母專案 `tw-gov-db` 位於同層的平級目錄中：
- **母專案路徑 (相對路徑)**：`../gov-db-in/tw-gov-db`
- **母專案 Core SDK 路徑**：`../gov-db-in/tw-gov-db/src`
- **母專案權威地圖檔**：`/Volumes/D2024/data/gov-db-in/domain_map_config.json` (或母專案內配置)

對接專區已在專案中準備好：
📂 `synergies/`
  ├── `GOV_A19_SYNERGY_SPEC.md` ➔ 指向母專案 `../gov-db-in/tw-gov-db/book/04_synergy_contracts/4.A19_spec_gov_a19_synergy.md` 的相對路徑軟連結 (Symlink)
  └── `test_gov_a19_synergy.py` ➔ 4 階跨部會對接測試套件

---

## 🎯 你的 3 大執行任務：

### 1. 讀取並驗證跨部會對接規格 (`synergies/GOV_A19_SYNERGY_SPEC.md`)
- 使用 `view_file` 讀取 `synergies/GOV_A19_SYNERGY_SPEC.md`。
- 了解本專案與母大腦 `tw-gov-db` 通用基石的映射關係（發布者 OID 歸併、門牌區號 `admin_code` 與氣象站 `station_id` WGS84 空間碰撞）。

### 2. 磨合內部 A00 與對外 Synergy 介面
- 讀取我們內部的 `A00_SPECIFICATION.md` 與 `db/agro.db` 結構。
- 確保內部 A10, A11 模組資料能完美轉譯並對齊至 `GOV_A19_SYNERGY_SPEC.md` 的五大通用基石。

### 3. 執行測試並更新對母大腦 Prompt 契約 (`synergies/PROMPT_TO_MASTER_G300.md`)
- 執行測試套件：
  `python3 synergies/test_gov_a19_synergy.py`
- 測試通過後，更新/確認 `synergies/PROMPT_TO_MASTER_G300.md` 檔案內容，供開發者複製回母大腦發動最終整合對接驗證！

---

請直接讀取 `synergies/GOV_A19_SYNERGY_SPEC.md` 並執行測試與磨合，回報結果！
