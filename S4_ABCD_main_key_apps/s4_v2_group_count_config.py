"""S4 v2 分組球數策略模型參數。

本檔案只放參數，不放分析或預測邏輯；修改模型時可避免影響主程式。
"""

from dataclasses import dataclass


# v2 專用資料及回測設定；不讀取或依賴 v1 的窗口設定。
WINDOW_SIZE = 19
SELECT_GROUPS = (1, 2, 3, 4)
MAIN_CANDIDATE_GROUPS = ("A", "B", "C") # 主要組別分析 # D組 不在主力組 
GROUP_RANGES = (
    (1, "A", 1, 9),
    (2, "B", 10, 20),
    (3, "C", 21, 31),
    (4, "D", 32, 40),
)
# 查詢條件
COMB_MATCH_MODE = ">="
COMBINATION_TAKE_COUNT = 5


@dataclass(frozen=True)
class GroupCountModelConfig:
    """分組球數預測模型設定。"""

    recent_windows: tuple[int, ...] = (7, 10, 19)
    window_weights: tuple[float, ...] = (0.50, 0.30, 0.20)
    low_quantile: float = 0.20
    high_quantile: float = 0.80
    quota_mode: int = 1
    quota_min: int = 1
    quota_max: int = 3
    use_group_size_baseline: bool = True
    use_recent_strength_adjustment: bool = True
    main_base_quotas: tuple[tuple[str, int], ...] = (
        ("A", 3), ("B", 4), ("C", 4), ("D", 3)
    )
    # 預測球數的分組範圍；用於 ABC 組合的逐期回測配額。
    group_quota_ranges: tuple[tuple[str, int, int], ...] = (
        ("A", 1, 4), ("B", 2, 5), ("C", 2, 5), ("D", 1, 4)
    )
    combination_min_total: int = 8
    main_uplift_count: int = 1
    main_uplift_balls: int = 1
    # 四種可選組合的預設配額；配額總數至少 5 球。
    combination_quotas: tuple[tuple[str, tuple[tuple[str, int], ...]], ...] = (
        ("ABC", (("A", 3), ("B", 4), ("C", 4))),
        ("BCD", (("B", 4), ("C", 4), ("D", 3))),
        ("ABD", (("A", 3), ("B", 4), ("D", 3))),
        ("ABCD", (("A", 2), ("B", 3), ("C", 3), ("D", 2))),
    )


MODEL_CONFIG = GroupCountModelConfig()

# 自我學習設定：最多取最近 200 個逐期核對樣本，前 160 調參，後 40 驗證。
LEARNING_HISTORY_COUNT = 200
LEARNING_VALIDATION_COUNT = 40
PRIZE3_WEIGHT_POWERS = (0.0, 0.5, 1.0)
PAYOUT_WEIGHT_POWERS = (0.0, 0.5, 1.0)
GROUP_STRENGTH_POWERS = (0.0, 0.5, 1.0)
RECENCY_DECAYS = (0.90, 0.95, 1.0)
LEARNING_LOG_CSV_NAME = "s4_v2_learning_backtest.csv"
LEARNED_PARAMS_JSON_NAME = "s4_v2_learned_params.json"

