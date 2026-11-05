"""S5 v3：使用預測組別走勢及動態候選池，驗證全部 11 個組合。"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path
from typing import cast

try:
    from .s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from .s5_v2_config import DATA_PATH, GROUPS, RANDOM_SEED, WINDOW_PERIODS
    from .s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap
except ImportError:  # 允許直接用檔案路徑執行
    from s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from s5_v2_config import DATA_PATH, GROUPS, RANDOM_SEED, WINDOW_PERIODS
    from s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap
'''
依賴 s5_v2 支程式 
每個回測期都會重新產生：
- ABCD 球數走勢
- 主力組
- 配腳組排序
- HFB 高頻膽號
- HFL 高頻腳號
- 動態候選球池
- 全部 11 個組合投注
- 當期最高命中
- 最後命中率排名
-----------------
回測期／窗口期
ABCD 走勢
主力／配腳
候選球池
11 組命中統計
總結打印格式
JSON 輸出內容

'''

VERSION = "S5_v3，動態候選球池組合驗證"
BACKTEST_PERIODS = 19 # 回測期 


POOL_NAMES = tuple(
    "+".join(groups)
    for size in (2, 3, 4)
    for groups in combinations("ABCD", size)
)
SCORES = (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)


def score(ticket: tuple[int, ...], draw_numbers: list[int]) -> float:
    main_hits = len(set(ticket) & set(draw_numbers[:6]))
    if main_hits < 6 and len(draw_numbers) >= 7 and draw_numbers[6] in ticket:
        return main_hits + 0.5
    return float(main_hits)


def validate(backtest_periods: int, window_periods: int, seed: int) -> dict[str, object]:
    draws = read_draws(DATA_PATH)
    count = min(backtest_periods, max(0, len(draws) - window_periods))
    first_target = len(draws) - count
    totals = {pool: {value: 0 for value in SCORES} for pool in POOL_NAMES}
    max_hits = {pool: 0.0 for pool in POOL_NAMES}
    total_bets = {pool: 0 for pool in POOL_NAMES}

    print(f'=== "{VERSION}" ===')
    print(f"回測期= {count}  窗口期={window_periods}，驗證組合={POOL_NAMES}")

    for offset, target_index in enumerate(range(first_target, len(draws))):
        window = draws[target_index - window_periods:target_index]
        target = draws[target_index]
        analysis = analyze_window(window)
        candidates = cast(dict[str, list[int]], candidate_groups(analysis))
        main_group = str(analysis["main"])
        supports = cast(list[str], analysis["supports"])
        trends = cast(dict[str, list[int]], analysis["trends"])
        hfb = cast(dict[str, list[int]], analysis["hfb"])
        hfl = cast(dict[str, list[int]], analysis["hfl"])

        print(f"\n{offset + 1:02d}. 核對日 {target['date']}｜主力 {main_group}｜配腳 {','.join(supports)}")
        print("ABCD 分組球數走勢：")
        for group in "ABCD":
            expected = window_periods * 7 * len(GROUPS[group]) / 40
            trend = "".join(str(value) if value else "-" for value in trends[group])
            strength = cast(dict[str, float], analysis["strength"])[group] * 100
            total = cast(dict[str, int], analysis["totals"])[group]
            print(f"{group}組：{trend} = {total} 球次 / {expected:g} = {strength:.1f}%")
        print("候選球池：")
        for index, group in enumerate("ABCD"):
            suffix = "，" if index < 3 else ""
            print(f"/> {group}[{','.join(map(str, candidates[group]))}]{suffix}")
        for pool_index, pool in enumerate(POOL_NAMES):
            pool_groups = pool.split("+")
            selected_main = main_group if main_group in pool_groups else pool_groups[0]
            bets, meta = generate_dynamic_bets(
                candidates,
                pool,
                selected_main,
                seed + offset * 100 + pool_index,
            )
            previous_numbers = draws[target_index - 1]["numbers"] if target_index > 0 else []
            bets = limit_previous_overlap(bets, candidates, previous_numbers, seed + offset * 1000 + pool_index)
            hits = [score(ticket, target["numbers"]) for ticket in bets]
            total_bets[pool] += len(hits)
            best = max(hits, default=0.0)
            max_hits[pool] = max(max_hits[pool], best)
            for hit in hits:
                if hit in totals[pool]:
                    totals[pool][hit] += 1
            print(f"  {pool:<7} {meta['pool_size']}球 / {len(bets)}注 / 最高{best:g}分")

    print(f"=== S5 V3 - 回測期 = {count}，全部動態組合驗證 總結 ===")
    ranked = []
    for pool in POOL_NAMES:
        positive = [
            f"{value:g}球={totals[pool][value]}注"
            for value in SCORES
            if totals[pool][value] >= 1
        ]
        total_3_plus = sum(totals[pool][value] for value in SCORES if value >= 3)
        hit_rate = total_3_plus / total_bets[pool] * 100 if total_bets[pool] else 0.0
        ranked.append((hit_rate, total_3_plus, max_hits[pool], pool))
        print(f"{pool:<7} {', '.join(positive) if positive else '>'}")

    print(f"=== 回測期 = {count}，命中表現排序（3 球或以上注數） ===")
    ranking_rows = []
    for rank, (hit_rate, count_3_plus, best, pool) in enumerate(sorted(ranked, reverse=True), start=1):
        print(f"{rank:02d}. {pool:<7} 命中率={hit_rate:.2f}%（{count_3_plus}/{total_bets[pool]}注），單期最高={best:g}球")
        ranking_rows.append({"rank": rank, "pool": pool, "hit_rate": hit_rate, "hit_3_plus": count_3_plus, "total_bets": total_bets[pool], "max_hit": best, "distribution": {str(value): totals[pool][value] for value in SCORES if totals[pool][value] >= 1}})
    best = ranking_rows[0] if ranking_rows else {}
    json_dir = Path(__file__).resolve().parent / "S5_All_Recored" / "json_data"
    json_dir.mkdir(parents=True, exist_ok=True)
    with (json_dir / "s5_v3_best_combination.json").open("w", encoding="utf-8") as handle:
        payload = {"version": VERSION, "backtest_periods": count, "window_periods": window_periods, "best": best, "ranking": ranking_rows}
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"最佳組合已寫入：{json_dir / 's5_v3_best_combination.json'}")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=VERSION)
    parser.add_argument("--backtest-periods", type=int, default=BACKTEST_PERIODS)
    parser.add_argument("--window-periods", type=int, default=WINDOW_PERIODS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    validate(args.backtest_periods, args.window_periods, args.seed)
