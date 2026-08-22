# 📘 《台灣政府開放資料通用基石圖鑑：從權威機關到跨部會基石的資料治理體系》全書目錄 (00_toc.md)

* **專案名稱**：`tw-gov-db` (台灣政府開放資料通用基石對照庫)
* **專案代號**：`GOV-300` (方案 A 權威機關簡碼 `300000000A`)
* **受控版本**：`v0.2`
* **歸檔目錄**：`events-2026Q3/gov-db-in/tw-gov-db/book/00_toc.md`

---

## 📚 專書目錄地圖與章節寫作意圖 (Writing Intentions)

### **[第 0 章：全書目錄與導覽](00_toc.md)**
* 🎯 **本章寫作意圖**：為全書提供全景導覽地圖，明確標示受控版本號 (`v0.2`) 與開源聲明，讓讀者與 AI Agent 在第 1 秒即可定位所需的資料治理模組與開源技術資產。

---

### **[第 1 章：專案願景與台灣政府數位轉型使命](01_vision_and_mission.md)**
* 🎯 **本章寫作意圖**：透過真實台灣公務與產學研第一線的資料慘痛碰撞案例，深刻揭露跨部會開放資料現存的 6 大現實痛點，並建立 `GOV-300` 母專案與部會子專案架構的開源願景。
  - **1.1 台灣跨部會開放資料的 6 大真實痛點與血淚情境**
    - 🎯 *寫作意圖*：以第一線資料分析與系統整合情境，真實還原 6 大血淚痛點：
      1. **【痛點 1：缺乏整體系統架構與知識圖譜連結】**：全台資料多為單點散落的二維試算表 (CSV/JSON)，缺乏可進行跨模組關聯、知識導航與 GraphRAG 零幻覺 Grounding 的大一統知識圖譜與通用基石架構。
      2. **【痛點 2：跨部會資料孤島與同名異義陷阱】**：農業部「新竹水利會」與內政部「新竹縣竹北市」在地理空間與組織 OID 上完全脫鉤，導致氣象寒害與災害救助統計無法一毫秒碰撞。
      3. **【痛點 3：發布單位別名混亂與異質字串狂暴】**：data.gov.tw 上同一個機關在不同資料集中出現「農糧署」、「行政院農業委員會農糧署」、「農業部農糧署作物生產組」等 10 種字串，字串比對 100% 失敗。
      4. **【痛點 4：舊民國年格式與時間字串陷阱】**：資料集中混雜「113/08/22」、「1130822」、「2024-08-22」與「113.8.22」，直接導致 SQL 日期排序與 GraphRAG 時間軸建構癱瘓。
      5. **【痛點 5：巨量 CSV 全量載入與記憶體/DB 儲存膨脹障礙】**：每次執行分析都要重新下載 180MB 包含 160 萬公司登記或全台門牌的大表，導致本機記憶體爆掉、SQLite 膨脹至數 GB。
      6. **【痛點 6：缺乏統一地籍、門牌與水系空間對合鍵】**：農業部休閒農場只有中文地址，內政部地籍圖只有段號（如成功段 100 號），兩者無法在 GIS 地圖或 SQL 表格中直連比對。
  - **1.2 建立大一統母專案與部會子專案 (`GOV-300` ↔ `GOV-A19` / `GOV-A13` / `GOV-A09`) 的開源價值**
    - 🎯 *寫作意圖*：論述以 `GOV-300` 為通用底座、部會為領域子專案的「分散式協同」架構優勢，定義開放資料庫之開源社會價值。

---

### **[第 2 章：GOV-300 母大腦全景架構、系統中繼與通用基石解構](02_architecture_overview.md)**
* 🎯 **本章寫作意圖**：系統化解構 `GOV-300` 的核心軟體架構、方案 A 子專案權威命名規範、Sys Meta/attributes_json 動態屬性擴充機制、雙軌瘦身機制與三層式跨專案 Co-work 協作模式。
  - **2.1 五大通用基石 (5 Baseline Cornerstones) 語意標準解構**
    - 🎯 *寫作意圖*：定義全台政府資料對合之 5 大必備通用鍵（基石一：組織OID/別名、基石二：行政區劃/地籍、基石三：水系/氣象測站、基石四：法人企業/農會、基石五：時間/日曆）。
  - **2.2 子專案方案 A 權威命名規範 (Option A Naming Taxonomy: `GOV-[CODE]`)**
    - 🎯 *寫作意圖*：解構子專案與領域代號的方案 A 權威命名邏輯。說明如何結合 **Prefix (GOV) + 官方行政院部會簡碼 (300 總母專案, A19 農業部, A13 內政部, A09 經濟部)**，建立全台灣跨部會專案的一致性簡碼代號與對照地圖 (`domain_map_config.json`)。
  - **2.3 Sys Meta 與 `attributes_json` 動態擴充與中繼資料機制 (`[SPC-006]`)**
    - 🎯 *寫作意圖*：解構 `attributes_json` 欄位設計哲學。說明如何利用半結構化 JSON 儲存受控版號 (`spec_version: "0.2"`)、歷史變更軌跡 (`history_trail`)、非結構化補充屬性與系統層 Sys Meta，實現 100% 相容性。
  - **2.4 雙軌瘦身架構 (Dual Optimization Architecture)**
    - 🎯 *寫作意圖*：說明如何透過法規虛擬層 (`agency_mandates` 0MB) 與企業旁路透傳快取 (`Pass-Through Cache`)，將本機 DB 體積自 180MB 精簡至 5MB，兼具離線穩定與線上即時性。
  - **2.5 三層式跨專案 Co-work 協作模式 (`DomainRegistryResolver`)**
    - 🎯 *寫作意圖*：介紹 `DomainRegistryResolver` 導航器，示範母子專案如何於 CLI 工具層、Core DB 實體直連層與 Library 免安裝動態注入層實現雙向無縫協作。

---

### **[第 3 章：GOV-300 核心資料庫與 12 大實體表圖鑑百科](03_db_glossary.md)**
* 🎯 **本章寫作意圖**：作為開發者與資料工程師的「全量實體對照百科全書」。詳細剖析 `master_agencies.sqlite` (4 張表) 與 `universal_keys.sqlite` (8 張表) 共 **12 大實體資料表** 的 DDL 欄位設計、`attributes_json` 實體應用、索引最佳化、外鍵關係與追溯管線。
  
  #### **Part A: `master_agencies.sqlite` 權威機關與領域註冊庫 (4 大實體表)**
  - **3.1 機關權威主檔表 (`master_agencies`)**
    - 🎯 *寫作意圖*：解構全台 7,956 筆官方權威 OID（含組織樹父子關聯 `parent_oid`、層級 `level_type` 與 `attributes_json` 中的地址、DN 與 spec_version）之 Schema。
  - **3.2 機關處務規程與法定職掌虛擬表 (`agency_mandates`)**
    - 🎯 *寫作意圖*：說明法規虛擬層 (Virtual Law Layer) 之 Schema 結構，解構本機 0MB 開銷連線 PostgreSQL/law_db MCP 查詢處務規程之原理。
  - **3.3 發布機關別名對照表 (`publisher_aliases`)**
    - 🎯 *寫作意圖*：詳述 708 筆 data.gov.tw 異質發布名稱對齊至 OID 的 `confidence_score` (1.0/0.9/0.8) 與 `attributes_json` 匹配標籤。
  - **3.4 部會子專案實體展開註冊表 (`domain_deployments`)**
    - 🎯 *寫作意圖*：揭露部會子專案 (`tw-agro-db`, `tw-moi-db`) 於母專案註冊之相對路徑 `repo_path`、根 OID 與 `attributes_json` 維護團隊標籤。

  #### **Part B: `universal_keys.sqlite` 五大通用基石庫 (8 大實體表)**
  - **3.5 行政區劃主檔表 (`admin_codes`)** [基石二]
    - 🎯 *寫作意圖*：解析 480 筆 6 碼國家標準行政區劃程式碼 (22 縣市 + 368 鄉鎮市區) 之權威定址 Schema。
  - **3.6 全國地籍段名段號表 (`cadastral_registry`)** [基石二]
    - 🎯 *寫作意圖*：解析全台地籍段名與段程式碼正則化 `cadastral_id` 的實體 Schema 與索引設計。
  - **3.7 郵遞區號與地址對照表 (`zipcode_registry`)** [基石二]
    - 🎯 *寫作意圖*：解析 372 筆 3 碼本機郵遞區號實體表，並說明如何與 6 碼線上投遞區號進行介面整合。
  - **3.8 水系河川主檔表 (`river_registry`)** [基石三]
    - 🎯 *寫作意圖*：剖析 122 條國家水系與主幹流域程式碼 (`river_id`) 之全台水文定址 Schema。
  - **3.9 氣象與環境監測站點主檔表 (`station_registry`)** [基石三]
    - 🎯 *寫作意圖*：剖析 450 個中央氣象署與環境部官方測站 (經緯度 WGS84、測站類型 `WEATHER`/`WATER_QUALITY`) 之空間 Schema。
  - **3.10 法人與企業旁路透傳快取表 (`corporate_registry`)** [基石四]
    - 🎯 *寫作意圖*：詳述 1,103 筆熱門 Seed 上市/國營企業快取表，解構 TTL 淘汰機制與 GCIS API Pass-Through Cache 模式。
  - **3.11 農會與非營利組織法人主檔表 (`npo_registry`)** [基石四]
    - 🎯 *寫作意圖*：解析 23,218 筆依法登記 NGO、基金會與 342 家農漁會法人程式碼與地址 Schema。
  - **3.12 行政機關辦公日曆表 (`calendar_registry`)** [基石五]
    - 🎯 *寫作意圖*：解析 1,199 筆 2018-2026 政府辦公日曆（含放假日 `is_holiday` 與颱風假分類 `holiday_category`）之時序 Schema。

  #### **Part C: 追溯與擴充中繼管線**
  - **3.13 實體表 `attributes_json` 欄位解析器與 SDK 動態讀寫指南 (`GovBaseEntity`)**
    - 🎯 *寫作意圖*：介紹 Core SDK `GovBaseEntity.to_json()` 與 `from_json()` 如何透明解析與寫入 `attributes_json` 中的 Sys Meta。
  - **3.14 資料來源追溯中繼檔 (`datasource_metadata.json`) 與 CI/CD**
    - 🎯 *寫作意圖*：說明如何將資料來源追溯解耦至獨立 JSON 檔案，確保 SQLite Schema 純粹性並支援 Git-friendly 版號控管。

---

### **[第 4 章：跨部會 Synergy 協同合約與 Spec 權責文檔治理專章](04_synergy_contracts.md)**
* 🎯 **本章寫作意圖**：作為所有部會子專案對接母專案 `GOV-300` 的「權威跨部會協同介面與 Spec 權責文檔治理專章」。詳細解構母子專案在 Spec 權責劃分、 Single Source of Truth 與兩階段生命週期（孵化 ➔ 歸位）上的治理機制，並彙集各部會協同合約。
  - **4.0 母子專案 Spec 權責劃分、生命週期與 Single Source of Truth 規範 (`[SPC-012]`)**
    - 🎯 *寫作意圖*：解構母子專案的三層 Spec 權責劃分與生命週期規範（母專案底座規格 `spec_gov_300.md`、跨專案協同合約 `spec_gov_[code]_synergy.md` Symlink 共享、子專案獨立業務規格 `AXX_SPECIFICATION.md` 與兩階段生命週期）。
  - **4.A19 GOV-A19 農業部 (tw-agro-db) 跨專案協同合約 (`spec_gov_a19_synergy.md`)**
    - 🎯 *寫作意圖*：彙整 `GOV-A19` 農業部與 `GOV-300` 的 4 大協同情境：342 家農漁會實體歸併、農地 6 碼門牌即時線上反查、450 氣象測站寒害災防衝擊預警，與 `agro_cli.py` 跨專案 CLI 調用。
  - **4.A13 GOV-A13 內政部 (tw-moi-db) 跨專案協同合約 (`spec_gov_a13_synergy.md`)**
    - 🎯 *寫作意圖*：彙整 `GOV-A13` 內政部與 `GOV-300` 的 3 大協同情境：全國地籍段號 (`cadastral_id`) 權威對照、7,748 村里邊界與 TGOS 門牌地碼反查，以及與 `GOV-A19` 農業部進行跨部會特定農業區國土利用聯防。
  - **4.A09 GOV-A09 經濟部 (tw-moea-db) 跨專案協同合約 (`spec_gov_a09_synergy.md` - 預留)**
    - 🎯 *寫作意圖*：規劃 `GOV-A09` 經濟部與 `GOV-300` 的 160 萬全量公司商業登記 Pass-Through 快取寫回，與水利署水庫集水區水文數據協同藍圖。

---

### **[第 5 章：四大人群實戰 Playbook 與 Agent 協同指南](05_stakeholder_playbooks.md)**
* 🎯 **本章寫作意圖**：以「角色與場景為導向 (Role-Oriented)」，提供 4 類關鍵利害關係人之實踐手冊與操作劇本。
  - **5.1 政府開放資料分析師：跨部會別名對齊與資料清洗 Playbook**
    - 🎯 *寫作意圖*：提供資料分析師運用 `align_publisher_oid()` 與 `clean_datetime()` 快速清洗異質政府資料的步驟指南。
  - **5.2 AI 系統架構師：GraphRAG 零幻覺 Grounding 與多 Agent 拓樸 Playbook**
    - 🎯 *寫作意圖*：引導 AI 架構師利用 `GOV-300` 權威實體對合鍵建立零幻覺 RAG 知識圖譜與多 Agent 協同架構。
  - **5.3 企業法務與合規團隊：上市/國營 Seed 與 GCIS API 旁路快取 Playbook**
    - 🎯 *寫作意圖*：說明企業法務如何利用 1,103 筆 Seed 快取進行企業身份校驗，並於 Cache Miss 時自動連線 GCIS API。
  - **5.4 軟體工程師：Python API 程式開發與跨專案 Co-work 開發指南**
    - 🎯 *寫作意圖*：提供工程師使用 Python Core SDK (`BaseDomainAdapter`, `DomainRegistryResolver`) 進行模組化開發與單元測試之規範。

---

### **[第 6 章：系統工程驗證、單元測試網與 QGIS 軟體定義地圖](06_system_engineering_and_sdm.md)**
* 🎯 **本章寫作意圖**：展示專案在品質治理、自動化測試與空間視覺化上的硬核工程實踐。
  - **6.1 SE-6D 系統工程追溯鏈 (`REQ` ➔ `SPC` ➔ `DSN` ➔ `ADR` ➔ `TCV` ➔ `CHG`)**
    - 🎯 *寫作意圖*：說明如何運用 `se_manager.py` 進行 6 大系統工程維度與唯一 ID 追溯鏈的 100% 合規審計。
  - **6.2 全自動化單元測試網與 100% 綠燈稽核驗證矩陣**
    - 🎯 *寫作意圖*：呈現 `test_five_pillars.py` 與 `test_domain_registry_resolver.py` 之測試案例矩陣與驗證結果。
  - **6.3 軟體定義地圖 (SDM) 與 QGIS 全台行政區、水系空間視覺化**
    - 🎯 *寫作意圖*：介紹如何運用 QGIS 軟體定義地圖 (SDM) 將 `admin_codes` 與 `river_registry` 空間數據動態渲染為高畫質主題圖。
  - **6.4 專案自動化維運與開源部署指南**
    - 🎯 *寫作意圖*：提供外接硬碟 `/Volumes/D2024/data/gov-db-in/db` 與軟連結 (`ln -s`) 之運維復原手冊。

---

### **[第 7 章：結語與跨部會生態展望](07_conclusion.md)**
* 🎯 **本章寫作意圖**：總結階段性成果，並展望跨部會資料大聯盟之未來地圖。
  - **7.1 結語：打破跨部會資料孤島的通用基石底座**
    - 🎯 *寫作意圖*：總結 `GOV-300` 作為全台灣政府資料治理通用基石的技術貢獻與階段性里程碑。
  - **7.2 延伸展望：從 `GOV-300` 到 `GOV-A19` (農業部)、`GOV-A13` (內政部) 的全台資料聯盟**
    - 🎯 *寫作意圖*：描繪結合 `GOV-A19` (農糧/食安)、`GOV-A13` (國土/地籍)、`GOV-A09` (經濟/商業) 打造「全台灣大數據黃金三角」的長遠展望。

---

### **[附錄 (Appendix)](08_appendices.md)**
* 🎯 **本章寫作意圖**：提供可直接查閱與複製的工具箱與參考手冊。
  - **附錄 A：GOV-300 全庫 DDL 腳本與完整 Schema 字典**
    - 🎯 *寫作意圖*：提供 `schema.sql` 全庫 DDL 腳本與欄位型態速查表。
  - **附錄 B：`opendata_cli.py` 與 `master_agencies_cli.py` 指令速查手冊**
    - 🎯 *寫作意圖*：提供命令列工具 CLI 參數、子命令 (含 `zipcode`) 與範例輸出手冊。
  - **附錄 C：`gov-db-wizard` Agent 技能調用手冊**
    - 🎯 *寫作意圖*：提供 `.agent/skills/gov-db-wizard/SKILL.md` 之 Agent 指令與 Python 調用範例。
