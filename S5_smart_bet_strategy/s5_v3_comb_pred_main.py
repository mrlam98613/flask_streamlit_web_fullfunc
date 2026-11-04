"""S5 v3 下期投注預測：窗口包括最後一期，使用 M4 下期日期。"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import cast

try:
    from .s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from .s5_v2_config import DATA_DIR, DATA_PATH, GROUPS, RANDOM_SEED, WINDOW_PERIODS
    from .s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap
    from .s5_v3_dynamic_comb_validation import validate
except ImportError:
    from s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from s5_v2_config import DATA_DIR, DATA_PATH, GROUPS, RANDOM_SEED, WINDOW_PERIODS
    from s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap
    from s5_v3_dynamic_comb_validation import validate

PROJECT_ROOT = Path(__file__).resolve().parents[1]
M4_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M4_lotto_prize_summary.csv"
ALL_POOLS = ("A+B", "A+C", "A+D", "B+C", "B+D", "C+D", "A+B+C", "A+B+D", "A+C+D", "B+C+D", "A+B+C+D")
PRED_BET_DIR = Path(__file__).resolve().parent / "next_draw_pred_data"


def next_draw_date() -> str:
    """讀取 M4 最新一列的下期開獎日期。"""
    with M4_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1].get("next_draw_date", "") if rows else ""


def load_best_pool() -> str:
    """讀取 S5 v3 回測產生的最佳組合。"""
    path = PRED_BET_DIR / "s5_v3_best_combination.json"
    if not path.exists():
        return ALL_POOLS[0]
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return str(data.get("best", {}).get("pool", ALL_POOLS[0]))


def refresh_prediction_directory(backtest_periods: int, window_periods: int, seed: int) -> str:
    """先重跑 v3 驗證，清除舊檔，再保留最新最佳組合 JSON。"""
    payload = validate(backtest_periods, window_periods, seed)
    PRED_BET_DIR.mkdir(parents=True, exist_ok=True)
    for path in PRED_BET_DIR.iterdir():
        if path.is_file():
            path.unlink()
    json_path = PRED_BET_DIR / "s5_v3_best_combination.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    best = cast(dict[str, object], payload.get("best", {}))
    return str(best.get("pool", ALL_POOLS[0]))


def predict(pool_names: tuple[str, ...], seed: int = RANDOM_SEED) -> None:
    """用包括最後一期的窗口產生下期動態投注。"""
    draws = read_draws(DATA_PATH)
    window = draws[-WINDOW_PERIODS:]
    analysis = analyze_window(window)
    candidates = cast(dict[str, list[int]], candidate_groups(analysis))
    main = str(analysis["main"])
    prediction_date = next_draw_date()
    previous = draws[-1]["numbers"] if draws else []
    last_draw = draws[-1] if draws else {"date": "", "numbers": []}
    last_numbers = cast(list[int], last_draw["numbers"])
    normal_text = ",".join(map(str, last_numbers[:6]))
    special_text = f" +{last_numbers[6]}" if len(last_numbers) >= 7 else ""
    print("=== S5_v3 ABCD 走趨 + 動態投注組合預測 ===")
    print(f"下期預測投注日期：{prediction_date}")
    print(f"窗口期 = {WINDOW_PERIODS}")
    print(f"包括最後一期{last_draw['date']}：[{normal_text}{special_text}]")
    print()
    print(f"主力組：{main}｜配腳組：{','.join(cast(list[str], analysis['supports']))}")
    print()
    print("---")
    print()
    print("候選球池：")
    for group in "ABCD":
        print(f"/> {group}[{','.join(map(str, candidates[group]))}]")
    print()
    print("---")
    print()
    PRED_BET_DIR.mkdir(parents=True, exist_ok=True)
    for index, pool in enumerate(pool_names):
        pool_groups = pool.split("+")
        selected_main = main if main in pool_groups else pool_groups[0]
        bets, meta = generate_dynamic_bets(candidates, pool, selected_main, seed + index)
        bets = limit_previous_overlap(bets, candidates, previous, seed + 1000 + index)
        path = PRED_BET_DIR / f"s5_v3_pred_{pool.replace('+', '_')}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["bet_date", "N1_N6"])
            for ticket in bets:
                writer.writerow([prediction_date, "[" + ",".join(map(str, ticket)) + "]"])
        print(f"{pool}: {meta['pool_size']}球 / {len(bets)}注 -> {path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", default="best", choices=("best", "all", *ALL_POOLS))
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--backtest-periods", type=int, default=50)
    parser.add_argument("--window-periods", type=int, default=WINDOW_PERIODS)
    args = parser.parse_args()
    refreshed_best = refresh_prediction_directory(args.backtest_periods, args.window_periods, args.seed)
    selected = ALL_POOLS if args.pool == "all" else (refreshed_best if args.pool == "best" else args.pool,)
    predict(selected, args.seed)
