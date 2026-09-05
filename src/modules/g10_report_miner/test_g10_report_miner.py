#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G10 gov-report-miner 核心與母大腦對接單元測試套件
"""

import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent
GOV_SRC = MODULE_ROOT.parents[1]
if str(GOV_SRC) not in sys.path:
    sys.path.insert(0, str(GOV_SRC))

from modules.g10_report_miner.g10_core import get_db_summary, validate_oid_exists, init_db

def test_g10_core_and_guardrails():
    init_db()
    summary = get_db_summary()
    assert "total_reports" in summary
    assert "namespace_status" in summary
    assert len(summary["namespace_status"]) == 4

    # 剛性防線一測試 (合法/暫存 OID)
    assert validate_oid_exists("UNKNOWN_PENDING") == True
    assert validate_oid_exists("2.16.886.101.20003") == True  # 行政院 OID

    # 剛性防線一測試 (不合法 OID 必須拋出 KeyError)
    try:
        validate_oid_exists("9.9.999.INVALID.OID")
        assert False, "不合法 OID 未能拋出 KeyError"
    except KeyError:
        pass  # 預期行為

    print("✅ G10 gov-report-miner 核心與 4 道剛性防線單元測試綠燈通過！")

if __name__ == "__main__":
    test_g10_core_and_guardrails()
