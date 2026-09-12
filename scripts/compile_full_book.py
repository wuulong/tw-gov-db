#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 台灣政府開放資料專書 (tw-gov-db) 大一統合訂本編譯器
description: 將 book/ 目錄下 20+ 個章節與協同合約依序合龍打包為單一檔案 FULL_BOOK_TAIWAN_GOV_DB.md。
category: publishing
dependencies: none (Standard Library only)
"""

from pathlib import Path

BOOK_DIR = Path(__file__).resolve().parents[1] / "book"


def compile_book():
    ordered_files = [
        BOOK_DIR / "00_toc.md",
        BOOK_DIR / "01_vision_and_mission.md",
        BOOK_DIR / "02_architecture_overview.md",
        BOOK_DIR / "03_db_glossary.md",
    ]

    # 第 4 章：Synergy 協同合約
    synergy_dir = BOOK_DIR / "04_synergy_contracts"
    if synergy_dir.exists():
        synergy_files = sorted(synergy_dir.glob("*.md"))
        ordered_files.extend(synergy_files)

    # 第 5 章：Playbooks
    p5_main = BOOK_DIR / "05_stakeholder_playbooks.md"
    if p5_main.exists():
        ordered_files.append(p5_main)
    playbook_dir = BOOK_DIR / "05_stakeholder_playbooks"
    if playbook_dir.exists():
        playbook_files = sorted(playbook_dir.glob("*.md"))
        ordered_files.extend(playbook_files)

    # 第 6, 7, 8 章
    for ending in ["06_system_engineering_and_sdm.md", "07_conclusion.md", "08_appendices.md"]:
        p = BOOK_DIR / ending
        if p.exists():
            ordered_files.append(p)

    full_content = []
    included_count = 0
    for p in ordered_files:
        if p.exists() and p.is_file():
            full_content.append(p.read_text(encoding="utf-8"))
            included_count += 1

    target_full_book = BOOK_DIR / "FULL_BOOK_TAIWAN_GOV_DB.md"
    target_full_book.write_text("\n\n---\n\n".join(full_content), encoding="utf-8")
    size_kb = round(target_full_book.stat().st_size / 1024, 1)
    print(f"[+] 專書編譯成功！已合龍 {included_count} 個章節檔案至 {target_full_book.name} (大小: {size_kb} KB)")


if __name__ == "__main__":
    compile_book()
