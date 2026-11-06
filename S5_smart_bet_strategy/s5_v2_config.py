from pathlib import Path

# 專案根目錄及版本名稱。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "S5_v2，ABCD 趨勢預測 + 動態配額投注組合"
# 歷史開獎資料來源及回測 CSV 輸出目錄。
DATA_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M6_lotto_history_prize.csv"
DATA_DIR = Path(__file__).resolve().parent / "data"

# 手動測試參數。
BACKTEST_PERIODS = 10
WINDOW_PERIODS = 19
RANDOM_SEED = 20261105
# S5 v2 預設輸出的兩組、三組及四組組合。
OUTPUT_POOLS = ("A+B", "A+B+C", "A+B+C+D")

# 原始 ABCD 分組範圍；實際候選池由 HFB/HFL 動態產生。
GROUPS = {
    "A": tuple(range(1, 10)),
    "B": tuple(range(10, 21)),
    "C": tuple(range(21, 32)),
    "D": tuple(range(32, 41)),
}
