from pathlib import Path
import base64
import csv
import re
from datetime import datetime

import streamlit as st
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIZE_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M3_lotto_prize_results.csv"
BET_RECORDS_PATH = PROJECT_ROOT / "A_new_bet_data_folder" / "my_bet_records.csv"
BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"
PREDICT_LAST_RUN_PATH = PROJECT_ROOT / "A_new_bet_data_folder" / "predict_last_run.txt"

import importlib.util
PREDICT_DIR = PROJECT_ROOT / "msk_2026_RBG_predict_V4"
if str(PREDICT_DIR) not in sys.path:
    sys.path.insert(0, str(PREDICT_DIR))

_spec = importlib.util.spec_from_file_location(
    "A_new_next_Pred_betDraw",
    PREDICT_DIR / "A_new_next_Pred_betDraw.py",
)

pred_job = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pred_job)


def run_predict_once_per_day(get_bet_draw: int, next_draw_date: str = ""):
    """每天只執行一次預測；若下期日期在 CSV 中已無對應記錄（開獎更新後），強制重新執行。"""
    today_key = f"{datetime.now().strftime('%Y-%m-%d')}:{int(get_bet_draw)}"

    # 優先檢查：CSV 內是否已有下期日期的預測，沒有就直接執行（不受每日限制）
    if next_draw_date:
        has_pred = False
        if BET_RECORDS_PATH.exists():
            with BET_RECORDS_PATH.open("r", encoding="utf-8-sig") as f:
                for line in f:
                    if line.startswith(next_draw_date):
                        has_pred = True
                        break
        if not has_pred:
            with st.spinner(f"正在產生下期投注預測（{int(get_bet_draw)}注）..."):
                pred_job.main(get_BetDraw=int(get_bet_draw))
            PREDICT_LAST_RUN_PATH.write_text(today_key, encoding="utf-8")
            st.session_state["predict_ran_today"] = today_key
            return

    # Session 內已執行過，直接跳過
    if st.session_state.get("predict_ran_today") == today_key:
        return

    # 檢查磁碟記錄
    if PREDICT_LAST_RUN_PATH.exists():
        stored = PREDICT_LAST_RUN_PATH.read_text(encoding="utf-8").strip()
        if stored == today_key:
            st.session_state["predict_ran_today"] = today_key
            return

    # 執行預測
    with st.spinner(f"正在產生下期投注預測（{int(get_bet_draw)}注）..."):
        pred_job.main(get_BetDraw=int(get_bet_draw))

    # 寫入記錄
    PREDICT_LAST_RUN_PATH.write_text(today_key, encoding="utf-8")
    st.session_state["predict_ran_today"] = today_key


@st.cache_data(show_spinner=False)
def load_ball_image_base64(num: int):
    img_path = BALLS_DIR / f"{num}.png"
    if not img_path.exists():
        return ""
    return base64.b64encode(img_path.read_bytes()).decode("utf-8")


def extract_ymd(text: str):
    if not text:
        return None

    m_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m_iso:
        return f"{m_iso.group(1)}-{m_iso.group(2)}-{m_iso.group(3)}"

    m_zh = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if m_zh:
        y = m_zh.group(1)
        mm = m_zh.group(2).zfill(2)
        dd = m_zh.group(3).zfill(2)
        return f"{y}-{mm}-{dd}"

    return None


def format_date_with_weekday(date_text: str):
    if not date_text:
        return "-"

    try:
        dt = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return date_text

    weekday_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    return f"{date_text}（{weekday_map[dt.weekday()]}）"


def parse_num_list(text: str):
    if not text:
        return []
    nums = [int(x) for x in re.findall(r"\d+", text)]
    return [n for n in nums if 1 <= n <= 49]


def render_balls(nums, label: str = ""):
    if not nums:
        st.write("-")
        return

    parts = []
    for idx, n in enumerate(nums):
        if len(nums) >= 7 and idx == 6:
            parts.append("<span style='font-weight:700;margin:0 8px;'>+</span>")

        b64 = load_ball_image_base64(int(n))
        if b64:
            parts.append(
                f"<img src='data:image/png;base64,{b64}' style='width:32px;height:32px;object-fit:contain;margin-right:3px;'/>"
            )
        else:
            parts.append(f"<span style='display:inline-block;margin-right:6px;font-weight:600;'>{n}</span>")

    label_html = ""
    if label:
        label_html = f"<span style='font-weight:600;margin-right:8px;'>{label}</span>"

    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:center;flex-wrap:nowrap;overflow-x:auto;'>{label_html}{''.join(parts)}</div>",
        unsafe_allow_html=True,
    )


def load_prize_result_info(path: Path):
    latest_date_raw = ""
    latest_numbers_raw = ""
    next_draw_raw = ""

    if not path.exists():
        return latest_date_raw, latest_numbers_raw, next_draw_raw

    with path.open("r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(line for line in f if line.strip()))

    in_latest = False
    in_next = False
    for row in rows:
        if not row:
            continue
        head = row[0].strip().lstrip("\ufeff")

        if head == "🔴 最新一期":
            in_latest = True
            in_next = False
            continue
        if head == "🟢 下一期":
            in_latest = False
            in_next = True
            continue

        if in_latest and len(row) >= 2:
            key = row[0].strip().lstrip("\ufeff")
            val = ",".join(row[1:]).strip()
            if key == "日期":
                latest_date_raw = val
            elif key == "號碼":
                latest_numbers_raw = val

        if in_next and len(row) >= 2:
            key = row[0].strip().lstrip("\ufeff")
            val = ",".join(row[1:]).strip()
            if key == "開獎日期":
                next_draw_raw = val

    return latest_date_raw, latest_numbers_raw, next_draw_raw


def load_prize_payout_rows(path: Path):
    """從 M3 CSV 解析最新一期的期數及七個獎級派彩明細。"""
    period = ""
    rows = []
    if not path.exists():
        return period, rows

    with path.open("r", encoding="utf-8-sig") as f:
        raw_rows = list(csv.reader(line for line in f if line.strip()))

    in_latest = False
    in_prizes = False
    for row in raw_rows:
        if not row:
            continue
        head = row[0].strip().lstrip("\ufeff")

        if head == "\U0001f534 最新一期":
            in_latest = True
            in_prizes = False
            continue
        if head == "\U0001f7e2 下一期":
            break

        if in_latest:
            if head == "期數" and len(row) >= 2:
                period = row[1].strip()
            elif head == "獎項":
                in_prizes = True
                continue
            elif in_prizes and len(row) >= 3:
                rows.append({
                    "獎項": row[0].strip(),
                    "獎金": row[1].strip(),
                    "中獎注數": row[2].strip(),
                })

    return period, rows


def load_predictions_for_date(path: Path, target_date: str):
    if not path.exists() or not target_date:
        return []

    result = []
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            reader.fieldnames = [name.strip().lstrip("\ufeff") for name in reader.fieldnames]

        for row in reader:
            clean_row = {(k or "").strip().lstrip("\ufeff"): (v or "").strip() for k, v in row.items()}
            bet_date = clean_row.get("bet_date", "")
            if bet_date != target_date:
                continue

            nums = []
            for i in range(1, 7):
                val = clean_row.get(f"N{i}", "")
                if val.isdigit():
                    n = int(val)
                    if 1 <= n <= 49:
                        nums.append(n)
            if len(nums) == 6:
                result.append(nums)

    return result


def render_home_page():
    get_bet_draw = int(st.session_state.get("setting_get_BetDraw", 2))

    latest_date_raw, latest_numbers_raw, next_draw_raw = load_prize_result_info(PRIZE_RESULTS_PATH)

    latest_date = extract_ymd(latest_date_raw)
    latest_numbers = parse_num_list(latest_numbers_raw)
    next_draw_date = extract_ymd(next_draw_raw)
    latest_date_display = format_date_with_weekday(latest_date or latest_date_raw)
    next_draw_date_display = format_date_with_weekday(next_draw_date or next_draw_raw)

    # 加入最新派彩資訊
    period, payout_rows = load_prize_payout_rows(PRIZE_RESULTS_PATH)

    period_display = f"（{period}）" if period else ""
    st.write(f"1.最新一期開獎結果 {period_display}")
    st.write(f"開獎日期：{latest_date_display}")
    render_balls(latest_numbers[:7])

    if payout_rows:
        import pandas as pd
        st.markdown("**派彩結果：**")
        st.dataframe(
            pd.DataFrame(payout_rows),
            width='stretch',
            hide_index=True,
        )

    st.markdown("---")
    st.write("2.下期投注預測")
    st.caption(f"目前設定：顯示 {get_bet_draw} 注下期預測")
    st.write(f"投注日期：{next_draw_date_display}")
    run_predict_once_per_day(get_bet_draw, next_draw_date=next_draw_date or "")  # 每天只執行一次，但下期無記錄時強制補跑

    pred_rows = load_predictions_for_date(BET_RECORDS_PATH, next_draw_date or "")
    if pred_rows:
        for idx, nums in enumerate(pred_rows, start=1):
            render_balls(nums, label=f"{idx}注:")
    else:
        st.info("目前沒有找到對應下期開獎日期的預測號碼。")


if __name__ == "__main__":
    render_home_page()
