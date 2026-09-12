# 📌 GOV-DB 子模組建構強制藍圖模板 (modules/template_blueprint/)

本目錄為所有台灣政府開放資料部會子專案（如 `tw-moi-db` `GOV-A13` 內政部、`tw-moea-db` `GOV-A09` 經濟部等）啟動建置時的 **強制複製起步範本庫 (Template Blueprint)**。

當要啟動一個新部會子模組時，必須完整複製本目錄下之架構與檔案資產。

---

## 📂 模板資產與檔案結構說明

```text
modules/template_blueprint/
├── README.md                      ◄── 本說明檔案 (模組簡介與架構範本)
├── AXX_SPECIFICATION.md           ◄── 子模組基礎業務 Spec 強制模板
├── AXX_ADVANCED_DESIGN_SPEC.md    ◄── 子模組內部多 DB 碰撞進階設計模板
├── CLI_MANUAL.md                  ◄── CLI 工具使用手冊範本
├── WORKFLOW.md                    ◄── Agentic AI 意圖路由導航手冊範本
├── schema.sql                     ◄── 子模組 SQLite 實體表與索引 DDL 強制範本
├── etl.py                         ◄── 資料入庫與 attributes_json (spec_version: "0.2.1") 範本
└── test_template_integration.py   ◄── 100% 獨立與對接母大腦的整合測試套件範本
```

---

## 🛠️ 複製與啟動 SOP (Step-by-Step)

1. **複製模板**：將 `modules/template_blueprint/` 複製至目標子專案或新模組目錄（如 `modules/a13_moi_core/`）。
2. **搜尋與替換**：將檔案中的 `AXX` 替換為實際部會代號（如 `A13`），將 `[DOMAIN_NAME]` 替換為專案全稱。
3. **完成階段 1~5**：遵從 `workflow_gov_db_submodule_bootstrap.md` 規範完成通用基石對齊、Spec 歸位、CLI 實作與整合對接測試！
