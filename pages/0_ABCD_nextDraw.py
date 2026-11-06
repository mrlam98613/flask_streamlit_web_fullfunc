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

from db import add_member_bet, member_bet_exists

try:
    from S5_smart_bet_strategy.s5_v2_abcd_predict import analyze_window, read_draws
    from S5_smart_bet_strategy.s5_v2_config import DATA_PATH, WINDOW_PERIODS
except ImportError:
    analyze_window = None
    read_draws = None
    DATA_PATH = None
    WINDOW_PERIODS = 19


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREDICTION_DIR = PROJECT_ROOT / "S5_smart_bet_strategy" / "next_draw_pred_data"
POOL_PATH = PREDICTION_DIR / "next_draw_pred_balls_pool.csv"
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
            [sys.executable, str(PREDICT_MAIN), "--pool", "all"],
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
    match = re.search(r"(?:s5_v3_pred_|s5_v3_nextdraw_pred_?|s5_v3_)([A-D]+)(?:_\d+){0,2}_?$", name)
    if not match:
        return name
    return match.group(1).replace("_", "+")


POOL_ORDER = ("A+B", "A+C", "A+D", "B+C", "B+D", "C+D", "A+B+C", "A+B+D", "A+C+D", "B+C+D", "A+B+C+D")


def pool_sort_key(path: Path) -> tuple[int, str]:
    """依指定的 11 組合順序排列預測檔案。"""
    label = pool_label(path)
    return (POOL_ORDER.index(label) if label in POOL_ORDER else len(POOL_ORDER), label)


def pool_file_info(path: Path, rows: list[tuple[str, str]]) -> tuple[int, int]:
    """取得組合球池數及注數；新版檔名優先，舊檔名則由號碼估算。"""
    numbers = re.search(r"_([0-9]+)_([0-9]+)_?$", path.stem)
    if numbers:
        return int(numbers.group(1)), int(numbers.group(2))
    unique_numbers = {
        int(value)
        for _date, text in rows
        for value in re.findall(r"\d+", text)
    }
    return len(unique_numbers), len(rows)


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


def load_candidate_pool() -> tuple[str, str, list[str], dict[str, list[int]]]:
    """讀取 S5 v3 產生的 ABCD 候選球池 CSV。"""
    if not POOL_PATH.exists():
        return "", "", [], {}
    pools: dict[str, list[int]] = {}
    main_group = ""
    support_groups: list[str] = []
    with POOL_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            group = (raw.get("group") or "").strip()
            values = [int(value) for value in re.findall(r"\d+", raw.get("candidate_balls") or "")]
            if group in "ABCD":
                pools[group] = values
            if not main_group:
                main_group = (raw.get("main_group") or "").strip()
                support_groups = [value.strip() for value in (raw.get("support_groups") or "").split(",") if value.strip()]
    date = ""
    with POOL_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        first = next(csv.DictReader(handle), None)
        date = (first or {}).get("bet_date", "").strip()
    if not main_group and analyze_window is not None and read_draws is not None and DATA_PATH is not None:
        try:
            draws = read_draws(DATA_PATH)
            analysis = analyze_window(draws[-WINDOW_PERIODS:])
            main_group = str(analysis.get("main", ""))
            support_groups = [str(value) for value in analysis.get("supports", [])]
        except (OSError, ValueError, TypeError):
            pass
    return date, main_group, support_groups, pools


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
    parts = []
    if label:
        parts.append(f"<span style='font-weight:700;margin-right:10px;white-space:nowrap;'>{label}</span>")
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


def parse_ticket_numbers(numbers_text: str) -> list[int]:
    """將預測 CSV 的號碼文字轉成會員投注資料格式。"""
    return [int(value) for value in re.findall(r"\d+", numbers_text) if 1 <= int(value) <= 49][:6]


def sync_all_tickets(path_name: str, count: int) -> None:
    """同步全選狀態至同一組合的每一張單式。"""
    selected = bool(st.session_state.get(f"select_all_{path_name}", False))
    for index in range(1, count + 1):
        st.session_state[f"select_ticket_{path_name}_{index}"] = selected


def render_candidate_pool(date_text: str, pools: dict[str, list[int]]) -> None:
    """以手機適合的細小球圖顯示 A/B/C/D 候選球池。"""
    total = sum(len(values) for values in pools.values())
    st.markdown(f"**下期預測球池：合共 {total} 球**")
    for group in "ABCD":
        values = pools.get(group, [])
        if not values:
            continue
        parts = [
            f"<span style='font-weight:700;min-width:18px;margin-right:3px;'>{group}</span>"
        ]
        for number in values:
            image = ball_image_base64(number)
            if image:
                parts.append(
                    f"<img src='data:image/png;base64,{image}' alt='{number}' "
                    "style='width:23px;height:23px;object-fit:contain;margin:1px;'/>"
                )
            else:
                parts.append(f"<span style='font-size:0.72rem;margin:1px 3px;'>{number}</span>")
        parts.append(f"<span style='font-size:0.75rem;margin-left:4px;'>／{len(values)}球</span>")
        st.markdown(
            "<div style='display:flex;align-items:center;flex-wrap:wrap;line-height:1.1;margin:2px 0;'>"
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
    files = sorted(find_prediction_files(), key=pool_sort_key)
    if not files:
        st.warning("目前找不到預測 CSV，請先執行 S5 v3 預測程式。")
        return

    loaded = {path: load_prediction(path) for path in files}
    bet_date = next((date for date, _rows in loaded.values() if date), "")
    st.markdown(f"**預測投注日期：** {format_date_with_weekday(bet_date)}")
    pool_date, main_group, support_groups, candidate_pools = load_candidate_pool()
    if candidate_pools:
        render_candidate_pool(pool_date or bet_date, candidate_pools)
        if main_group:
            st.markdown(f"**主力組：** {main_group}　**配腳組：** {','.join(support_groups)}")
    st.markdown("**選擇投注組合：**")
    options = []
    option_paths = {}
    for index, path in enumerate(files, start=1):
        _date, rows = loaded[path]
        pool_size, bet_count = pool_file_info(path, rows)
        option = f"{index}. {pool_label(path)}：{pool_size}球 / {bet_count}注"
        options.append(option)
        option_paths[option] = (path, pool_size, bet_count)

    selected = st.selectbox("下拉選擇 11 組合", options, index=0 if options else None)
    if selected:
        path, pool_size, bet_count = option_paths[selected]
        _date, rows = loaded[path]
        select_all_key = f"select_all_{path.name}"
        st.session_state.setdefault(select_all_key, False)
        st.checkbox(
            "全選此組合所有注數",
            key=select_all_key,
            on_change=sync_all_tickets,
            args=(path.name, len(rows)),
        )
        selected_tickets: list[list[int]] = []
        for index, (_row_date, numbers) in enumerate(rows, start=1):
            ticket_numbers = parse_ticket_numbers(numbers)
            ticket_key = f"select_ticket_{path.name}_{index}"
            st.session_state.setdefault(ticket_key, False)
            checkbox_col, ticket_col = st.columns([0.85, 5.15], gap="small")
            with checkbox_col:
                checked = st.checkbox(f"{index}注", key=ticket_key)
            with ticket_col:
                render_ticket_balls(numbers, "")
            if checked:
                selected_tickets.append(ticket_numbers)

        if st.button(
            "➕ 加入下期預測投注",
            type="primary",
            key=f"add_prediction_{path.name}",
            disabled=not selected_tickets,
        ):
            email = st.session_state.get("login_email_val")
            if not email:
                st.session_state["current_page"] = "member"
                st.rerun()
            elif not selected_tickets:
                st.warning("請至少選擇一注。")
            else:
                added = 0
                duplicated = 0
                for ticket in selected_tickets:
                    if member_bet_exists(email, bet_date, "S5_v3 預測", "六合彩單式", ticket):
                        duplicated += 1
                        continue
                    add_member_bet(
                        email=email,
                        bet_date=bet_date,
                        bet_source="S5_v3 預測",
                        bet_type="六合彩單式",
                        numbers=ticket,
                        bet_unit=10,
                        total_bets=1,
                        total_cost=10,
                        notes=f"由 {pool_label(path)} 下期預測加入",
                    )
                    added += 1
                if added:
                    st.success(f"已加入會員投注紀錄：{added} 注。")
                if duplicated:
                    st.info(f"已有相同投注，略過：{duplicated} 注。")


if __name__ == "__main__":
    render_page()
