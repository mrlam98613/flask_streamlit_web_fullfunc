"""S4 v2 A/B/C/D 分組球數策略模型。

模型輸入每組最近各期球數，輸出下一期的預期、最低及最高球數。
本檔案不依賴 S4 v1 主程式，可獨立測試及日後由 v2 主程式引用。
"""

from __future__ import annotations

from dataclasses import asdict
from math import ceil, floor
from typing import Mapping, Sequence

from s4_v2_group_count_config import MODEL_CONFIG, GroupCountModelConfig


def _validate_config(config: GroupCountModelConfig) -> None:
    if not config.recent_windows:
        raise ValueError("recent_windows 不可為空")
    if len(config.recent_windows) != len(config.window_weights):
        raise ValueError("recent_windows 與 window_weights 長度必須相同")
    if any(window <= 0 for window in config.recent_windows):
        raise ValueError("recent_windows 必須大於 0")
    if any(weight < 0 for weight in config.window_weights):
        raise ValueError("window_weights 不可為負數")
    if sum(config.window_weights) <= 0:
        raise ValueError("window_weights 總和必須大於 0")
    if not 0 <= config.low_quantile <= config.high_quantile <= 1:
        raise ValueError("分位數必須符合 0 <= low <= high <= 1")
    if config.quota_mode not in (1, 2):
        raise ValueError("quota_mode 只可為 1 或 2")
    if not 0 <= config.quota_min <= config.quota_max <= 7:
        raise ValueError("quota_min / quota_max 必須介於 0 至 7")


def _quantile(values: Sequence[int], probability: float) -> float:
    """使用線性插值計算簡單分位數。"""
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * probability
    lower = floor(position)
    upper = ceil(position)
    if lower == upper:
        return ordered[lower]
    ratio = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * ratio


def _weighted_recent_average(
    sequence: Sequence[int], config: GroupCountModelConfig
) -> float:
    """依 7/10/19 期窗口計算加權平均。"""
    if not sequence:
        return 0.0
    weights_total = 0.0
    weighted_sum = 0.0
    for window, weight in zip(config.recent_windows, config.window_weights):
        values = list(sequence[-window:])
        if not values:
            continue
        weighted_sum += (sum(values) / len(values)) * weight
        weights_total += weight
    return weighted_sum / weights_total if weights_total else 0.0


def predict_group_ranges(
    group_sequences: Mapping[str, Sequence[int]],
    group_sizes: Mapping[str, int],
    config: GroupCountModelConfig = MODEL_CONFIG,
) -> dict[str, dict[str, float | int]]:
    """預測各組下一期最低、最高及預期球數。

    `group_sequences` 的每組資料應由遠期到近期排列，例如：
    ``{"A": [0, 3, 1, 1, 2, 2, 4]}``。
    """
    _validate_config(config)
    result: dict[str, dict[str, float | int]] = {}
    for group, sequence in group_sequences.items():
        values = [max(0, min(7, int(value))) for value in sequence]
        if not values:
            result[group] = {
                "expected": 0.0,
                "strength": 0.0,
                "min_balls": 0,
                "max_balls": 0,
            }
            continue

        expected = _weighted_recent_average(values, config)
        group_size = group_sizes.get(group)
        baseline = (7 * group_size / 40) if group_size else expected
        total_expected = sum(values) / len(values)
        strength = total_expected / baseline if baseline else 1.0
        if config.use_group_size_baseline and config.use_recent_strength_adjustment:
            expected = baseline * strength
        elif config.use_group_size_baseline:
            expected = baseline
        elif config.use_recent_strength_adjustment:
            expected = expected * strength

        low = _quantile(values, config.low_quantile)
        high = _quantile(values, config.high_quantile)
        if config.quota_mode == 2:
            low = max(low, config.quota_min)
            high = min(max(high, low), config.quota_max)

        result[group] = {
            "expected": round(expected, 3),
            "strength": round(strength, 3),
            "min_balls": max(0, min(7, int(round(low)))),
            "max_balls": max(0, min(7, int(round(high)))),
        }
    return result


def model_config_as_dict(
    config: GroupCountModelConfig = MODEL_CONFIG,
) -> dict[str, object]:
    """提供目前模型參數，方便主程式打印或寫入報告。"""
    return asdict(config)


def build_combination_allocations(
    prediction: Mapping[str, Mapping[str, float | int]],
    config: GroupCountModelConfig = MODEL_CONFIG,
) -> dict[str, dict[str, int | str]]:
    """建立 ABC/BCD/ABD/ABCD 組合配額，處理模型預測為 0 球的組別。

    某組建議配額為 0 時，該組的原配額會轉移至組合內近期強度最高、
    且預測不為 0 的優先組別；組合總球數保持不變。
    """
    result: dict[str, dict[str, int | str]] = {}
    for combination, quota_items in config.combination_quotas:
        allocation = {group: quota for group, quota in quota_items}
        zero_groups = [
            group for group in allocation
            if int(float(prediction.get(group, {}).get("expected", 0.0)) + 0.5) == 0
        ]
        eligible = [
            group for group in allocation
            if group not in zero_groups
        ]
        priority = sorted(
            eligible,
            key=lambda group: float(prediction.get(group, {}).get("strength", 0.0)),
            reverse=True,
        )
        receiver = priority[0] if priority else None
        for group in zero_groups:
            if receiver and group != receiver:
                allocation[receiver] += allocation[group]
                allocation[group] = 0
        recommended = {
            group: max(0, min(7, int(float(prediction.get(group, {}).get("expected", 0.0)) + 0.5)))
            for group, _quota in quota_items
        }
        if sum(recommended.values()) < 5 and eligible:
            receiver = sorted(
                eligible,
                key=lambda group: float(prediction.get(group, {}).get("strength", 0.0)),
                reverse=True,
            )[0]
            recommended[receiver] += 5 - sum(recommended.values())
        result[combination] = {
            "allocation": ", ".join(f"{group}[{allocation[group]}]" for group, _ in quota_items),
            "total": sum(allocation.values()),
            "recommended": ", ".join(
                f"{group}[{recommended[group]}]" for group, _ in quota_items
            ),
            "recommended_total": sum(recommended.values()),
        }
    return result


def best_combination_prediction(
    prediction: Mapping[str, Mapping[str, float | int]],
    config: GroupCountModelConfig = MODEL_CONFIG,
) -> dict[str, str | int]:
    """選出最強三組，並將模型配額補足至該組合的系統原配額。"""
    candidates = [item for item in config.combination_quotas if len(item[1]) == 3]
    combination, quota_items = max(
        candidates,
        key=lambda item: sum(
            float(prediction.get(group, {}).get("strength", 0.0))
            for group, _quota in item[1]
        ),
    )
    allocation = {
        group: max(0, min(quota, int(float(prediction.get(group, {}).get("expected", 0.0)) + 0.5)))
        for group, quota in quota_items
    }
    target_total = sum(quota for _group, quota in quota_items)
    priority = sorted(
        (group for group, _quota in quota_items),
        key=lambda group: float(prediction.get(group, {}).get("strength", 0.0)),
        reverse=True,
    )
    while sum(allocation.values()) < target_total:
        changed = False
        for group in priority:
            quota = dict(quota_items)[group]
            if allocation[group] < quota:
                allocation[group] += 1
                changed = True
                if sum(allocation.values()) >= target_total:
                    break
        if not changed:
            break
    return {
        "combination": combination,
        "allocation": ", ".join(f"{group}[{allocation[group]}]" for group, _ in quota_items),
        "total": sum(allocation.values()),
        "system_total": target_total,
    }


def build_main_architecture_prediction(
    main_group_sequence: Sequence[str],
    group_prediction: Mapping[str, Mapping[str, float | int]] | None = None,
    main_group_prize_records: Sequence[tuple[str, float]] | None = None,
    config: GroupCountModelConfig = MODEL_CONFIG,
) -> dict[str, object]:
    """依每期主力組別及近期窗口權重，建立主力球組最高配額。"""
    if main_group_prize_records:
        main_scores = {group: 0.0 for group, _quota in config.main_base_quotas}
        total_records = len(main_group_prize_records)
        for index, (group, prize_count) in enumerate(main_group_prize_records):
            if group not in main_scores:
                continue
            recency_weight = 1.0 + (index / max(1, total_records - 1))
            main_scores[group] += max(0.0, prize_count) * recency_weight
        ranking = sorted(main_scores, key=lambda group: (-main_scores[group], group))
    elif group_prediction:
        main_scores = {
            group: float(group_prediction.get(group, {}).get("strength", 0.0))
            for group, _quota in config.main_base_quotas
        }
        ranking = sorted(main_scores, key=lambda group: (-main_scores[group], group))
    elif not main_group_sequence:
        ranking = [group for group, _quota in config.main_base_quotas]
    else:
        scores = {group: 0.0 for group, _quota in config.main_base_quotas}
        for index, group in enumerate(main_group_sequence):
            if group not in scores:
                continue
            # 越近期的主力組別權重越高。
            recency_weight = 1.0 + (index / max(1, len(main_group_sequence) - 1))
            scores[group] += recency_weight
        ranking = sorted(scores, key=lambda group: (-scores[group], group))

    base = dict(config.main_base_quotas)
    uplift_groups = set(ranking[:config.main_uplift_count])
    allocation = {
        group: quota + (config.main_uplift_balls if group in uplift_groups else 0)
        for group, quota in base.items()
    }
    return {
        "ranking": ranking,
        "allocation": ", ".join(f"{group}[{allocation[group]}]" for group in base),
        "total": sum(allocation.values()),
    }

