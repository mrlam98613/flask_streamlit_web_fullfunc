"""舊版 S5 v2 預測入口；正式預測請使用 s5_v3_comb_pred_main.py。"""

from __future__ import annotations

if __name__ == "__main__":
    # 保留舊版行為：只讀取現有最佳組合 JSON，不重新執行 v3 回測。
    from s5_v3_comb_pred_main import ALL_POOLS, RANDOM_SEED, argparse, load_best_pool, predict

    parser = argparse.ArgumentParser(description="舊版 S5 v2 預測入口")
    parser.add_argument("--pool", default="best", choices=("best", "all", *ALL_POOLS))
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    selected = ALL_POOLS if args.pool == "all" else (load_best_pool() if args.pool == "best" else args.pool,)
    predict(selected, args.seed)
