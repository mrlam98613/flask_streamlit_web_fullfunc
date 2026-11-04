"""S4 v2 獨立分組球數學習、回測及預測主程式。"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Optional, TypedDict, cast

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
from s4_v2_group_count_config import (
    COMBINATION_TAKE_COUNT,
    COMB_MATCH_MODE,
    GROUP_RANGES,
    GROUP_STRENGTH_POWERS,
    LEARNED_PARAMS_JSON_NAME,
    LEARNING_HISTORY_COUNT,
    LEARNING_LOG_CSV_NAME,
    LEARNING_VALIDATION_COUNT,
    MAIN_CANDIDATE_GROUPS,
    MODEL_CONFIG,
    PAYOUT_WEIGHT_POWERS,
    PRIZE3_WEIGHT_POWERS,
    RECENCY_DECAYS,
    SELECT_GROUPS,
    WINDOW_SIZE,
)
from s4_v2_group_count_strategy import (
    predict_main_and_legs,
)

M6_CSV = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M6_lotto_history_prize.csv"
M3_CSV = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M3_lotto_prize_results.csv"
PREDICT_DIR = CURRENT_DIR / "s4_v2_predict_prize3"
PREDICT_CSV = PREDICT_DIR / "s4_v2_pred_main_banker_leg.csv"
GROUPS = {group_id: (code, start, end) for group_id, code, start, end in GROUP_RANGES}
GROUP_CODES = {group_id: code for group_id, code, _start, _end in GROUP_RANGES}


class DrawRow(TypedDict):
    date: str
    nums: list[int]
    special: Optional[int]
    prize_count: float


def to_float(value: object, default: float = 0.0) -> float:
    if not isinstance(value, (int, float, str)) or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {key.strip(): (value or "").strip() for key, value in row.items() if key}
            for row in csv.DictReader(handle)
        ]


def read_draws() -> list[DrawRow]:
    draws: list[DrawRow] = []
    for row in read_csv_rows(M6_CSV):
        date = row.get("nDdate", "")
        if not date:
            continue
        special_value = int(to_float(row.get("N7")))
        draws.append({
            "date": date,
            "nums": [int(to_float(row.get(f"N{index}"))) for index in range(1, 7)],
            "special": special_value if 1 <= special_value <= 49 else None,
            "prize_count": to_float(row.get("prize3")),
        })
    return draws


def selected_group_ids() -> list[int]:
    return list(SELECT_GROUPS)


def group_ball_count(row: DrawRow, group_id: int) -> int:
    _code, start, end = GROUPS[group_id]
    count = sum(start <= number <= end for number in row["nums"])
    special = row["special"]
    return count + int(special is not None and start <= special <= end)


def row_selected_ball_count(row: DrawRow) -> int:
    return sum(group_ball_count(row, group_id) for group_id in selected_group_ids())


def print_matched_window_count(window_rows: list[tuple[int, DrawRow]]) -> None:
    matched = sum(
        1 for _index, row in window_rows
        if (COMB_MATCH_MODE == ">=" and sum(
            sum(GROUPS[gid][1] <= n <= GROUPS[gid][2] for n in row["nums"])
            for gid in selected_group_ids()
        ) >= COMBINATION_TAKE_COUNT)
    )
    total = len(window_rows)
    percent = round(matched / total * 100) if total else 0
    print("---- 查詢條件 統計")
    print(
        f"窗口條件 {COMB_MATCH_MODE} {COMBINATION_TAKE_COUNT} 球，"
        f"查詢 {matched} / {total} 期統計 = {matched}期 ({percent} %)"
    )


def write_csv_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_total_payout_by_date() -> dict[str, float]:
    """以 M6 三獎中獎注數乘三獎每注派彩，計算三獎總派彩。"""
    totals: dict[str, float] = {}
    for row in read_csv_rows(M6_CSV):
        date = row.get("nDdate", "")
        if not date:
            continue
        totals[date] = (
            to_float(row.get("prize3"))
            * to_float(row.get("prize3_unit"))
        )
    return totals


def print_group_priority_table_with_payout(
    window_rows: list[tuple[int, DrawRow]],
    target_index: int,
    payouts: dict[str, float],
) -> list[tuple[str, str, float, float, int]]:
    """打印主力／副組走勢及 1、2、3 獎總派彩，回傳每期分析記錄。"""
    records: list[tuple[str, str, float, float, int]] = []
    print()
    print("----- ABCD 主力組 / 副組分組走勢 -----")
    print("ID   | 日期       | 3獎中獎注 | 3獎派彩總額 | 球數 | 主力 | 副組")
    group_ids = selected_group_ids()
    for row_index, row in window_rows:
        counts = {group_id: group_ball_count(row, group_id) for group_id in group_ids}
        main_candidates = [gid for gid in group_ids if GROUP_CODES[gid] in MAIN_CANDIDATE_GROUPS]
        ranked_main = sorted(
            main_candidates,
            key=lambda gid: (-counts[gid], main_candidates.index(gid)),
        )
        if not ranked_main:
            continue
        main_id = ranked_main[0]
        main_code = GROUP_CODES[main_id]
        main_display = f"{main_code}{counts[main_id]}"
        sub_groups = sorted(
            (gid for gid in group_ids if gid != main_id),
            key=lambda gid: (-counts[gid], group_ids.index(gid)),
        )
        sub_text = ", ".join(
            f"{GROUP_CODES[gid]}{counts[gid]}"
            for gid in sub_groups if counts[gid] > 0
        )
        payout = payouts.get(row["date"], 0.0)
        draw_count = row_selected_ball_count(row)
        rank_id = target_index - row_index + 1
        print(
            f"{rank_id:>2}期 | {row['date']} | {int(row['prize_count']):>6} | "
            f"{payout:>11,.0f} | {draw_count:>4} | {main_display:<10} | {sub_text}"
        )
        records.append((main_code, sub_text, float(row["prize_count"]), payout, draw_count))
    return records


def print_group_ball_trend(window_rows: list[tuple[int, DrawRow]]) -> None:
    """顯示預測窗口內 ABCD 球數走勢及相對於均勻分布的比例。"""
    window_total = len(window_rows)
    denominator = window_total * 7
    print()
    print("----- ABCD 分組球數走勢  查詢期數 x 7球  = 球次數 -----")
    for group_id in selected_group_ids():
        code, start, end = GROUPS[group_id]
        counts = [group_ball_count(row, group_id) for _index, row in window_rows]
        total = sum(counts)
        expected = denominator * (end - start + 1) / 40
        percent = total / expected * 100 if expected else 0.0
        sequence = "".join(str(count) if count else "-" for count in counts)
        print(
            f"{code}組 球數走趨：{sequence} = {total} 球次 / "
            f"{expected:g} = {percent:.1f}%"
        )


def print_high_prize3_summary(records: list[tuple[str, str, float, float, int]]) -> None:
    """摘要列出 3 獎注數達 200 且 ABCD 合計至少 5 球的有效期。"""
    high_rows = [
        record for record in records
        if record[2] >= 200 and record[4] >= 5
    ]
    print()
    print("----- 3獎中獎注數 >= 200 注期數特點 -----")
    if not high_rows:
        print("窗口內沒有 3 獎中獎注數 >= 200 注的期數。")
        return
    main_counts: dict[str, int] = {}
    leg_counts: dict[str, int] = {}
    for main, legs, _prize_count, _payout, _draw_count in high_rows:
        main_counts[main] = main_counts.get(main, 0) + 1
        for part in legs.split(", "):
            if part:
                group = part[0]
                leg_counts[group] = leg_counts.get(group, 0) + 1
    main_text = ", ".join(
        f"{group} {count}期" for group, count in
        sorted(main_counts.items(), key=lambda item: (-item[1], item[0]))
    )
    leg_text = ", ".join(
        f"{group} {count}次" for group, count in
        sorted(leg_counts.items(), key=lambda item: (-item[1], item[0]))
    ) or "無配腳組"
    print(f"高注數期：{len(high_rows)} 期；主力組分布：{main_text}")
    print(f"配腳組出現：{leg_text}")


def build_group_sequences(
    window_rows: list[tuple[int, DrawRow]],
) -> dict[str, list[int]]:
    return {
        GROUP_CODES[group_id]: [
            group_ball_count(row, group_id) for _row_index, row in window_rows
        ]
        for group_id in selected_group_ids()
    }


def build_main_group_sequence(
    window_rows: list[tuple[int, DrawRow]],
) -> list[str]:
    """依每期球數選出一個主力組別，平手時依 ABCD 原順序。"""
    sequence: list[str] = []
    group_ids = selected_group_ids()
    for _row_index, row in window_rows:
        main_group = max(
            group_ids,
            key=lambda group_id: (
                group_ball_count(row, group_id),
                -group_ids.index(group_id),
            ),
        )
        sequence.append(GROUP_CODES[main_group])
    return sequence


def build_main_group_prize_records(
    window_rows: list[tuple[int, DrawRow]],
    payouts: dict[str, float],
    prize_power: float = 1.0,
    payout_power: float = 0.0,
    group_strength_power: float = 0.0,
    recency_decay: float = 0.95,
) -> tuple[
    list[tuple[str, float]],
    dict[str, dict[str, float]],
    dict[str, dict[str, int]],
]:
    """以合計至少 5 球的期數建立注數加權主副組資料；同分按 ABCD 排序。"""
    records: list[tuple[str, float]] = []
    leg_scores: dict[str, dict[str, float]] = {
        GROUP_CODES[group_id]: {} for group_id in selected_group_ids()
    }
    group_ids = selected_group_ids()
    group_strength: dict[str, float] = {}
    total_rows = len(window_rows)
    for group_id in group_ids:
        code, start, end = GROUPS[group_id]
        actual = sum(group_ball_count(row, group_id) for _idx, row in window_rows)
        expected = total_rows * 7 * (end - start + 1) / 40
        group_strength[code] = actual / expected if expected else 0.0
    observed_leg_max_by_main: dict[str, dict[str, int]] = {
        main: {GROUP_CODES[group_id]: 0 for group_id in group_ids if GROUP_CODES[group_id] != main}
        for main in MAIN_CANDIDATE_GROUPS
    }
    for position, (_row_index, row) in enumerate(window_rows):
        counts = {group_id: group_ball_count(row, group_id) for group_id in group_ids}
        total = sum(counts.values())
        main_candidates = [
            group_id for group_id in group_ids
            if GROUP_CODES[group_id] in MAIN_CANDIDATE_GROUPS
        ]
        ranked = sorted(
            main_candidates,
            key=lambda group_id: (-counts[group_id], main_candidates.index(group_id)),
        )
        # 總球數至少 5 球；最高球數相同時依 ABCD 順序決定主力。
        if total < 5:
            continue
        main_code = GROUP_CODES[ranked[0]]
        main_count = counts[ranked[0]]
        age = len(window_rows) - position - 1
        prize_weight = max(1.0, float(row["prize_count"])) ** prize_power
        payout_signal = max(1.0, payouts.get(row["date"], 0.0) / 1_000_000)
        prize_weight *= payout_signal ** payout_power
        prize_weight *= max(0.0, group_strength[main_code]) ** group_strength_power
        prize_weight *= recency_decay ** age
        records.append((main_code, prize_weight))
        leg_groups = sorted(
            (group_id for group_id in group_ids if group_id != ranked[0]),
            key=lambda group_id: (-counts[group_id], group_ids.index(group_id)),
        )
        for group_id in leg_groups:
            if counts[group_id] <= 0:
                continue
            leg_code = GROUP_CODES[group_id]
            previous = leg_scores[main_code].get(leg_code, 0.0)
            leg_scores[main_code][leg_code] = previous + prize_weight * counts[group_id]
            # 只有球數低於主力的組別，才作為配腳配額上限的歷史依據。
            if counts[group_id] < main_count:
                observed_leg_max_by_main[main_code][leg_code] = max(
                    observed_leg_max_by_main[main_code].get(leg_code, 0),
                    counts[group_id],
                )
    return records, leg_scores, observed_leg_max_by_main


def print_model_prediction(
    main_group_prize_records: list[tuple[str, float]],
    leg_scores: dict[str, dict[str, float]],
    observed_leg_max_by_main: dict[str, dict[str, int]],
) -> dict[str, object]:
    prediction = predict_main_and_legs(
        main_group_prize_records, leg_scores, observed_leg_max_by_main, MODEL_CONFIG
    )
    print()
    print("----- S4 v2 分組球數模型預測 -----")
    support_text = ", ".join(
        f"{group}[{quota}]"
        for group, quota in cast(dict[str, int], prediction["support_quotas"]).items()
    )
    print(f"預測主力組：{prediction['main_group']}[{prediction['main_quota']}]")
    print(
        f"主力組 + 配腳組：{prediction['main_group']}[{prediction['main_quota']}] + "
        f"{support_text} = {prediction['total']} 球"
    )
    return prediction


def save_prediction_csv(
    pred_date: str,
    prediction: dict[str, object],
    snowball: str,
) -> None:
    """依預測日期新增或更新主力及配腳組 CSV 紀錄。"""
    PREDICT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "pred_date", "main_key", "leg_key1", "leg_key2", "leg_key3",
        "snowball",
    ]
    legs = cast(dict[str, int], prediction["support_quotas"])
    main_group = str(prediction["main_group"])
    main_quota = cast(int, prediction["main_quota"])
    row = {
        "pred_date": pred_date,
        "main_key": f"{main_group}[{main_quota}]",
        "leg_key1": "",
        "leg_key2": "",
        "leg_key3": "",
        "snowball": snowball,
    }
    for index, (group, quota) in enumerate(legs.items(), start=1):
        if index <= 3:
            row[f"leg_key{index}"] = f"{group}[{quota}]"

    existing: list[dict[str, str]] = []
    if PREDICT_CSV.exists():
        with PREDICT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
            existing = list(csv.DictReader(handle))
    rows = [
        {field: old.get(field, "") for field in fieldnames}
        for old in existing
        if old.get("pred_date") != pred_date
    ]
    rows.append(row)
    with PREDICT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_prediction(
    window_rows: list[tuple[int, DrawRow]],
    payouts: dict[str, float],
    prize_power: float,
    payout_power: float,
    group_strength_power: float,
    recency_decay: float,
) -> dict[str, object]:
    evidence, leg_scores, observed_leg_max_by_main = build_main_group_prize_records(
        window_rows, payouts, prize_power, payout_power, group_strength_power, recency_decay
    )
    prediction = predict_main_and_legs(
        evidence, leg_scores, observed_leg_max_by_main, MODEL_CONFIG
    )
    return {
        "evidence": evidence,
        "leg_scores": leg_scores,
        "observed_leg_max_by_main": observed_leg_max_by_main,
        "prediction": prediction,
    }


def score_prediction(
    prediction: dict[str, object],
    draw: DrawRow,
    payouts: dict[str, float],
) -> tuple[float, float, str, int]:
    """評分預測組別覆蓋率與明確主力命中；回傳分數、權重、實際主力、覆蓋球數。"""
    group_ids = selected_group_ids()
    counts = {GROUP_CODES[gid]: group_ball_count(draw, gid) for gid in group_ids}
    total_count = sum(counts.values())
    main_candidates = [group for group in counts if group in MAIN_CANDIDATE_GROUPS]
    ranked = sorted(
        main_candidates,
        key=lambda group: (-counts[group], main_candidates.index(group)),
    )
    actual_main = ""
    if total_count >= 5 and ranked:
        actual_main = ranked[0]

    model_result = cast(dict[str, object], prediction["prediction"])
    selected_groups = [
        str(model_result["main_group"]),
        *cast(dict[str, int], model_result["support_quotas"]).keys(),
    ]
    covered = sum(counts.get(group, 0) for group in selected_groups)
    coverage = covered / total_count if total_count else 0.0
    main_hit = 1.0 if actual_main and actual_main == model_result["main_group"] else 0.0
    score = 0.7 * coverage + 0.3 * main_hit
    payout = max(0.0, payouts.get(draw["date"], 0.0))
    sample_weight = (
        math.log1p(max(0.0, float(draw["prize_count"])))
        * math.log1p(payout / 1_000_000)
    )
    return score, sample_weight, actual_main, covered


def run_walk_forward_learning(
    draws: list[DrawRow],
    payouts: dict[str, float],
) -> tuple[float, float, float, float, list[dict[str, object]], dict[str, object]]:
    """以前 80% 逐期選參數，最近 20% 作時間順序驗證。"""
    window_size = WINDOW_SIZE
    first_index = max(window_size, len(draws) - LEARNING_HISTORY_COUNT)
    check_indices = list(range(first_index, len(draws)))
    if len(check_indices) < 10:
        raise ValueError("可用歷史期數不足，至少需要 10 個窗口外核對期")
    validation_count = min(LEARNING_VALIDATION_COUNT, max(1, len(check_indices) // 4))
    split = max(1, len(check_indices) - validation_count)
    train_indices = check_indices[:split]
    validation_indices = check_indices[split:]

    def window_for(check_index: int) -> list[tuple[int, DrawRow]]:
        start = max(0, check_index - window_size)
        return list(enumerate(draws[start:check_index], start=start))

    candidates: list[tuple[float, float, float, float, float]] = []
    for prize_power in PRIZE3_WEIGHT_POWERS:
        for payout_power in PAYOUT_WEIGHT_POWERS:
            for group_strength_power in GROUP_STRENGTH_POWERS:
                for recency_decay in RECENCY_DECAYS:
                    weighted_score = 0.0
                    total_weight = 0.0
                    for check_index in train_indices:
                        predicted = make_prediction(
                            window_for(check_index), payouts,
                            prize_power, payout_power, group_strength_power, recency_decay,
                        )
                        score, weight, _actual_main, _covered = score_prediction(
                            predicted, draws[check_index], payouts
                        )
                        weighted_score += score * weight
                        total_weight += weight
                    average = weighted_score / total_weight if total_weight else 0.0
                    candidates.append((average, prize_power, payout_power, group_strength_power, recency_decay))
    train_score, best_prize_power, best_payout_power, best_group_strength_power, best_recency_decay = max(
        candidates, key=lambda item: (item[0], -item[1], -item[2], -item[3], item[4])
    )

    validation_rows: list[dict[str, object]] = []
    all_log_rows: list[dict[str, object]] = []
    validation_weighted = 0.0
    validation_total_weight = 0.0
    for check_index in check_indices:
        window_rows = window_for(check_index)
        predicted = make_prediction(
            window_rows, payouts, best_prize_power, best_payout_power,
            best_group_strength_power, best_recency_decay
        )
        score, weight, actual_main, covered = score_prediction(
            predicted, draws[check_index], payouts
        )
        phase = "validation" if check_index in validation_indices else "training"
        if phase == "validation":
            validation_weighted += score * weight
            validation_total_weight += weight
        model_result = cast(dict[str, object], predicted["prediction"])
        legs = cast(dict[str, int], model_result["support_quotas"])
        check_draw = draws[check_index]
        log_row = {
            "date": check_draw["date"],
            "phase": phase,
            "prize_power": best_prize_power,
            "payout_power": best_payout_power,
            "group_strength_power": best_group_strength_power,
            "recency_decay": best_recency_decay,
            "predicted_main": model_result["main_group"],
            "predicted_legs": ",".join(legs),
            "predicted_quota": f"{model_result['main_group']}[{model_result['main_quota']}]+"
                + ",".join(f"{group}[{quota}]" for group, quota in legs.items()),
            "predicted_total": model_result["total"],
            "quota_minimum": MODEL_CONFIG.combination_min_total,
            "quota_ranges": ",".join(
                f"{group}[{low}-{high}]"
                for group, low, high in MODEL_CONFIG.group_quota_ranges
            ),
            "actual_main": actual_main,
            "actual_group_counts": ",".join(
                f"{GROUP_CODES[gid]}[{group_ball_count(check_draw, gid)}]"
                for gid in selected_group_ids()
            ),
            "covered_draw_balls": covered,
            "prize3_count": check_draw["prize_count"],
            "prize3_payout": payouts.get(check_draw["date"], 0.0),
            "score": round(score, 5),
        }
        all_log_rows.append(log_row)
        if phase == "validation":
            validation_rows.append(log_row)
    validation_score = (
        validation_weighted / validation_total_weight if validation_total_weight else 0.0
    )

    learned = {
        "prize3_weight_power": best_prize_power,
        "prize3_payout_weight_power": best_payout_power,
        "group_strength_weight_power": best_group_strength_power,
        "recency_decay": best_recency_decay,
        "train_weighted_score": round(train_score, 5),
        "validation_weighted_score": round(validation_score, 5),
        "training_draw_count": len(train_indices),
        "validation_draw_count": len(validation_indices),
        "window_size": window_size,
    }
    write_csv_rows(CURRENT_DIR / LEARNING_LOG_CSV_NAME, all_log_rows)
    (CURRENT_DIR / LEARNED_PARAMS_JSON_NAME).write_text(
        json.dumps(learned, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return (
        best_prize_power, best_payout_power, best_group_strength_power,
        best_recency_decay, validation_rows, learned,
    )


def read_next_jackpot_context() -> tuple[str, float]:
    """從 M3 最新結果檔讀取下期日期及多寶彩金。"""
    m3_path = M3_CSV
    next_date = ""
    jackpot = 0.0
    in_next_section = False
    with m3_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if not row:
                continue
            key = row[0].strip()
            if "下一期" in key:
                in_next_section = True
                continue
            if not in_next_section or len(row) < 2:
                continue
            if key == "開獎日期":
                date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", row[1])
                if date_match:
                    next_date = "-".join(
                        (date_match.group(1), date_match.group(2).zfill(2), date_match.group(3).zfill(2))
                    )
            elif "多寶" in key:
                jackpot = to_float(row[1].replace(",", ""))
    return next_date, jackpot


def main() -> None:
    draws = read_draws()
    if not draws:
        raise FileNotFoundError(f"找不到或未能讀取 M6：{M6_CSV}")

    window_count = WINDOW_SIZE
    payout_by_date = build_total_payout_by_date()
    (
        prize_power, payout_power, group_strength_power, recency_decay,
        validation_rows, learned,
    ) = (
        run_walk_forward_learning(draws, payout_by_date)
    )
    print("----- S4 v2 自我學習回測 -----")
    print(
        f"逐期樣本：訓練 {learned['training_draw_count']} 期，"
        f"時間順序驗證 {learned['validation_draw_count']} 期；"
        f"窗口期 {window_count} 期"
    )
    print(
        f"訓練加權分數：{learned['train_weighted_score']}；"
        f"驗證加權分數：{learned['validation_weighted_score']}"
    )
    print(
        f"自動選出參數：3獎注數權重={prize_power}，"
        f"3獎派彩權重={payout_power}，"
        f"分組強弱權重={group_strength_power}，"
        f"近期衰減={recency_decay}"
    )
    if validation_rows:
        last_check = validation_rows[-1]
        print(
            f"最近驗證核對 {last_check['date']}：預測主力 {last_check['predicted_main']}，"
            f"實際明確主力 {last_check['actual_main'] or '無'}；"
            f"實際組別球數 {last_check['actual_group_counts']}，"
            f"ABCD 組開出 {last_check['covered_draw_balls']} 球"
        )

    latest_index = len(draws) - 1
    window_start_index = max(0, latest_index - window_count + 1)
    latest_window = list(enumerate(draws[window_start_index:latest_index + 1], start=window_start_index))
    print()
    print(f"====== 下期預測，使用最近 {len(latest_window)} 期 ======")
    table_records = print_group_priority_table_with_payout(
        latest_window, latest_index, payout_by_date
    )
    print_matched_window_count(latest_window)
    print_group_ball_trend(latest_window)
    print_high_prize3_summary(table_records)
    evidence, leg_scores, observed_leg_max_by_main = build_main_group_prize_records(
        latest_window, payout_by_date, prize_power, payout_power,
        group_strength_power, recency_decay
    )
    next_date, jackpot = read_next_jackpot_context()
    final_prediction = print_model_prediction(
        evidence, leg_scores, observed_leg_max_by_main
    )
    evidence_scores = cast(dict[str, float], final_prediction["evidence_scores"])
    final_prediction["main_evidence_score"] = evidence_scores.get(
        str(final_prediction["main_group"]), 0.0
    )
    final_prediction["prize3_weight_power"] = prize_power
    final_prediction["payout_weight_power"] = payout_power
    final_prediction["group_strength_weight_power"] = group_strength_power
    final_prediction["recency_decay"] = recency_decay
    snowball_text = f"多寶 / 金多寶 {jackpot:,.0f} 元"
    save_prediction_csv(next_date or "unknown", final_prediction, snowball_text)
    print(
        f"M3檔案所載彩池：{next_date or '日期未知'}，"
        f"多寶 / 金多寶 {jackpot:,.0f} 元"
    )


if __name__ == "__main__":
    main()

