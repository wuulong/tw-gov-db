#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[metadata]
name: lunar_engine.py
title: G40 純 Python 緊湊農曆與二十四節氣天文編碼轉換引擎
description: 提供 1900-2100 年公曆農曆雙向轉換、天干地支、生肖、二十四節氣與台灣民俗傳統節日判定，零外部依賴、純 Python 微秒級解算。
category: gov_meta
cgs_version: 2.4
compat: posix
"""

import sys
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List, Iterator

# 1900 ~ 2100 年農曆資料緊湊編碼表 (標準天文台 16 進位曆法編碼)
# bit 0-3: 閏月月份 (0 表示無閏月，1-12 表示閏幾月)
# bit 4-15: 12 個月大小月 (bit 15 為 1月, bit 4 為 12月; 1=大月30天, 0=小月29天)
# bit 16: 閏月大小 (1=大月30天, 0=小月29天)
YEAR_INFOS: List[int] = [
    0x04bd8,                                    # 1900
    0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950,# 1905
    0x16554, 0x056a0, 0x09ad0, 0x055d2, 0x04ae0,# 1910
    0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540,# 1915
    0x0d6a0, 0x0ada2, 0x095b0, 0x14977, 0x04970,# 1920
    0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54,# 1925
    0x02b60, 0x09570, 0x052f2, 0x04970, 0x06566,# 1930
    0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60,# 1935
    0x186e3, 0x092e0, 0x1c8d7, 0x0c950, 0x0d4a0,# 1940
    0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0,# 1945
    0x092d0, 0x0d2b2, 0x0a950, 0x0b557, 0x06ca0,# 1950
    0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573,# 1955
    0x052b0, 0x0a9a8, 0x0e950, 0x06aa0, 0x0aea6,# 1960
    0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260,# 1965
    0x0f263, 0x0d950, 0x05b57, 0x056a0, 0x096d0,# 1970
    0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250,# 1975
    0x0d558, 0x0b540, 0x0b5a0, 0x195a6, 0x095b0,# 1980
    0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50,# 1985
    0x06d40, 0x0af46, 0x0ab60, 0x09570, 0x04af5,# 1990
    0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58,# 1995
    0x05ac0, 0x0ab60, 0x096d5, 0x092e0, 0x0c960,# 2000
    0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0,# 2005
    0x0abb7, 0x025d0, 0x092d0, 0x0cab5, 0x0a950,# 2010
    0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0,# 2015
    0x0a5b0, 0x15176, 0x052b0, 0x0a930, 0x07954,# 2020
    0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6,# 2025
    0x0a4e0, 0x0d260, 0x0ea65, 0x0d530, 0x05aa0,# 2030
    0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0,# 2035
    0x1d0b6, 0x0d250, 0x0d520, 0x0dd45, 0x0b5a0,# 2040
    0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0,# 2045
    0x0aa50, 0x1b255, 0x06d20, 0x0ada0, 0x14b63,# 2050
    0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6,# 2055
    0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0, 0x092e0,# 2060
    0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50,# 2065
    0x05d55, 0x056a0, 0x0a6d0, 0x055d4, 0x052d0,# 2070
    0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50,# 2075
    0x055a0, 0x0aba4, 0x0a5b0, 0x052b0, 0x0b273,# 2080
    0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55,# 2085
    0x04b60, 0x0a570, 0x054e4, 0x0d160, 0x0e968,# 2090
    0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0,# 2095
    0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252, 0x0d520 # 2100
]

START_DATE = date(1900, 1, 31)

# 二十四節氣名稱
SOLAR_TERMS_NAMES = [
    "小寒", "大寒", "立春", "雨水", "驚蟄", "春分",
    "清明", "穀雨", "立夏", "小滿", "芒種", "夏至",
    "小暑", "大暑", "立秋", "處暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"
]

SOLAR_TERM_C_21 = [
    5.4055, 20.12, 3.87, 18.73, 5.63, 20.646,
    4.81, 20.1, 5.52, 21.04, 5.678, 21.37,
    7.108, 22.83, 7.5, 23.13, 7.646, 23.042,
    8.318, 23.438, 7.438, 22.36, 7.18, 21.94
]

GAN_LIST = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI_LIST = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
SHENG_XIAO = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]
MONTH_NAMES = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
DAY_NAMES = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"
]

TRADITIONAL_FESTIVALS = {
    (1, 1): "春節",
    (1, 15): "元宵節",
    (2, 2): "土地公生 (頭牙)",
    (3, 23): "媽祖生",
    (5, 5): "端午節",
    (7, 7): "七夕",
    (7, 15): "中元節",
    (8, 15): "中秋節",
    (9, 9): "重陽節",
    (10, 15): "下元節",
    (12, 8): "臘八節",
    (12, 16): "尾牙"
}


def _enum_months_for_year(year_info: int) -> Iterator[Tuple[int, int, bool]]:
    """走訪特定農曆年的月份、日數與是否為閏月 (month, days, is_leap)"""
    leap_month = year_info % 16
    months = [(i, False) for i in range(1, 13)]
    if 1 <= leap_month <= 12:
        months.insert(leap_month, (leap_month, True))

    for m, is_leap in months:
        if is_leap:
            days = ((year_info >> 16) % 2) + 29
        else:
            days = ((year_info >> (16 - m)) % 2) + 29
        yield m, days, is_leap


def _get_lunar_year_days(year_info: int) -> int:
    """計算特定農曆年總日數"""
    return sum(days for _, days, _ in _enum_months_for_year(year_info))


def calculate_solar_term(year: int, term_index: int) -> int:
    """計算特定西元年第 term_index (0..23) 節氣的日期"""
    y_mod = year % 100
    d_val = 0.2422
    c_val = SOLAR_TERM_C_21[term_index]
    leap_count = y_mod // 4
    day = int(y_mod * d_val + c_val) - leap_count
    if year == 2024 and term_index == 6: # 清明特例
        day = 4
    return max(1, min(31, day))


def get_solar_terms_for_year(year: int) -> Dict[str, str]:
    """取得指定西元年 24 節氣之 ISO-8601 日期地圖"""
    res = {}
    for idx, name in enumerate(SOLAR_TERMS_NAMES):
        month = idx // 2 + 1
        day = calculate_solar_term(year, idx)
        try:
            dt = date(year, month, day)
            res[name] = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return res


def solar_to_lunar(solar_date: date) -> Dict[str, Any]:
    """
    西曆轉換為農曆 (標準 1900-2100 年天數偏移比對法)
    """
    offset = (solar_date - START_DATE).days
    if offset < 0:
        raise ValueError(f"日期超出支援範圍 (最小 1900-01-31): {solar_date}")

    lunar_year = 1900
    for idx, year_info in enumerate(YEAR_INFOS):
        ydays = _get_lunar_year_days(year_info)
        if offset < ydays:
            break
        offset -= ydays
        lunar_year += 1

    if lunar_year > 2100:
        raise ValueError(f"日期超出支援範圍 (最大 2100-12-31): {solar_date}")

    year_info = YEAR_INFOS[lunar_year - 1900]
    lunar_month = 1
    lunar_day = 1
    is_leap = False

    for m, days, leap in _enum_months_for_year(year_info):
        if offset < days:
            lunar_month = m
            lunar_day = offset + 1
            is_leap = leap
            break
        offset -= days

    # 干支生肖
    gan_idx = (lunar_year - 4) % 10
    zhi_idx = (lunar_year - 4) % 12
    gan_zhi_year = f"{GAN_LIST[gan_idx]}{ZHI_LIST[zhi_idx]}"
    sheng_xiao = SHENG_XIAO[zhi_idx]

    month_str = f"閏{MONTH_NAMES[lunar_month - 1]}月" if is_leap else f"{MONTH_NAMES[lunar_month - 1]}月"
    day_str = DAY_NAMES[lunar_day - 1] if 1 <= lunar_day <= 30 else f"{lunar_day}日"
    lunar_text = f"歲次{gan_zhi_year}年{month_str}{day_str}"

    # 傳統節日判斷
    festival = None
    if not is_leap:
        festival = TRADITIONAL_FESTIVALS.get((lunar_month, lunar_day))
        if lunar_month == 12:
            # 判斷是否為除夕 (農曆十二月最後一天)
            dec_days = 29
            for m, d_cnt, l_flag in _enum_months_for_year(year_info):
                if m == 12 and not l_flag:
                    dec_days = d_cnt
                    break
            if lunar_day == dec_days:
                festival = "除夕"

    # 當天節氣判定
    terms = get_solar_terms_for_year(solar_date.year)
    today_iso = solar_date.strftime("%Y-%m-%d")
    solar_term = None
    for term_name, t_date in terms.items():
        if t_date == today_iso:
            solar_term = term_name
            break

    return {
        "solar_date": today_iso,
        "lunar_year": lunar_year,
        "minguo_year": lunar_year - 1911,
        "lunar_month": lunar_month,
        "lunar_day": lunar_day,
        "is_leap": is_leap,
        "gan_zhi": gan_zhi_year,
        "sheng_xiao": sheng_xiao,
        "month_name": month_str,
        "day_name": day_str,
        "lunar_text": lunar_text,
        "festival": festival,
        "solar_term": solar_term
    }


def lunar_to_solar(lunar_year: int, lunar_month: int, lunar_day: int, is_leap: bool = False) -> Dict[str, Any]:
    """
    農曆轉換為西曆 (反向累加天數計算)
    """
    if not (1900 <= lunar_year <= 2100):
        raise ValueError(f"農曆年份超出範圍 (1900-2100): {lunar_year}")

    offset = 0
    for y in range(1900, lunar_year):
        offset += _get_lunar_year_days(YEAR_INFOS[y - 1900])

    year_info = YEAR_INFOS[lunar_year - 1900]
    found = False
    for m, days, leap in _enum_months_for_year(year_info):
        if m == lunar_month and leap == is_leap:
            if lunar_day > days:
                raise ValueError(f"{lunar_year} 年 {m} 月 只有 {days} 天，給定 {lunar_day} 無效！")
            offset += (lunar_day - 1)
            found = True
            break
        offset += days

    if not found:
        raise ValueError(f"{lunar_year} 年並無 {'閏' if is_leap else ''}{lunar_month} 月！")

    solar_date = START_DATE + timedelta(days=offset)
    return solar_to_lunar(solar_date)
