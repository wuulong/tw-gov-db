#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
title: 台灣營利事業 8 碼統一編號 (BAN) 雙軌驗證引擎
description: 純 Python 實作加權檢查碼演算法，完整支援舊制除 10、第 7 位為 7 雙重判定、以及 2023 年 4 月財政部新制除 5/10 邏輯與文字串流萃取。
category: validator
dependencies: none (Standard Library only)
"""

import re
from typing import Dict, Any, List, Optional, Tuple

# 官方固定加權係數
WEIGHTS = [1, 2, 1, 2, 1, 2, 4, 1]

class BanValidator:
    """
    台灣統一編號檢核演算法引擎
    """

    @staticmethod
    def clean_tax_id(raw: str) -> Optional[str]:
        """清理輸入字串，返回 8 碼純數字，若格式不符則回傳 None"""
        if not raw or not isinstance(raw, str):
            return None
        cleaned = re.sub(r"[\s\-_]", "", raw.strip())
        if re.fullmatch(r"\d{8}", cleaned):
            return cleaned
        return None

    @classmethod
    def validate(cls, raw: str, mode: str = "both") -> Dict[str, Any]:
        """
        核心檢核函式
        :param raw: 輸入統編字串
        :param mode: "both" (預設), "strict" (僅舊制除 10), "current" (僅 2023 新制)
        :return: 結構化檢驗結果
        """
        tax_id = cls.clean_tax_id(raw)
        if not tax_id:
            return {
                "tax_id": raw,
                "is_valid": False,
                "error": "INVALID_FORMAT",
                "valid_by_legacy": False,
                "valid_by_current": False,
                "has_special_rule_7": False,
                "checksum": 0,
                "explanation": "格式錯誤，必須為 8 位純數字"
            }

        digits = [int(c) for c in tax_id]
        products = [d * w for d, w in zip(digits, WEIGHTS)]

        # 計算各位數和 (Digit Sum)
        digit_sums = [(p // 10) + (p % 10) for p in products]
        total_sum = sum(digit_sums)

        has_rule_7 = (digits[6] == 7)
        # 第 7 位是 7 時的特例總和替換：
        # 當 digits[6] == 7 時，products[6] = 28，其位數和為 2 + 8 = 10。
        # 特例演算法允許將位數和視為 1 (即 1 + 0)，此時替換後的總和為 total_sum - 10 + 1 = total_sum - 9
        alt_sum = total_sum - 9 if has_rule_7 else total_sum

        # 1. 舊制 (Legacy): 總和可被 10 整除 (若第 7 位為 7，替代總和可被 10 整除亦可)
        valid_legacy = (total_sum % 10 == 0) or (has_rule_7 and alt_sum % 10 == 0)

        # 2. 2023 新制 (Current, 財政部 112 年 4 月實施):
        # 總和可被 10 或 5 整除 (若第 7 位為 7，替代總和亦可被 10 或 5 整除)
        valid_current = (total_sum % 10 == 0 or total_sum % 5 == 0) or \
                        (has_rule_7 and (alt_sum % 10 == 0 or alt_sum % 5 == 0))

        if mode == "strict":
            is_valid = valid_legacy
        elif mode == "current":
            is_valid = valid_current
        else:
            is_valid = valid_current or valid_legacy

        explanation = []
        if is_valid:
            if valid_legacy:
                explanation.append("符合舊制加權除10規範")
            if valid_current and not valid_legacy:
                explanation.append("符合2023年4月財政部新制除5規範")
            if has_rule_7:
                explanation.append("適用第七位數為7之雙重檢查特例")
        else:
            explanation.append("加權校驗碼總和不符規範")

        return {
            "tax_id": tax_id,
            "is_valid": is_valid,
            "error": None if is_valid else "CHECKSUM_FAILED",
            "valid_by_legacy": valid_legacy,
            "valid_by_current": valid_current,
            "has_special_rule_7": has_rule_7,
            "checksum": total_sum,
            "alt_checksum": alt_sum if has_rule_7 else None,
            "explanation": "；".join(explanation)
        }

    @classmethod
    def extract_from_text(cls, text: str) -> List[Dict[str, Any]]:
        """
        從任意文本中搜尋所有 8 碼數字候選，並自動剔除偽碼，返回合法統編清單
        """
        if not text or not isinstance(text, str):
            return []

        # 找出所有 8 碼數字邊界
        candidates = re.findall(r"\b\d{8}\b", text)
        results = []
        seen = set()

        for cand in candidates:
            if cand in seen:
                continue
            # 排除明顯西元年月日特徵 (如 19xx, 20xx 開頭且月份日期合理)
            if cand.startswith(("19", "20")):
                year = int(cand[:4])
                month = int(cand[4:6])
                day = int(cand[6:8])
                if 1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
                    # 這是標準年月日，跳過
                    continue

            val_res = cls.validate(cand)
            if val_res["is_valid"]:
                seen.add(cand)
                results.append(val_res)

        return results
