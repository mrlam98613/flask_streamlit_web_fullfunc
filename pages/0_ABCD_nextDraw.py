"""顯示 S5 v3 ABCD 動態候選球池的下期投注預測。"""

from __future__ import annotations

import csv
import base64
import re
from datetime import datetime
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREDICTION_DIR = PROJECT_ROOT / "S5_smart_bet_strategy" / "next_draw_pred_data"
BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"


def find_prediction_files() -> list[Path]:
    """掃描預測目錄，取得所有可用的 S5 預測 CSV，不依賴固定檔名。"""
    if not PREDICTION_DIR.exists():
        return []
    return sorted(
        path for path in PREDICTION_DIR.glob("*.csv")
        if path.name.startswith(("s5_v3_pred_", "s5_v3_nextdraw_pred"))
    )


def pool_label(path: Path) -> str:
    """由檔名轉成顯示用的組合名稱，例如 A_C 變成 A+C。"""
    name = path.stem
    match = re.search(r"(?:s5_v3_pred_|s5_v3_nextdraw_pred_?)(.+)$", name)
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

    files = find_prediction_files()
    if not files:
        st.warning("目前找不到預測 CSV，請先執行 S5 v3 預測程式。")
        return

    options = {f"{pool_label(path)}（{path.name}）": path for path in files}
    selected_label = st.selectbox("選擇投注組合", list(options))
    selected_path = options[selected_label]
    bet_date, rows = load_prediction(selected_path)

    st.markdown(f"**預測投注日期：** {format_date_with_weekday(bet_date)}")
    st.markdown(f"**投注組合：** {pool_label(selected_path)}　**總注數：** {len(rows)} 注")

    for index, (_date, numbers) in enumerate(rows, start=1):
        render_ticket_balls(numbers, f"第 {index} 注：")


if __name__ == "__main__":
    render_page()
