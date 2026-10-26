"""S4 v2 分組球數模型示範主程式。

本程式獨立引用 v1 的資料讀取及窗口顯示函式，但不修改 v1 程式。
模型參數及預測邏輯分別位於 s4_v2_group_count_config.py 與
s4_v2_group_count_strategy.py。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(CURRENT_DIR))

import s4_v1_backtest_main_key_app as v1
from s4_v2_group_count_config import MODEL_CONFIG
from s4_v2_group_count_strategy import (
    build_main_architecture_prediction,
    predict_group_ranges,
)


def build_group_sequences(
    window_rows: list[tuple[int, v1.DrawRow]],
) -> dict[str, list[int]]:
    return {
        v1.GROUP_CODES[group_id]: [
            v1.group_ball_count(row, group_id) for _row_index, row in window_rows
        ]
        for group_id in v1.selected_group_ids()
    }


def build_main_group_sequence(
    window_rows: list[tuple[int, v1.DrawRow]],
) -> list[str]:
    """依每期球數選出一個主力組別，平手時依 ABCD 原順序。"""
    sequence: list[str] = []
    group_ids = v1.selected_group_ids()
    for _row_index, row in window_rows:
        main_group = max(
            group_ids,
            key=lambda group_id: (
                v1.group_ball_count(row, group_id),
                -group_ids.index(group_id),
            ),
        )
        sequence.append(v1.GROUP_CODES[main_group])
    return sequence


def build_main_group_prize_records(
    window_rows: list[tuple[int, v1.DrawRow]],
) -> list[tuple[str, float]]:
    """建立每期主力組別及該期 3 獎中獎注數資料。"""
    records: list[tuple[str, float]] = []
    group_ids = v1.selected_group_ids()
    for _row_index, row in window_rows:
        main_group = max(
            group_ids,
            key=lambda group_id: (
                v1.group_ball_count(row, group_id),
                -group_ids.index(group_id),
            ),
        )
        records.append((v1.GROUP_CODES[main_group], float(row["prize_count"])))
    return records


def print_model_prediction(
    group_sequences: dict[str, list[int]],
    main_group_sequence: list[str],
    main_group_prize_records: list[tuple[str, float]],
) -> None:
    group_sizes = {
        v1.GROUP_CODES[group_id]: v1.GROUPS[group_id][2] - v1.GROUPS[group_id][1] + 1
        for group_id in v1.selected_group_ids()
    }
    prediction = predict_group_ranges(group_sequences, group_sizes, MODEL_CONFIG)

    print()
    print("----- S4 v2 分組球數模型預測 -----")
    main_prediction = build_main_architecture_prediction(
        main_group_sequence,
        prediction,
        main_group_prize_records,
        MODEL_CONFIG,
    )
    ranking = cast(list[str], main_prediction["ranking"])
    print(
        f"主力組別架構排序：{', '.join(ranking)}"
    )
    print(
        f"主力球組最高配額：{main_prediction['allocation']} = "
        f"{main_prediction['total']} 球"
    )


def main() -> None:
    draws = v1.read_draws()
    if not draws:
        raise FileNotFoundError(f"找不到或未能讀取 M6：{v1.M6_CSV}")

    window_count = max(v1.WINDOW_DRAW_COUNT_LIST)
    latest_index = len(draws) - 1
    window_start_index = max(0, latest_index - window_count + 1)
    window_rows = [
        (row_index, row)
        for row_index, row in enumerate(
            draws[window_start_index:latest_index + 1],
            start=window_start_index,
        )
    ]

    print(f"====== S4 v2 分組球數策略模型，窗口期 = {len(window_rows)} ======")
    print("模型資料：使用目前窗口期完整資料")
    v1.print_group_priority_table(window_rows, latest_index)
    v1.print_matched_window_count(window_rows)
    group_sequences = build_group_sequences(window_rows)
    print_model_prediction(
        group_sequences,
        build_main_group_sequence(window_rows),
        build_main_group_prize_records(window_rows),
    )


if __name__ == "__main__":
    main()

