"""S5 v1 回測主程式。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

try:
    from .s5_v1_bet_combination import POOL_SPECS, generate_bets, hit_summary, load_draws
except ImportError:  # 允許直接用檔案路徑執行
    from S5_smart_bet_strategy.old_apps.s5_v1_bet_combination import POOL_SPECS, generate_bets, hit_summary, load_draws

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKTEST_PERIODS = 10
WINDOW_PERIODS = 19
RANDOM_SEED = 20261104
OUTPUT_POOLS = ("A+B", "A+B+C", "A+B+C+D")
'''
前邏輯是：
- 每注固定 6 球
- 各候選組別都有配額
- 基本注內號碼不重複
- 每期重新隨機排列
- main_group 參數已預留，但目前沒有強制主力組必須取得 2–3 球
分組配額：有
主力＋配腳優先：尚未正式套用
A 主力 + B、C 配腳
A：2–3 球
B+C：剩餘 3–4 球

'''


def _score_ticket(ticket, draw_numbers):
    main_hits = len(set(ticket) & set(draw_numbers[:6]))
    if main_hits < 6 and len(draw_numbers) >= 7 and draw_numbers[6] in ticket:
        return main_hits + 0.5
    return main_hits


def _write_bet_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["bet_date", "N1_N6", "hit-num"])
        writer.writerows(rows)


def run_backtest(backtest_periods=BACKTEST_PERIODS, window_periods=WINDOW_PERIODS, seed=RANDOM_SEED):
    data_path = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M2_last_upgrade_lotto_data.csv"
    draws = load_draws(data_path)
    actual_periods = min(backtest_periods, max(0, len(draws) - window_periods))
    print(f"開獎資料：{len(draws)} 期")
    print(f"窗口期：{window_periods} 期；回測期：{actual_periods} 期；候選球池：{len(POOL_SPECS)} 組")
    tracked_scores = (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)
    selected_specs = [spec for spec in POOL_SPECS if spec.name in OUTPUT_POOLS]
    totals = {spec.name: {score: 0 for score in tracked_scores} for spec in POOL_SPECS}
    csv_rows = {spec.name: [] for spec in selected_specs}
    # 由最後一期向前取回測期；每個核對期之前的 19 期才是窗口，
    # 核對期本身不會放入自己的窗口。
    first_target_index = len(draws) - actual_periods
    for offset in range(actual_periods):
        target_index = first_target_index + offset
        target = draws[target_index]
        window_draws = draws[target_index - window_periods:target_index]
        if len(window_draws) != window_periods:
            continue
        print(f"\n[{offset + 1:02d}/{actual_periods:02d}] 驗證期：{target['date']}")
        for pool_index, spec in enumerate(POOL_SPECS):
            bets, _ = generate_bets(spec, seed=seed + offset * 100 + pool_index)
            result = hit_summary(bets, target["numbers"])
            for ticket in bets:
                score = _score_ticket(ticket, target["numbers"])
                if score in totals[spec.name]:
                    totals[spec.name][score] += 1
                if spec.name in csv_rows:
                    numbers_text = "[" + ",".join(str(number) for number in ticket) + "]"
                    csv_rows[spec.name].append([target["date"], numbers_text, f"{score:g}"])
            print(f"  {spec.name:<7} {len(spec.numbers):>2}球 / {len(bets)}注 / 最高{result['max_hit']:g}分")

    for spec in selected_specs:
        output_name = {
            "A+B": "s5_v1_2_group_bet.csv",
            "A+B+C": "s5_v1_3_group_bet.csv",
            "A+B+C+D": "s5_v1_4_group_bet.csv",
        }[spec.name]
        output_dir = Path(__file__).resolve().parent / "data"
        _write_bet_csv(output_dir / output_name, csv_rows[spec.name])
        print(f"已重建：{output_name}（{len(csv_rows[spec.name])} 注）")
    print("\n=== 總結 ===")
    for name, result in totals.items():
        positive = [
            f"{score:g}球={result[score]}注"
            for score in tracked_scores
            if result[score] >= 1
        ]
        detail = "，".join(positive) if positive else "沒有 3 球或以上命中"
        print(f"{name:<7} {detail}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S5 v1 A/B/C/D 投注組合回測")
    parser.add_argument("--backtest-periods", type=int, default=BACKTEST_PERIODS)
    parser.add_argument("--window-periods", type=int, default=WINDOW_PERIODS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    run_backtest(args.backtest_periods, args.window_periods, args.seed)
