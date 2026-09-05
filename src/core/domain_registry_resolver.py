#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: DomainRegistryResolver 跨專案服務與模組註冊解析器
description: 提供母專案 (tw-gov-db) 與子專案 (tw-agro-db 等) 讀取 domain_map_config.json 實現自動定位、動態模組載入與資料庫連線。
category: core
dependencies: json, pathlib, importlib
"""

import json
import os
import sys
import importlib
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

DEFAULT_MAP_PATHS = [
    Path("/Volumes/D2024/data/gov-db-in/domain_map_config.json"),
    Path(__file__).resolve().parents[2] / "domain_map_config.json"
]

class DomainRegistryResolver:
    """
    [Core SDK] 跨專案領域地圖導航器 (Domain Map Resolver)
    """
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._resolve_config_path()
        self.map_data = self._load_config()

    def _resolve_config_path(self) -> Path:
        for p in DEFAULT_MAP_PATHS:
            if p.exists():
                return p
        raise FileNotFoundError(f"無法找到 domain_map_config.json，搜尋路徑: {DEFAULT_MAP_PATHS}")

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_domain_info(self, domain_id_or_code: str) -> Dict[str, Any]:
        """支援傳入 domain_id (tw-gov-db) 或專案代號 (G00, A10) 定位專案"""
        domains = self.map_data.get("domains", {})
        
        # 1. 直接比對 Key (G00, A10) 或 domain_id
        if domain_id_or_code in domains:
            return domains[domain_id_or_code]

        # 2. 搜尋程式碼或 ID 匹配項
        for code, info in domains.items():
            if info.get("domain_id") == domain_id_or_code or info.get("project_code") == domain_id_or_code:
                return info

        raise KeyError(f"未在 domain_map_config.json 中註冊該領域代號或 ID: {domain_id_or_code}")

    def get_shared_db_path(self, db_filename: str) -> Path:
        """取得共享資料庫路徑 (優先順序: 1. 環境變數 GOV_DB_SHARED_DIR 2. 外接硬碟 3. 本地 fallback)"""
        # 1. 優先讀取環境變數 GOV_DB_SHARED_DIR
        env_dir = os.environ.get("GOV_DB_SHARED_DIR")
        if env_dir and Path(env_dir).exists():
            return Path(env_dir) / db_filename

        # 2. 次優先讀取外接硬碟預設路徑 /Volumes/D2024/data/gov-db-in/db
        ext_dir = Path(self.map_data.get("shared_db_dir", "/Volumes/D2024/data/gov-db-in/db"))
        return ext_dir / db_filename

    def bootstrap_domain_python_path(self, target_domain_id: str):
        """強韌化功能: 自動將目標 Domain 專案之 src 加入 sys.path，實現免安裝 import 跨專案呼叫"""
        info = self.get_domain_info(target_domain_id)
        pkg_path = info.get("python_package_path") or str(Path(info["local_repo_path"]) / "src")
        if pkg_path and pkg_path not in sys.path:
            sys.path.insert(0, pkg_path)
            print(f"🔗 [DomainRegistryResolver] 已將 {target_domain_id} 核心套件注入 sys.path: {pkg_path}")

    def load_domain_adapter_class(self, domain_id: str):
        """動態加載目標領域 Adapter 類別 (如載入 tw-agro-db 的 AgroAdapter)"""
        self.bootstrap_domain_python_path("tw-gov-db")
        info = self.get_domain_info(domain_id)
        self.bootstrap_domain_python_path(domain_id)
        
        module_path = info.get("entry_adapter_module")
        if not module_path:
            raise ValueError(f"領域 {domain_id} 未設定 entry_adapter_module")
        
        module = importlib.import_module(module_path)
        return module

    def run_domain_cli(self, domain_id: str, subcommand: str, extra_args: Optional[List[str]] = None) -> str:
        """CLI Co-work 功能: 跨專案直接呼叫目標領域的 CLI 工具 (如呼叫 tw-agro-db 的 agro_cli.py)"""
        import subprocess
        info = self.get_domain_info(domain_id)
        cli_script = info.get("cli_entry_script")
        if not cli_script or not Path(cli_script).exists():
            raise FileNotFoundError(f"領域 {domain_id} 的 CLI 工具不存在: {cli_script}")

        cmd = [sys.executable, cli_script, subcommand]
        if extra_args:
            cmd.extend(extra_args)

        print(f"🚀 [CLI Co-work] 正在跨專案呼叫 {domain_id} CLI: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"跨專案 CLI 呼叫失敗 ({res.stderr.strip()})")
        return res.stdout.strip()

    def get_domain_core_db_connection(self, domain_id: str, db_name: Optional[str] = None) -> sqlite3.Connection:
        """Core DB 整合功能: 取得目標領域核心整合 DB (如 tw-agro-db 的 agro_integrated.sqlite) 之連線"""
        info = self.get_domain_info(domain_id)
        core_dbs = info.get("core_dbs", [])
        target_db_name = db_name or (core_dbs[0] if core_dbs else None)
        
        if not target_db_name:
            raise ValueError(f"領域 {domain_id} 未註冊核心資料庫")

        db_path = self.get_shared_db_path(target_db_name)
        if not db_path.exists():
            # 備援嘗試本地 repo 內之路徑 (優先 db/ 其次 ontology/)
            repo_base = Path(info["local_repo_path"])
            db_path_sub = repo_base / "db" / target_db_name
            if db_path_sub.exists():
                db_path = db_path_sub
            else:
                db_path = repo_base / "ontology" / target_db_name

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn
