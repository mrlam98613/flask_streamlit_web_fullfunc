"""S5 v3 下期投注預測：窗口包括最後一期，使用 M4 下期日期。"""

from __future__ import annotations

import argparse
import csv
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import cast

'''
s5_v3_comb_pred_main.py , 
S5_V3 最終執行下期預測 動態投注組合
'''


try:
    from .s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from .s5_v2_config import DATA_DIR, DATA_PATH, GROUPS, RANDOM_SEED, WINDOW_PERIODS
    from .s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap
    from .s5_v3_dynamic_comb_validation import BACKTEST_PERIODS as VALIDATION_BACKTEST_PERIODS, validate
except ImportError:
    from s5_v2_abcd_predict import analyze_window, candidate_groups, read_draws
    from s5_v2_config import DATA_DIR, DATA_PATH, GROUPS, RANDOM_SEED, WINDOW_PERIODS
    from s5_v2_dynamic_bets import generate_dynamic_bets, limit_previous_overlap
    from s5_v3_dynamic_comb_validation import BACKTEST_PERIODS as VALIDATION_BACKTEST_PERIODS, validate


VERSION = "S5_V3 最終執行下期預測 動態投注組合 "

PROJECT_ROOT = Path(__file__).resolve().parents[1]
M4_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M4_lotto_prize_summary.csv"
ALL_POOLS = ("A+B", "A+C", "A+D", "B+C", "B+D", "C+D", "A+B+C", "A+B+D", "A+C+D", "B+C+D", "A+B+C+D")
PRED_BET_DIR = Path(__file__).resolve().parent / "next_draw_pred_data"
RECORD_DIR = Path(__file__).resolve().parent / "S5_All_Recored"
JSON_DIR = RECORD_DIR / "json_data"
BET_RECORD_PATH = RECORD_DIR / "bet_recored.csv"
WIN_RESULTS_PATH = RECORD_DIR / "win_results.csv"
ABCD_POOL_RECORD_PATH = RECORD_DIR / "ABCD_pool.csv"


def score(ticket: tuple[int, ...], draw_numbers: list[int]) -> float:
    """計算投注單與真實開獎的命中分數。"""
    main_hits = len(set(ticket) & set(draw_numbers[:6]))
    if main_hits < 6 and len(draw_numbers) >= 7 and draw_numbers[6] in ticket:
        return main_hits + 0.5
    return float(main_hits)


def next_draw_date() -> str:
    """讀取 M4 最新一列的下期開獎日期。"""
    with M4_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1].get("next_draw_date", "") if rows else ""


def load_best_pool() -> str:
    """讀取 S5 v3 回測產生的最佳組合。"""
    path = JSON_DIR / "s5_v3_best_combination.json"
    if not path.exists():
        return ALL_POOLS[0]
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return str(data.get("best", {}).get("pool", ALL_POOLS[0]))


def refresh_prediction_directory(backtest_periods: int, window_periods: int, seed: int) -> str:
    """先重跑 v3 驗證，清除舊檔，再保留最新最佳組合 JSON。"""
    # 預測頁只需要驗證結果，不顯示 v3 逐期明細。
    with redirect_stdout(io.StringIO()):
        payload = validate(backtest_periods, window_periods, seed)
    PRED_BET_DIR.mkdir(parents=True, exist_ok=True)
    for path in PRED_BET_DIR.iterdir():
        if path.is_file():
            path.unlink()
    json_path = JSON_DIR / "s5_v3_best_combination.json"
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    best = cast(dict[str, object], payload.get("best", {}))
    return str(best.get("pool", ALL_POOLS[0]))


def print_validation_summary(payload: dict[str, object]) -> None:
    """只打印 v3 驗證總結，不打印逐期回測明細。"""
    period_value = payload.get("backtest_periods", "")
    period_text = str(period_value) if period_value else "-"
    print(f"=== S5 V3 - 回測期 = {period_text}，全部動態組合驗證 總結 ===")
    ranking = cast(list[dict[str, object]], payload.get("ranking", []))
    def rank_value(item: dict[str, object]) -> int:
        """安全讀取 JSON 排名欄位，避免靜態型別將 object 傳給 int。"""
        value = item.get("rank", 999)
        return int(value) if isinstance(value, (int, float, str)) else 999

    for row in sorted(ranking, key=rank_value):
        pool = str(row.get("pool", ""))
        distribution = cast(dict[str, int], row.get("distribution", {}))
        parts = [f"{float(score):g}球={count}注" for score, count in distribution.items() if float(score) >= 3]
        print(f"{pool:<7} {', '.join(parts) if parts else '>'}")
    print("----")


def predict(pool_names: tuple[str, ...], seed: int = RANDOM_SEED, print_bet_results: bool = True) -> tuple[list[str], list[dict[str, str]]]:
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
    pool_path = PRED_BET_DIR / "next_draw_pred_balls_pool.csv"
    with pool_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["bet_date", "main_group", "support_groups", "group", "candidate_balls"])
        for group in "ABCD":
            writer.writerow([
                prediction_date,
                main,
                ",".join(cast(list[str], analysis["supports"])),
                group,
                "[" + ",".join(map(str, candidates[group])) + "]",
            ])
    append_candidate_pool_record(prediction_date, main, cast(list[str], analysis["supports"]), candidates)
    result_lines = []
    record_rows: list[dict[str, str]] = []
    for index, pool in enumerate(pool_names):
        pool_groups = pool.split("+")
        selected_main = main if main in pool_groups else pool_groups[0]
        bets, meta = generate_dynamic_bets(candidates, pool, selected_main, seed + index)
        bets = limit_previous_overlap(bets, candidates, previous, seed + 1000 + index)
        pool_code = pool.replace("+", "")
        path = PRED_BET_DIR / f"s5_v3_{pool_code}_{meta['pool_size']}_{len(bets)}_.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["bet_date", "N1_N6"])
            for ticket in bets:
                writer.writerow([prediction_date, "[" + ",".join(map(str, ticket)) + "]"])
                record_rows.append({"bet_date": prediction_date, "pool": pool, "N1_N6": "[" + ",".join(map(str, ticket)) + "]"})
        result_lines.append(f"{pool}: {meta['pool_size']}球 / {len(bets)}注 -> {path.name}")
        if print_bet_results:
            print(result_lines[-1])
    return result_lines, record_rows


def append_candidate_pool_record(
    prediction_date: str,
    main_group: str,
    support_groups: list[str],
    candidates: dict[str, list[int]],
) -> None:
    """將每期 A/B/C/D 候選球池追加到長期紀錄，日期相同則不重複。"""
    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, str]] = []
    if ABCD_POOL_RECORD_PATH.exists():
        with ABCD_POOL_RECORD_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            existing = list(csv.DictReader(handle))
    if any(row.get("bet_date", "") == prediction_date for row in existing):
        return
    fieldnames = ["bet_date", "main_group", "support_groups", "group", "candidate_balls"]
    migrated = [
        {
            "bet_date": row.get("bet_date", ""),
            "main_group": row.get("main_group", ""),
            "support_groups": row.get("support_groups", ""),
            "group": row.get("group", ""),
            "candidate_balls": row.get("candidate_balls", ""),
        }
        for row in existing
    ]
    migrated.extend(
        {
            "bet_date": prediction_date,
            "main_group": main_group,
            "support_groups": ",".join(support_groups),
            "group": group,
            "candidate_balls": "[" + ",".join(map(str, candidates[group])) + "]",
        }
        for group in "ABCD"
    )
    with ABCD_POOL_RECORD_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(migrated)


def append_bet_records(rows: list[dict[str, str]]) -> None:
    """按投注日期追加預測紀錄，同一日期不重複寫入。"""
    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    if BET_RECORD_PATH.exists():
        with BET_RECORD_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            existing = list(csv.DictReader(handle))
    existing_dates = {row.get("bet_date", "") for row in existing}
    new_dates = {row["bet_date"] for row in rows}
    if existing_dates & new_dates:
        rows = []
    all_rows = existing + rows
    with BET_RECORD_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bet_date", "pool", "N1_N6"])
        writer.writeheader()
        writer.writerows(all_rows)


def rebuild_win_results() -> None:
    """重新核對所有投注紀錄，建立包含命中分數的結果 CSV。"""
    draws = {row["date"]: row["numbers"] for row in read_draws(DATA_PATH)}
    records = []
    if BET_RECORD_PATH.exists():
        with BET_RECORD_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            records = list(csv.DictReader(handle))
    output = []
    for row in records:
        numbers = [int(value) for value in row.get("N1_N6", "").replace("[", "").replace("]", "").split(",") if value.strip().isdigit()]
        draw = draws.get(row.get("bet_date", ""), [])
        output.append({**row, "draw_N1_N7": "[" + ",".join(map(str, draw)) + "]" if draw else "", "hit-num": f"{score(tuple(numbers), draw):g}" if draw else ""})
    with WIN_RESULTS_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bet_date", "pool", "N1_N6", "draw_N1_N7", "hit-num"])
        writer.writeheader()
        writer.writerows(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", default="all", choices=("best", "all", *ALL_POOLS))
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--backtest-periods", type=int, default=VALIDATION_BACKTEST_PERIODS)
    parser.add_argument("--window-periods", type=int, default=WINDOW_PERIODS)
    args = parser.parse_args()
    refreshed_best = refresh_prediction_directory(args.backtest_periods, args.window_periods, args.seed)
    with (JSON_DIR / "s5_v3_best_combination.json").open("r", encoding="utf-8") as handle:
        validation_payload = json.load(handle)
    selected = ALL_POOLS if args.pool == "all" else (refreshed_best if args.pool == "best" else args.pool,)
    # 先輸出預測內容，再附加 v3 驗證總結；驗證逐期明細已被上面的 quiet mode 隱藏。
    result_lines, record_rows = predict(selected, args.seed, print_bet_results=False)
    append_bet_records(record_rows)
    rebuild_win_results()
    print_validation_summary(validation_payload)
    for line in result_lines:
        print(line)
