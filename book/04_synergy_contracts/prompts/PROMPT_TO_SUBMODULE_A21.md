# 🚀 任務指示：GOV-A21 (tw-fsc-db) ↔ GOV-300 (tw-gov-db) 跨部會對接與 Synergy 維護

你現在是 **`tw-fsc-db` (`GOV-A21` 金管會主題資料庫)** 的 Agentic AI 開發專家。

---

## 📍 母專案相對路徑指引 (Mother Repo Path Guidance)
本專案與母專案 `tw-gov-db` 位於同層的平級目錄中：
- **母專案路徑 (相對路徑)**：`../gov-db-in/tw-gov-db`
- **母專案 Core SDK 路徑**：`../gov-db-in/tw-gov-db/src`
- **母專案權威地圖檔**：`/Volumes/D2024/data/gov-db-in/domain_map_config.json`

對接專區已在專案中準備好：
📂 `synergies/`
  ├── `A21_SPECIFICATION.md` ➔ 子專案基礎業務規格書
  ├── `A21_ADVANCED_DESIGN_SPEC.md` ➔ 跨多 DB 事前穿透規格書
  ├── `GOV_A21_SYNERGY_SPEC.md` ➔ 跨專案協同合約與對 G300 需求規格
  ├── `PROMPT_TO_MASTER_G300.md` ➔ 寫給母專案的對接任務指示
  └── `test_gov_a21_synergy.py` ➔ 4 階跨部會對接測試套件

---

## 🎯 你的 3 大執行任務：
1. 讀取並驗證跨部會對接規格 (`synergies/GOV_A21_SYNERGY_SPEC.md`)。
2. 確保五大通用基石（組織 OID、門牌區號、企業統編、辦公日曆）與母大腦貫通連線且無重複建設。
3. 執行測試套件：`python3 synergies/test_gov_a21_synergy.py` 確保 100% PASS！
