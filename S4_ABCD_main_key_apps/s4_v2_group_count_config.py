"""S4 v2 分組球數策略模型參數。

本檔案只放參數，不放分析或預測邏輯；修改模型時可避免影響主程式。
"""

from dataclasses import dataclass


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
    main_uplift_count: int = 3
    main_uplift_balls: int = 1
    # 四種可選組合的預設配額；配額總數至少 5 球。
    combination_quotas: tuple[tuple[str, tuple[tuple[str, int], ...]], ...] = (
        ("ABC", (("A", 3), ("B", 4), ("C", 4))),
        ("BCD", (("B", 4), ("C", 4), ("D", 3))),
        ("ABD", (("A", 3), ("B", 4), ("D", 3))),
        ("ABCD", (("A", 2), ("B", 3), ("C", 3), ("D", 2))),
    )


MODEL_CONFIG = GroupCountModelConfig()

