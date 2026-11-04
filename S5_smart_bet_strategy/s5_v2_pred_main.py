"""S5 v2 預測入口：讀取 S5 v3 最佳組合或讓用戶指定組合。"""

from __future__ import annotations

if __name__ == "__main__":
    # 保留同一個命令列介面，實際預測邏輯集中於 v3_comb_pred_main。
    from s5_v3_comb_pred_main import argparse, load_best_pool, predict, ALL_POOLS, RANDOM_SEED

    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", default="best", choices=("best", "all", *ALL_POOLS))
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    selected = ALL_POOLS if args.pool == "all" else (load_best_pool() if args.pool == "best" else args.pool,)
    predict(selected, args.seed)
