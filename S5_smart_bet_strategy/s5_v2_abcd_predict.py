"""S5 v2 ABCD 走勢及主力／配腳預測。"""
from __future__ import annotations

import csv
from collections import Counter
from typing import TypedDict, cast

try:
    from .s5_v2_config import GROUPS
except ImportError:  # 允許直接由 s5_v2_backtest_main.py 路徑執行
    from s5_v2_config import GROUPS


class Draw(TypedDict):
    """標準化後的一期開獎資料格式。"""

    date: str
    numbers: list[int]


def read_draws(path) -> list[Draw]:
    """讀取 M6 開獎 CSV，轉成日期及 N1–N7 號碼列表。"""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        result = []
        for row in rows:
            numbers = [int(row[f"N{i}"]) for i in range(1, 7)]
            special = int(row.get("N7") or 0)
            if 1 <= special <= 40:
                numbers.append(special)
            result.append({"date": row.get("nDdate", row.get("ndate", "")), "numbers": numbers})
        return [row for row in result if row["date"]]


def _group_numbers(numbers: list[int], group: str) -> list[int]:
    """取出指定 ABCD 組別內的開獎號碼，並移除重複號碼。"""
    return sorted(set(numbers) & set(GROUPS[group]))


def analyze_window(window: list[Draw]) -> dict[str, object]:
    """分析窗口期的球數走勢、組別強度、主力組、配腳組及 HFB/HFL。"""
    totals = {group: 0 for group in GROUPS}
    counts = {group: Counter() for group in GROUPS}
    trends = {group: [] for group in GROUPS}
    for draw in window:
        for group in GROUPS:
            nums = _group_numbers(draw["numbers"], group)
            totals[group] += len(nums)
            counts[group].update(nums)
            trends[group].append(len(nums))
    denominator = len(window) * 7
    strength = {
        group: totals[group] / (denominator * len(GROUPS[group]) / 40)
        for group in GROUPS
    }
    main = sorted((g for g in GROUPS if g != "D"), key=lambda g: (-strength[g], -totals[g], g))[0]
    supports = sorted((g for g in GROUPS if g != main), key=lambda g: (-strength[g], -totals[g], g))
    hfb, hfl = {}, {}
    for group in GROUPS:
        ordered = sorted(counts[group], key=lambda n: (-counts[group][n], n))
        hfb[group] = [n for n in ordered if counts[group][n] >= 2]
        hfl[group] = [n for n in ordered if counts[group][n] == 1]
    return {"totals": totals, "strength": strength, "trends": trends, "main": main, "supports": supports, "hfb": hfb, "hfl": hfl}


def candidate_groups(analysis: dict[str, object]) -> dict[str, list[int]]:
    """合併各組 HFB 與 HFL，建立本期動態候選球池。"""
    hfb = cast(dict[str, list[int]], analysis["hfb"])
    hfl = cast(dict[str, list[int]], analysis["hfl"])
    return {group: list(dict.fromkeys(hfb[group] + hfl[group])) for group in GROUPS}
