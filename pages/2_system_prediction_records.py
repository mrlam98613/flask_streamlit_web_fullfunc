"""公開顯示管理員的系統預投注紀錄。"""

from __future__ import annotations

import base64
import csv
import json
import os
import sqlite3
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMBER_DATA_DIR = Path(os.getenv("MEMBER_DATA_DIR", str(PROJECT_ROOT / "member"))).expanduser()
MEMBERS_DB = MEMBER_DATA_DIR / "members.db"
BET_DB_DIR = MEMBER_DATA_DIR / "member_bet_dbs"
BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"
LOTTO_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M2_last_upgrade_lotto_data.csv"
PAYOUTS = {3.0: 40, 3.5: 320, 4.0: 640, 4.5: 9600}


def admin_email() -> str:
    if not MEMBERS_DB.exists():
        return ""
    with sqlite3.connect(MEMBERS_DB) as conn:
        row = conn.execute("SELECT email FROM members WHERE is_admin = 1 ORDER BY id LIMIT 1").fetchone()
    return str(row[0]) if row else ""


def load_records(email: str) -> list[dict]:
    path = BET_DB_DIR / f"{''.join(c if c.isalnum() else '_' for c in email.lower()).strip('_')}_bets.db"
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM bets ORDER BY bet_date DESC, id DESC")]


def load_draws() -> dict[str, list[int]]:
    draws: dict[str, list[int]] = {}
    if not LOTTO_RESULTS_PATH.exists():
        return draws
    with LOTTO_RESULTS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            date = (row.get("ndate") or "").strip()
            numbers = [int(row.get(f"N{i}") or 0) for i in range(1, 8)]
            if date and all(numbers):
                draws[date] = numbers
    return draws


@st.cache_data(show_spinner=False)
def ball_image(number: int) -> str:
    path = BALLS_DIR / f"{number}.png"
    return base64.b64encode(path.read_bytes()).decode() if path.exists() else ""


def ball_html(number: int, highlight: str = "") -> str:
    image = ball_image(number)
    border = "border:2px solid red;border-radius:50%;" if highlight == "main" else "border:2px solid #1677ff;border-radius:5px;" if highlight == "special" else ""
    if image:
        return f"<img src='data:image/png;base64,{image}' style='width:32px;height:32px;object-fit:contain;margin:1px;{border}'/>"
    return f"<span style='display:inline-block;width:32px;text-align:center;{border}'>{number}</span>"


def render_numbers(row: dict, draw: list[int]) -> None:
    bankers = json.loads(row.get("bankers") or "[]")
    legs = json.loads(row.get("legs") or "[]")
    numbers = json.loads(row.get("numbers") or "[]")
    main = set(draw[:6])
    special = draw[6] if len(draw) >= 7 else None

    def group_html(values: list[int]) -> str:
        return "".join(ball_html(int(number), "main" if int(number) in main else "special" if int(number) == special else "") for number in values)

    if bankers or legs:
        html = group_html(bankers) + "<b style='font-size:1.2rem;margin:0 6px;'>+</b>" + group_html(legs)
    else:
        html = group_html(numbers)
    st.markdown(f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:2px;margin:3px 0 10px;'>{html}</div>", unsafe_allow_html=True)


def score(row: dict, draw: list[int]) -> float:
    numbers = set(json.loads(row.get("numbers") or "[]"))
    main = len(numbers & set(draw[:6]))
    return main + (0.5 if len(draw) >= 7 and draw[6] in numbers and main < 6 else 0)


def render_page() -> None:
    st.markdown("<h4 style='margin:0 0 10px;font-size:1.15rem;'>最新 / 過往【系統預投注紀錄】</h4>", unsafe_allow_html=True)
    records = load_records(admin_email())
    draws = load_draws()
    if not records:
        st.info("目前沒有系統預投注紀錄。")
        return

    dates = sorted({str(row.get("bet_date", "")) for row in records}, reverse=True)
    total_cost = 0
    total_payout = 0
    total_bets = 0

    for section_index, section_name in enumerate(("最新紀錄", "過去紀錄")):
        section_dates = dates[:1] if section_index == 0 else dates[1:]
        if not section_dates:
            continue
        st.markdown(
            f"<div style='font-size:0.95rem;font-weight:600;margin:10px 0 5px;'>{section_name}</div>",
            unsafe_allow_html=True,
        )
        record_number = 1
        for selected_date in section_dates:
            selected = [row for row in records if row.get("bet_date") == selected_date]
            draw = draws.get(selected_date, [])
            status = "已開獎" if draw else "未開獎"
            for row in selected:
                total_bets += int(row.get("total_bets") or 1)
                total_cost += int(row.get("total_cost") or 0)
                if draw:
                    total_payout += PAYOUTS.get(score(row, draw), 0) * int(row.get("total_bets") or 1)
                bet_type = str(row.get("bet_type", "")).replace("六合彩", "")
                status_color = "#2563eb" if draw else "#dc2626"
                st.markdown(
                    f"<div style='font-size:0.88rem;font-weight:600;margin:3px 0 2px;'>"
                    f"{record_number}. 投注開獎日期：{selected_date}｜"
                    f"{bet_type}｜<span style='color:{status_color};'>{status}</span></div>",
                    unsafe_allow_html=True,
                )
                render_numbers(row, draw)
                st.markdown("<hr style='margin:6px 0 12px;border:0;border-top:1px solid #d1d5db;'>", unsafe_allow_html=True)
                record_number += 1

    st.markdown(
        "<div style='font-size:0.95rem;font-weight:600;margin:14px 0 6px;'>"
        "系統預測：投注損益資料</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:1.05rem;line-height:1.9;'>"
        f"投注期次數：1 次｜已開獎：{1 if draw else 0} 次<br>"
        f"總投注金額：${total_cost}<br>"
        f"總派彩金額：${total_payout}<br>"
        f"<b>投注派彩損益：${total_payout - total_cost:+d}</b>"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render_page()
