#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G10 gov-report-miner CGS v2.0 主控 CLI 工具
__cli_spec_version__ = "2.0"
"""

import sys
import os
import json
from typing import Optional
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

MODULE_ROOT = Path(__file__).resolve().parent
GOV_SRC = MODULE_ROOT.parents[1]
if str(GOV_SRC) not in sys.path:
    sys.path.insert(0, str(GOV_SRC))

from modules.g10_report_miner.g10_core import (
    get_db_summary,
    get_catalog_registry,
    register_and_ingest_catalog,
    fetch_report_by_uid,
    init_db
)

app = typer.Typer(help="🏛️ G10 gov-report-miner 政府研究報告探勘與典藏工具 (CGS v2.0)")
console = Console()

@app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", "-j", help="輸出單行緊湊 JSON 格式 (省 Token)")
):
    """查詢 G10 報告索引庫筆數、快取狀態與代號系統能力矩陣看板"""
    summary = get_db_summary()
    
    if json_output:
        print(json.dumps(summary, ensure_ascii=False))
        return

    console.print("[bold green]📊 G10 gov-report-miner 運作狀態與代號系統能力矩陣看板[/bold green]\n")
    
    table = Table(title="代號系統能力矩陣 (sys_namespace_status)")
    table.add_column("代號系統", style="cyan")
    table.add_column("名稱", style="magenta")
    table.add_column("有總表?", style="yellow")
    table.add_column("總表已載?", style="green")
    table.add_column("總表筆數", justify="right")
    table.add_column("自動化能力", style="bold blue")

    for ns in summary["namespace_status"]:
        table.add_row(
            ns["namespace_code"],
            ns["namespace_name"],
            "✅ 是" if ns["has_master_catalog"] else "❌ 否",
            "✅ 是" if ns["catalog_ingested"] else "❌ 否",
            f"{ns['catalog_total_count']:,}",
            ns["auto_download_level"]
        )

    console.print(table)
    console.print("\n📁 [report_index.sqlite] 實體報告統計:")
    console.print(f"  └── 📋 [全量報告索引 (report_index)]: {summary['total_reports']} 筆")
    console.print(f"  └── 📋 [實體檔已快取 (is_cached=1)]: {summary['cached_reports']} 筆")
    console.print(f"  └── 📋 [待歸檔暫存 (UNKNOWN_PENDING)]: {summary['staged_reports']} 筆")

@app.command("catalogs")
def catalogs(
    json_output: bool = typer.Option(False, "--json", "-j", help="輸出單行緊湊 JSON 格式")
):
    """查詢已註冊與驗證之總表地圖 (sys_master_catalog_registry)"""
    registry = get_catalog_registry()
    if json_output:
        print(json.dumps(registry, ensure_ascii=False))
        return

    console.print("[bold green]📊 G10 已註冊與驗證之總表追溯地圖 (sys_master_catalog_registry)[/bold green]\n")
    table = Table(title="總表註冊與驗證狀態表")
    table.add_column("總表 ID", style="cyan")
    table.add_column("總表名稱", style="magenta")
    table.add_column("歸屬 OID", style="yellow")
    table.add_column("驗證狀態", style="bold green")
    table.add_column("剖析筆數", justify="right")

    for c in registry:
        table.add_row(
            c["catalog_id"],
            c["catalog_title"],
            c["agency_oid"],
            c["verification_status"],
            f"{c['total_items_count']:,}"
        )

    console.print(table)

@app.command("ingest-catalog")
def ingest_catalog_cmd(
    dataset_id: str = typer.Option(..., "--dataset-id", "-d", help="開放資料平台 Dataset ID"),
    agency_oid: str = typer.Option(..., "--oid", "-o", help="權威發布機關 OID"),
    title: str = typer.Option(..., "--title", "-t", help="總表名稱"),
    url: str = typer.Option(..., "--url", "-u", help="總表實體 CSV/JSON 下載網址"),
    json_output: bool = typer.Option(False, "--json", "-j", help="單行緊湊 JSON 輸出")
):
    """【正式工具命令】線上下載、剖析並註冊 Open Data 總表"""
    console.print(f"[bold yellow]🔄 發動總表探勘與採集: Dataset [{dataset_id}] {title}...[/bold yellow]")
    res = register_and_ingest_catalog(
        dataset_id=dataset_id,
        agency_oid=agency_oid,
        title=title,
        download_url=url
    )
    if json_output:
        print(json.dumps(res, ensure_ascii=False))
        return

    console.print(f"[bold green]✅ 總表 [{res['catalog_id']}] 採集剖析成功！驗證狀態: {res['verification_status']}, 剖析寫入 {res['items_parsed']} 筆報告！[/bold green]")

@app.command("fetch")
def fetch_cmd(
    report_uid: str = typer.Argument(..., help="報告唯一識別碼 (report_uid)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="單行緊湊 JSON 輸出")
):
    """【正式工具命令】二階段按需採集下載實體報告 PDF/CSV 檔案"""
    console.print(f"[bold yellow]🔄 發動二階段按需採集: [{report_uid}]...[/bold yellow]")
    res = fetch_report_by_uid(report_uid)
    if json_output:
        print(json.dumps(res, ensure_ascii=False))
        return

    console.print(f"[bold green]✅ 報告 [{res['report_uid']}] 下載成功！[/bold green]")
    console.print(f"  • 本地快取路徑: [cyan]{res['local_cache_path']}[/cyan]")
    console.print(f"  • SHA256 雜湊碼: {res['file_sha256']}")

@app.command("batch-probe")
def batch_probe_cmd(
    json_output: bool = typer.Option(False, "--json", "-j", help="單行緊湊 JSON 輸出")
):
    """【正式工具命令】自動批量探勘與下載驗證全量未測試之潛力總表 Dataset"""
    console.print("[bold yellow]🚀 發動全量開放資料潛力總表批量探勘與驗證 (batch-probe)...[/bold yellow]\n")
    from modules.g10_report_miner.g10_core import batch_probe_untested_catalogs
    res = batch_probe_untested_catalogs()
    
    if json_output:
        print(json.dumps(res, ensure_ascii=False))
        return

    console.print(f"[bold green]✅ 批量探勘完成！[/bold green]")
    console.print(f"  • 未測試總表總數: {res['untested_total']} 筆")
    console.print(f"  • 驗證成功 (CONFIRMED_VALID): [bold green]{res['confirmed_valid']} 筆[/bold green]")
    console.print(f"  • 排除/無效 (REJECTED_INVALID): [bold red]{res['rejected_invalid']} 筆[/bold red]\n")

    table = Table(title="批量探勘驗證結果彙整")
    table.add_column("Dataset ID", style="cyan")
    table.add_column("總表名稱", style="magenta")
    table.add_column("歸併機關/OID", style="yellow")
    table.add_column("驗證狀態", style="bold green")
    table.add_column("剖析筆數", justify="right")

    for d in res["details"]:
        status_str = "🟢 CONFIRMED" if d["status"] == "CONFIRMED_VALID" else "🔴 REJECTED"
        table.add_row(
            d["dataset_id"],
            d["title"][:25],
            f"{d['agency_raw']}\n({d['agency_oid']})",
            status_str,
            f"{d['items_parsed']:,}"
        )

    console.print(table)

@app.command("match-gpn")
def match_gpn_cmd(
    query_key: str = typer.Argument(..., help="GRB 案號 (PROJKEY) 或計畫名稱關鍵字"),
    json_output: bool = typer.Option(False, "--json", "-j", help="單行緊湊 JSON 輸出")
):
    """【正式工具命令】機制 A 碰撞對位：用 GRB 案號對位國家圖書館 GPN 下載服務"""
    from modules.g10_report_miner.g10_core import match_grb_to_gpn
    res = match_grb_to_gpn(query_key)
    
    if json_output:
        print(json.dumps(res, ensure_ascii=False))
        return

    if res["status"] == "NOT_FOUND":
        console.print(f"[bold red]❌ {res['message']}[/bold red]")
        return

    console.print(f"[bold green]🔗 【機制 A 碰撞成功】找到匹配的 GRB 計畫對位條目！[/bold green]")
    console.print(f"  • GRB 報告 UID   : [cyan]{res['report_uid']}[/cyan]")
    console.print(f"  • 計畫名稱       : {res['title']}")
    console.print(f"  • GRB 案號       : [yellow]{res['grb_projkey']}[/yellow]")
    console.print(f"  • 全文可達性狀態 : {res['availability_desc']}")
    console.print(f"  • 匹配 GPN 號    : [bold green]{res['matched_gpn_uid']}[/bold green]")
    console.print(f"  • 國圖/門戶網址  : {res['gpn_download_url']}")

@app.command("ingest-grb")
def ingest_grb_cmd(
    xml_path: str = typer.Option("events-2026Q3/gov-db-in/tw-gov-db/data/reports/catalogs_cache/GRB_113.xml", "--xml", "-x", help="GRB XML 總表檔案路徑"),
    limit: int = typer.Option(0, "--limit", "-n", help="限制寫入筆數 (0 表示全量)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="單行緊湊 JSON 輸出")
):
    """【正式工具命令】將 GRB 全量 23,116 筆研究計畫大腦寫入 grb_projects 專用資料表"""
    from modules.g10_report_miner.g10_core import ingest_grb_catalog_full
    console.print(f"[bold yellow]🚀 發動 GRB 全量大腦資料庫寫入作業: [{xml_path}]...[/bold yellow]")
    
    res = ingest_grb_catalog_full(Path(xml_path), limit=limit)
    
    if json_output:
        print(json.dumps(res, ensure_ascii=False))
        return

    console.print(f"[bold green]🎉 【GRB 專用表灌庫完成】已成功寫入 {res['inserted_count']:,} 筆全量研究計畫條目至 `{res['table_name']}` 資料表！[/bold green]")

@app.command("search-grb")
def search_grb_cmd(
    kw: Optional[str] = typer.Option(None, "--kw", "-k", help="計畫名稱或關鍵字"),
    pi: Optional[str] = typer.Option(None, "--pi", "-p", help="計畫主持人姓名"),
    limit: int = typer.Option(10, "--limit", "-n", help="顯示筆數上限"),
    json_output: bool = typer.Option(False, "--json", "-j", help="單行緊湊 JSON 輸出")
):
    """【正式工具命令】多維度智慧檢索 GRB 57.6萬筆研究計畫資料庫"""
    from modules.g10_report_miner.g10_core import search_grb_projects
    res = search_grb_projects(kw=kw, pi=pi, limit=limit)

    if json_output:
        print(json.dumps(res, ensure_ascii=False))
        return

    console.print(f"[bold green]🔍 【GRB 檢索結果】找到 {res['total_results']} 筆符合條件之研究計畫：[/bold green]\n")
    table = Table(title="GRB 研究計畫檢索結果")
    table.add_column("UID / PROJKEY", style="cyan")
    table.add_column("年度", justify="center")
    table.add_column("計畫名稱", style="bold white")
    table.add_column("主持人 / 執行單位", style="yellow")
    table.add_column("核定預算 (千元)", justify="right", style="green")

    for r in res["results"]:
        table.add_row(
            r["projkey"],
            str(r["pub_year"]),
            r["title"][:28],
            f"{r['pi']}\n({r['exec_organ'][:15]})",
            f"{r['plan_amt']:,}" if r['plan_amt'] else "未公開"
        )

    console.print(table)

@app.command("schema")
def schema():
    """印出 G10 核心與能力看板資料表 Schema DDL"""
    ddl = """
    -- report_index 全域索引表
    CREATE TABLE report_index (
        report_uid TEXT PRIMARY KEY, agency_oid TEXT NOT NULL, title TEXT NOT NULL,
        agency_name_raw TEXT, pub_year INTEGER, authors_or_pi TEXT, source_platform TEXT NOT NULL,
        remote_url TEXT, fetch_status TEXT, file_format TEXT, is_cached INTEGER,
        local_cache_path TEXT, file_sha256 TEXT, attributes_json TEXT
    );

    -- sys_master_catalog_registry 總表註冊與追溯表
    CREATE TABLE sys_master_catalog_registry (
        catalog_id TEXT PRIMARY KEY, namespace_code TEXT NOT NULL, agency_oid TEXT NOT NULL,
        catalog_title TEXT NOT NULL, source_dataset_id TEXT, download_url TEXT NOT NULL,
        file_format TEXT, total_items_count INTEGER, verification_status TEXT,
        last_fetched_at DATETIME, last_file_sha256 TEXT, attributes_json TEXT
    );

    -- sys_namespace_status 能力看板表
    CREATE TABLE sys_namespace_status (
        namespace_code TEXT PRIMARY KEY, namespace_name TEXT NOT NULL,
        has_master_catalog INTEGER, catalog_ingested INTEGER, catalog_total_count INTEGER,
        auto_download_level TEXT, last_catalog_sync DATETIME, updated_at DATETIME
    );
    """
    console.print(ddl)

if __name__ == "__main__":
    init_db()
    app()
