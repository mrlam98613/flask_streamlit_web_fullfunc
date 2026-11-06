"""S5 v2 回測主程式：動態候選池 + ABCD 預測 + 三組輸出。"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import cast

'''
03. 核對日 2026-11-05｜主力 A｜配腳 C,B,D
ABCD 分組球數走勢：
A組：-142211111-33242121 = 32 球次 / 29.925 = 106.9%
B組：-2113-1--23121-3113 = 25 球次 / 36.575 = 68.4%
C組：31212-233212-33-331 = 35 球次 / 36.575 = 95.7%
D組：32---2-1213111-1--1 = 19 球次 / 29.925 = 63.5%
候選球池：
/> A[5,8,9,2,4,3,7,6]，
/> B[19,11,18,20,10,12,14,17,13,16]，
/> C[31,29,21,24,28,23,26,27,30,22,25]，
/> D[34,40,33,35,36,37,38,32]
A+B: 18球 / 3注 = 命中：沒有 3 球或以上
A+B+C: 29球 / 5注 = 命中：沒有 3 球或以上
A+B+C+D: 37球 / 7注 = 命中：沒有 3 球或以上
'''


try:
    from .s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from .s5_v2_config import BACKTEST_PERIODS, DATA_DIR, DATA_PATH, GROUPS, OUTPUT_POOLS, RANDOM_SEED, VERSION, WINDOW_PERIODS
    from .s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap
except ImportError:  # 允許直接 python3 檔案.py 執行
    from s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from s5_v2_config import BACKTEST_PERIODS, DATA_DIR, DATA_PATH, GROUPS, OUTPUT_POOLS, RANDOM_SEED, VERSION, WINDOW_PERIODS
    from s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap


def score(ticket, draw_numbers):
    """計算單注命中分數；正號每球 1 分，特別號最多加 0.5 分。"""
    main = len(set(ticket) & set(draw_numbers[:6]))
    return main + (0.5 if main < 6 and len(draw_numbers) > 6 and draw_numbers[6] in ticket else 0)


def write_csv(path: Path, rows):
    """將逐注回測結果以 UTF-8-SIG CSV 格式寫入指定路徑。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["bet_date", "N1_N6", "hit-num"])
        writer.writerows(rows)


def run(backtest_periods=BACKTEST_PERIODS, window_periods=WINDOW_PERIODS, seed=RANDOM_SEED):
    """執行 S5 v2 回測：每期重新預測 ABCD 並驗證指定三組組合。"""
    draws = read_draws(DATA_PATH)
    count = min(backtest_periods, max(0, len(draws) - window_periods))
    start = len(draws) - count
    csv_rows = {pool: [] for pool in OUTPUT_POOLS}
    print(f'=== "{VERSION}" ===')
    print(f"回測期= {count}  窗口期={window_periods}，輸出組合={OUTPUT_POOLS}")
    for offset, target_index in enumerate(range(start, len(draws))):
        window = draws[target_index - window_periods:target_index]
        target = draws[target_index]
        analysis = analyze_window(window)
        groups = cast(dict[str, list[int]], candidate_groups(analysis))
        main = str(analysis["main"])
        supports = cast(list[str], analysis["supports"])
        trends = cast(dict[str, list[int]], analysis["trends"])
        print(f"\n{offset + 1:02d}. 核對日 {target['date']}｜主力 {main}｜配腳 {','.join(supports)}")
        totals = cast(dict[str, int], analysis["totals"])
        strength = cast(dict[str, float], analysis["strength"])
        print("ABCD 分組球數走勢：")
        for group in "ABCD":
            expected = window_periods * 7 * len(GROUPS[group]) / 40
            trend = "".join(str(value) if value else "-" for value in trends[group])
            print(f"{group}組：{trend} = {totals[group]} 球次 / {expected:g} = {strength[group] * 100:.1f}%")
        print("候選球池：")
        print("，\n".join(f"/> {g}[{','.join(map(str, groups[g]))}]" for g in "ABCD"))
        for pool_index, pool in enumerate(OUTPUT_POOLS):
            pool_groups = pool.split("+")
            pool_main = main if main in pool_groups else pool_groups[0]
            bets, meta = generate_dynamic_bets(groups, pool, pool_main, seed + offset * 100 + pool_index)
            previous_numbers = draws[target_index - 1]["numbers"] if target_index > 0 else []
            bets = limit_previous_overlap(bets, groups, previous_numbers, seed + offset * 1000 + pool_index)
            distribution = {}
            for ticket in bets:
                hit = score(ticket, target["numbers"])
                if hit >= 3:
                    distribution[hit] = distribution.get(hit, 0) + 1
                csv_rows[pool].append([target["date"], "[" + ",".join(map(str, ticket)) + "]", f"{hit:g}"])
            hit_text = "，".join(f"{hit:g}球 [{count}注]" for hit, count in sorted(distribution.items()))
            print(f"{pool}: {meta['pool_size']}球 / {len(bets)}注 = 命中：{hit_text or '沒有 3 球或以上'}")
    names = {"A+B": "s5_v2_2_group_bet.csv", "A+B+C": "s5_v2_3_group_bet.csv", "A+B+C+D": "s5_v2_4_group_bet.csv"}
    for pool, rows in csv_rows.items():
        write_csv(DATA_DIR / names[pool], rows)
        print(f"已重建 {names[pool]}：{len(rows)} 注")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backtest-periods", type=int, default=BACKTEST_PERIODS)
    parser.add_argument("--window-periods", type=int, default=WINDOW_PERIODS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    run(args.backtest_periods, args.window_periods, args.seed)
