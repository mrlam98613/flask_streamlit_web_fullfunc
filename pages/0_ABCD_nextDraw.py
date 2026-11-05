"""顯示 S5 v3 ABCD 動態候選球池的下期投注預測。"""

from __future__ import annotations

import csv
import base64
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREDICTION_DIR = PROJECT_ROOT / "S5_smart_bet_strategy" / "next_draw_pred_data"
BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"
M4_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M4_lotto_prize_summary.csv"
PREDICT_MAIN = PROJECT_ROOT / "S5_smart_bet_strategy" / "s5_v3_comb_pred_main.py"


def find_prediction_files() -> list[Path]:
    """掃描預測目錄，取得所有可用的 S5 預測 CSV，不依賴固定檔名。"""
    if not PREDICTION_DIR.exists():
        return []
    return sorted(
        path for path in PREDICTION_DIR.glob("*.csv")
        if path.name.startswith(("s5_v3_", "s5_v3_nextdraw_pred"))
    )


def load_next_draw_date() -> str:
    """讀取 M4 最新一列的下期開獎日期。"""
    if not M4_PATH.exists():
        return ""
    with M4_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1].get("next_draw_date", "").strip() if rows else ""


def prediction_exists_for_date(target_date: str, files: list[Path]) -> bool:
    """檢查現有預測 CSV 是否已有指定下期日期。"""
    if not target_date:
        return False
    for path in files:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if (row.get("bet_date") or "").strip() == target_date:
                        return True
        except OSError:
            continue
    return False


def ensure_latest_prediction() -> tuple[bool, str]:
    """只在預測目錄沒有最新日期時執行 S5 v3 預測。"""
    target_date = load_next_draw_date()
    files = find_prediction_files()
    if prediction_exists_for_date(target_date, files):
        return False, target_date
    if not PREDICT_MAIN.exists():
        return False, target_date
    try:
        subprocess.run(
            [sys.executable, str(PREDICT_MAIN), "--pool", "best"],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return True, target_date
    except (OSError, subprocess.SubprocessError) as error:
        st.warning(f"未能自動更新下期投注預測：{error}")
        return False, target_date


def pool_label(path: Path) -> str:
    """由檔名轉成顯示用的組合名稱，例如 A_C 變成 A+C。"""
    name = path.stem
    match = re.search(r"(?:s5_v3_pred_|s5_v3_nextdraw_pred_?|s5_v3_)([A-D]+)(?:_\d+_)?$", name)
    if not match:
        return name
    return match.group(1).replace("_", "+")


def load_prediction(path: Path) -> tuple[str, list[tuple[str, str]]]:
    """讀取預測 CSV，回傳預測日期及每注號碼文字。"""
    rows: list[tuple[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {(key or "").strip(): (value or "").strip() for key, value in raw.items()}
            rows.append((row.get("bet_date", ""), row.get("N1_N6", "")))
    date = rows[0][0] if rows else ""
    return date, rows


def format_date_with_weekday(date_text: str) -> str:
    """將 YYYY-MM-DD 日期格式化為日期加中文星期。"""
    try:
        date_value = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return date_text or "未提供"
    weekdays = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
    return f"{date_text} {weekdays[date_value.weekday()]}"


@st.cache_data(show_spinner=False)
def ball_image_base64(number: int) -> str:
    """讀取指定球號 PNG，轉成網頁可顯示的 Base64。"""
    path = BALLS_DIR / f"{number}.png"
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def render_ticket_balls(numbers_text: str, label: str) -> None:
    """將 CSV 號碼文字轉成與主預測頁相同的單行六合彩球圖。"""
    numbers = [int(value) for value in re.findall(r"\d+", numbers_text) if 1 <= int(value) <= 49]
    if not numbers:
        st.write(f"{label} {numbers_text or '-'}")
        return
    parts = [f"<span style='font-weight:700;margin-right:10px;white-space:nowrap;'>{label}</span>"]
    for number in numbers[:6]:
        image = ball_image_base64(number)
        if image:
            parts.append(
                f"<img src='data:image/png;base64,{image}' alt='{number}' "
                "style='width:36px;height:36px;object-fit:contain;margin-right:5px;'/>"
            )
        else:
            parts.append(f"<span style='font-weight:700;margin-right:10px;'>{number}</span>")
    st.markdown(
        "<div style='display:flex;align-items:center;flex-wrap:nowrap;'>"
        + "".join(parts)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_page() -> None:
    """渲染 ABCD 下期動態投注頁面。"""
    st.markdown(
        "<h4 style='margin:0 0 6px 0;font-size:1.15rem;'>ABCD 下期動態投注預測</h4>",
        unsafe_allow_html=True,
    )
    st.caption("讀取 S5 v3 產生的最新預測 CSV；檔名可按組合動態變化。")

    updated, target_date = ensure_latest_prediction()
    if updated:
        st.success(f"已更新下期投注預測：{target_date}")
    files = find_prediction_files()
    if not files:
        st.warning("目前找不到預測 CSV，請先執行 S5 v3 預測程式。")
        return

    loaded = {path: load_prediction(path) for path in files}
    bet_date = next((date for date, _rows in loaded.values() if date), "")
    st.markdown(f"**預測投注日期：** {format_date_with_weekday(bet_date)}")
    st.markdown("**選擇投注組合：**")

    selected_paths = []
    for path in files:
        date, rows = loaded[path]
        label = f"{pool_label(path)}，{len(rows)} 注"
        if st.checkbox(label, key=f"abcd_pool_{path.name}"):
            selected_paths.append(path)

    for path in selected_paths:
        _date, rows = loaded[path]
        st.markdown(f"#### {pool_label(path)}：{len(rows)} 注")
        for index, (_row_date, numbers) in enumerate(rows, start=1):
            render_ticket_balls(numbers, f"第 {index} 注：")


if __name__ == "__main__":
    render_page()
