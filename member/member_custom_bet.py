from __future__ import annotations

import base64
import csv
import json
import math
import random
from datetime import datetime
from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import add_member_bet, list_member_bets, member_bet_exists  # noqa: E402
from custom_components.number_picker import number_picker  # noqa: E402


BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"
PRIZE_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M3_lotto_prize_results.csv"
ABCD_POOL_PATH = PROJECT_ROOT / "S5_smart_bet_strategy" / "next_draw_pred_data" / "next_draw_pred_balls_pool.csv"
ALL_NUMBERS = list(range(1, 50))


@st.cache_data(show_spinner=False)
def load_ball_image_base64(num: int) -> str:
    img_path = BALLS_DIR / f"{int(num)}.png"
    if not img_path.exists():
        return ""
    return base64.b64encode(img_path.read_bytes()).decode("utf-8")


def init_custom_bet_state() -> None:
    """初始化自定投注狀態。"""

    st.session_state.setdefault("custom_seed_numbers", [])
    st.session_state.setdefault("custom_picker_seed_numbers", [])
    st.session_state.setdefault("custom_generated_numbers", [])
    st.session_state.setdefault("custom_generated_signature", None)
    st.session_state.setdefault("custom_seed_reset_token", 0)
    st.session_state.setdefault("custom_banker_numbers", [])
    st.session_state.setdefault("custom_leg_numbers", [])
    st.session_state.setdefault("custom_banker_reset_token", 0)
    st.session_state.setdefault("custom_leg_reset_token", 0)
    st.session_state.setdefault("custom_saved_notice", "")
    st.session_state.setdefault("custom_save_locked", False)
    st.session_state.setdefault("custom_last_banker_count", None)


def extract_ymd(text: str) -> str:
    """從中文日期或 ISO 日期取出 yyyy-mm-dd。"""

    if not text:
        return ""

    import re

    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"

    zh = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if zh:
        return f"{zh.group(1)}-{zh.group(2).zfill(2)}-{zh.group(3).zfill(2)}"

    return text


def load_next_draw_date() -> str:
    """從 M3_lotto_prize_results.csv 讀取下一期開獎日期。"""

    if not PRIZE_RESULTS_PATH.exists():
        return ""

    with PRIZE_RESULTS_PATH.open("r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if row and row[0].strip().lstrip("\ufeff") == "開獎日期" and len(row) >= 2:
                return extract_ymd(row[1].strip())

    return ""


def format_date_with_weekday(date_text: str) -> str:
    """把 yyyy-mm-dd 顯示成 yyyy-mm-dd（星期X）。"""

    if not date_text:
        return ""

    try:
        dt = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return date_text

    week_map = ["一", "二", "三", "四", "五", "六", "日"]
    return f"{date_text}（星期{week_map[dt.weekday()]}）"


def load_abcd_pool() -> tuple[str, list[str], dict[str, list[int]]]:
    """讀取最新 S5 v3 ABCD 候選球池。"""
    if not ABCD_POOL_PATH.exists():
        return "", [], {}
    import re

    pools: dict[str, list[int]] = {}
    main_group = ""
    support_groups: list[str] = []
    with ABCD_POOL_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            group = (row.get("group") or "").strip()
            if group in "ABCD":
                pools[group] = [
                    int(value)
                    for value in re.findall(r"\d+", row.get("candidate_balls") or "")
                ]
            if not main_group:
                main_group = (row.get("main_group") or "").strip()
                support_groups = [
                    value.strip()
                    for value in (row.get("support_groups") or "").split(",")
                    if value.strip()
                ]
    return main_group, support_groups, pools


def render_abcd_pool_card() -> None:
    """以文字卡片顯示最新 ABCD 預測球池。"""
    main_group, support_groups, pools = load_abcd_pool()
    if not pools:
        return
    total = sum(len(values) for values in pools.values())
    rows = "".join(
        f"<div class='abcd-pool-row'><span>{group}</span><span class='abcd-pool-values'>{values}</span><b>{len(values)} 球</b></div>"
        for group, values in ((group, pools.get(group, [])) for group in "ABCD")
        if values
    )
    st.markdown(
        f"""
        <div class='abcd-pool-card'>
          <div class='abcd-pool-title'>下期預測球池：ABCD 組，合共 {total} 球</div>
          <div class='abcd-pool-trend'><b>主力組：</b>{main_group or '未提供'}　<b>配腳組：</b>{','.join(support_groups) or '未提供'}</div>
          {rows}
        </div>
        <style>
        .abcd-pool-card {{ border:1px solid #dbeafe; border-radius:10px; background:#f8fbff; padding:10px 12px; margin:4px 0 12px; }}
        .abcd-pool-title {{ font-weight:700; color:#1e3a8a; margin-bottom:6px; }}
        .abcd-pool-trend {{ font-size:0.9rem; color:#374151; margin-bottom:5px; }}
        .abcd-pool-row {{ display:flex; gap:8px; align-items:center; padding:3px 0; font-size:0.88rem; }}
        .abcd-pool-row span {{ width:18px; font-weight:700; }}
        .abcd-pool-values {{ flex:1; color:#374151; font:inherit; white-space:normal; }}
        .abcd-pool-row b {{ white-space:nowrap; color:#4b5563; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def reset_generated_numbers() -> None:
    """種子或投注設定改變後，清空舊發球結果。"""

    st.session_state["custom_generated_numbers"] = []
    st.session_state["custom_generated_signature"] = None
    st.session_state["custom_saved_notice"] = ""
    st.session_state["custom_save_locked"] = False


def clear_direct_numbers() -> None:
    """清除單式／複式直接選取的號碼。"""
    st.session_state["custom_direct_numbers"] = []
    reset_generated_numbers()


def reset_banker_leg_numbers() -> None:
    """清空膽拖選號。"""

    st.session_state["custom_banker_numbers"] = []
    st.session_state["custom_leg_numbers"] = []
    st.session_state["custom_banker_reset_token"] += 1
    st.session_state["custom_leg_reset_token"] += 1
    st.session_state["custom_saved_notice"] = ""
    st.session_state["custom_save_locked"] = False


def reset_custom_bet_outputs() -> None:
    """投注種類或金額改變時，清空已產生投注。"""

    st.session_state["custom_seed_numbers"] = []
    st.session_state["custom_picker_seed_numbers"] = []
    st.session_state["custom_seed_reset_token"] += 1
    st.session_state["custom_last_banker_count"] = None
    st.session_state["custom_direct_numbers"] = []
    st.session_state["custom_save_locked"] = False
    reset_generated_numbers()
    reset_banker_leg_numbers()


def render_seed_picker(seeds: list[int], nums: list[int]) -> None:
    """顯示 1-49 球號，最多可選 3 個種子球。"""

    render_selected_and_generated_numbers(seeds, nums)
    render_seed_only_picker(seeds)


def render_direct_bet_picker(bet_size: int) -> list[int]:
    """單式／複式直接由 1-49 按鈕選滿指定球數。"""
    selected = number_picker(
        selected=st.session_state.get("custom_direct_numbers", []),
        max_select=bet_size,
        reset_token=st.session_state.get("custom_seed_reset_token", 0),
        key=f"custom_direct_number_picker_{st.session_state.get('custom_seed_reset_token', 0)}_{bet_size}",
    )
    selected = sorted(int(num) for num in selected)
    st.session_state["custom_direct_numbers"] = selected
    return selected


def render_seed_only_picker(seeds: list[int]) -> None:
    """只顯示種子選號盤。"""

    picker_seeds = st.session_state.get("custom_picker_seed_numbers", seeds)
    selected = number_picker(
        selected=picker_seeds,
        max_select=3,
        reset_token=st.session_state["custom_seed_reset_token"],
        key=f"custom_seed_number_picker_{st.session_state['custom_seed_reset_token']}",
    )
    selected = sorted(int(num) for num in selected)
    if selected != picker_seeds:
        st.session_state["custom_picker_seed_numbers"] = selected
        st.session_state["custom_seed_numbers"] = selected
        reset_generated_numbers()
        st.rerun()


def render_banker_leg_picker(
    bankers: list[int],
    legs: list[int],
    banker_count: int,
    leg_count: int,
) -> None:
    """用單一 1-49 鍵盤選膽或配腳。"""

    pick_options = ["膽", "配腳"]
    if st.session_state.get("custom_banker_leg_pick_mode") not in pick_options:
        st.session_state["custom_banker_leg_pick_mode"] = "膽"

    pick_mode = st.radio(
        "選號模式",
        pick_options,
        horizontal=True,
        key="custom_banker_leg_pick_mode",
    )

    if pick_mode == "膽":
        selected = number_picker(
            selected=bankers,
            max_select=banker_count,
            disabled_numbers=legs,
            reset_token=st.session_state["custom_banker_reset_token"],
            key=f"custom_banker_leg_picker_banker_{st.session_state['custom_banker_reset_token']}_{banker_count}",
        )
        selected_bankers = sorted(int(num) for num in selected)
        if selected_bankers != bankers:
            st.session_state["custom_banker_numbers"] = selected_bankers
            st.session_state["custom_leg_numbers"] = [num for num in legs if num not in selected_bankers]
            st.session_state["custom_saved_notice"] = ""
            st.session_state["custom_save_locked"] = False
            st.rerun()
    else:
        selected = number_picker(
            selected=legs,
            max_select=leg_count,
            disabled_numbers=bankers,
            reset_token=st.session_state["custom_leg_reset_token"],
            key=f"custom_banker_leg_picker_leg_{st.session_state['custom_leg_reset_token']}_{leg_count}",
        )
        selected_legs = sorted(int(num) for num in selected if int(num) not in bankers)
        if selected_legs != legs:
            st.session_state["custom_leg_numbers"] = selected_legs
            st.session_state["custom_saved_notice"] = ""
            st.session_state["custom_save_locked"] = False
            st.rerun()


def get_bet_config():
    """讀取投注種類、球數、每注金額。"""

    bet_type = st.radio(
        "投注種類",
        ["單式 [6]", "複式 [7-15]", "膽拖 [1-5]膽"],
        horizontal=True,
        key="custom_bet_type",
        on_change=reset_custom_bet_outputs,
    )

    bet_size = 6
    if bet_type == "複式 [7-15]":
        bet_size = int(
            st.selectbox(
                "複式球數",
                list(range(7, 16)),
                key="custom_multiple_size",
                on_change=reset_custom_bet_outputs,
            )
        )

    if bet_type == "單式 [6]":
        bet_unit = 10
        st.selectbox("每注金額", ["$10 固定"], disabled=True, key="custom_single_unit")
    else:
        bet_unit = int(
            st.selectbox(
                "每注金額",
                [5, 10],
                format_func=lambda value: f"${value}",
                key="custom_bet_unit",
                on_change=reset_custom_bet_outputs,
            )
        )

    return bet_type, bet_size, bet_unit


def calculate_total_bets(bet_type: str, bet_size: int) -> int:
    """計算投注注數；目前先支援單式和複式。"""

    if bet_type == "單式 [6]":
        return 1
    if bet_type == "複式 [7-15]":
        return math.comb(bet_size, 6)
    return 0


def calculate_banker_leg_bets(bankers: list[int], legs: list[int]) -> int:
    """膽拖注數 = 從配腳選出補足 6 個號碼的組合數。"""

    banker_count = len(bankers)
    leg_count = len(legs)
    need_legs_per_bet = 6 - banker_count
    if banker_count < 1 or banker_count > 5 or leg_count < 7 - banker_count:
        return 0
    return math.comb(leg_count, need_legs_per_bet)


def generate_numbers(seed_numbers: list[int], bet_size: int) -> list[int]:
    """用 random 暫時補足投注號碼。"""

    need_count = bet_size - len(seed_numbers)
    pool = [num for num in ALL_NUMBERS if num not in seed_numbers]
    generated = sorted(seed_numbers + random.sample(pool, need_count))
    return generated


def generate_banker_leg_numbers(
    seed_numbers: list[int],
    banker_count: int = 1,
    leg_count: int | None = None,
) -> tuple[list[int], list[int]]:
    """用種子優先補膽，再補足最少配腳。"""

    banker_count = min(max(int(banker_count), 1), 5)
    leg_count = 7 - banker_count if leg_count is None else int(leg_count)
    leg_count = min(max(leg_count, 7 - banker_count), 49 - banker_count)
    seed_numbers = sorted({int(num) for num in seed_numbers if 1 <= int(num) <= 49})
    rng = random.Random(datetime.now().strftime("%Y%m%d%H%M%S%f"))

    bankers = seed_numbers[:banker_count]
    banker_pool = [num for num in ALL_NUMBERS if num not in bankers]
    if len(bankers) < banker_count:
        bankers = sorted(bankers + rng.sample(banker_pool, banker_count - len(bankers)))

    leg_pool = [num for num in ALL_NUMBERS if num not in bankers]
    legs = sorted(rng.sample(leg_pool, leg_count))
    return bankers, legs


def fill_banker_leg_numbers(
    bankers: list[int],
    legs: list[int],
    banker_count: int,
    leg_count: int,
) -> tuple[list[int], list[int]]:
    """保留已選膽/腳，再補足到指定數量。"""

    rng = random.Random(datetime.now().strftime("%Y%m%d%H%M%S%f"))
    new_bankers = sorted({int(num) for num in bankers})[:banker_count]
    seed_legs = sorted({int(num) for num in legs if int(num) not in new_bankers})[:leg_count]
    pool = [num for num in ALL_NUMBERS if num not in new_bankers and num not in seed_legs]
    if len(new_bankers) < banker_count:
        new_bankers = sorted(new_bankers + rng.sample(pool, banker_count - len(new_bankers)))

    new_legs = sorted(num for num in seed_legs if num not in new_bankers)[:leg_count]
    leg_pool = [num for num in ALL_NUMBERS if num not in new_bankers and num not in new_legs]
    if len(new_legs) < leg_count:
        new_legs = sorted(new_legs + rng.sample(leg_pool, leg_count - len(new_legs)))

    return new_bankers, new_legs


def seed_allocation_for_banker_leg(banker_count: int) -> tuple[int, int]:
    """膽拖種子分配：優先填膽，總種子最多 3 球。"""

    banker_seed_count = min(max(int(banker_count), 1), 3)
    leg_seed_count = max(0, 3 - banker_seed_count)
    return banker_seed_count, leg_seed_count


def build_ball_image_html(nums: list[int]) -> str:
    """產生球圖 HTML。"""

    parts = []
    for num in nums:
        b64 = load_ball_image_base64(num)
        if b64:
            parts.append(
                f"<img src='data:image/png;base64,{b64}' "
                "style='width:34px;height:34px;object-fit:contain;margin-right:4px;'/>"
            )
        else:
            parts.append(f"<span style='font-weight:700;margin-right:6px;'>{num:02d}</span>")

    return "".join(parts)


def render_generated_numbers(nums: list[int]) -> None:
    """顯示已發球號碼。"""

    if not nums:
        return

    st.markdown(
        f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:2px;margin:3px 0 6px 0;'>{build_ball_image_html(nums)}</div>",
        unsafe_allow_html=True,
    )


def render_generated_numbers_inline(label: str, nums: list[int], empty_text: str = "未發球") -> None:
    """同一行顯示標籤與球圖。"""

    if nums:
        body = build_ball_image_html(nums)
    else:
        body = f"<span style='color:#6b7280;font-size:0.9rem;'>{empty_text}</span>"

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0 4px 0;line-height:34px;">
            <span style="font-size:1.05rem;font-weight:700;line-height:34px;display:inline-flex;align-items:center;">{label}</span>
            <div style="display:flex;align-items:center;flex-wrap:wrap;gap:2px;min-height:34px;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_saved_notice() -> None:
    """在選號鍵盤下方顯示儲存提示。"""

    notice = st.session_state.get("custom_saved_notice", "")
    if not notice:
        return

    st.markdown(
        f"<h7 style='display:block;font-size:1rem;font-weight:800;color:#166534;margin:8px 0 6px 0;'>{notice}</h7>",
        unsafe_allow_html=True,
    )


def render_selected_and_generated_numbers(seeds: list[int], nums: list[int]) -> None:
    """把用戶種子球和系統補足號碼集中顯示。"""

    with st.container(border=True):
        render_generated_numbers_inline("選種子號：", seeds, empty_text="未選")
        render_generated_numbers_inline("投注：", nums)


def render_banker_leg_summary(seeds: list[int], bankers: list[int], legs: list[int]) -> None:
    """集中顯示種子、膽、配腳和膽拖投注號碼。"""

    combined_body = ""
    if bankers or legs:
        combined_body = (
            build_ball_image_html(bankers)
            + "<span style='font-weight:800;margin:0 6px;'>+</span>"
            + build_ball_image_html(legs)
        )

    with st.container(border=True):
        if combined_body:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0 4px 0;line-height:34px;">
                    <span style="font-size:1.05rem;font-weight:700;line-height:34px;display:inline-flex;align-items:center;">膽拖投注：</span>
                    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:2px;min-height:34px;">{combined_body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            render_generated_numbers_inline("膽拖投注：", [], empty_text="未選膽 / 配腳")


def render_custom_action_styles() -> None:
    """黃色操作按鈕樣式。"""

    st.markdown(
        """
        <style>
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stHorizontalBlock"] button,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div div[data-testid="stHorizontalBlock"] button,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stButton"] button {
            background: #facc15 !important;
            color: #111827 !important;
            border: 1px solid #eab308 !important;
            font-weight: 800 !important;
            border-radius: 8px !important;
        }
        .custom-action-a,
        .custom-action-b,
        .custom-action-c {
            display: none;
        }
        div[data-testid="column"]:has(.custom-action-a) div[data-testid="stButton"] button,
        div[data-testid="stColumn"]:has(.custom-action-a) div[data-testid="stButton"] button,
        div:has(> div[data-testid="stElementContainer"] .custom-action-a) div[data-testid="stButton"] button {
            background: #dbeafe !important;
            color: #1e3a8a !important;
            border-color: #93c5fd !important;
        }
        div[data-testid="column"]:has(.custom-action-b) div[data-testid="stButton"] button,
        div[data-testid="stColumn"]:has(.custom-action-b) div[data-testid="stButton"] button,
        div:has(> div[data-testid="stElementContainer"] .custom-action-b) div[data-testid="stButton"] button {
            background: #facc15 !important;
            color: #111827 !important;
            border-color: #eab308 !important;
        }
        div[data-testid="column"]:has(.custom-action-c) div[data-testid="stButton"] button,
        div[data-testid="stColumn"]:has(.custom-action-c) div[data-testid="stButton"] button,
        div:has(> div[data-testid="stElementContainer"] .custom-action-c) div[data-testid="stButton"] button {
            background: #dc2626 !important;
            color: #ffffff !important;
            border-color: #b91c1c !important;
        }
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stHorizontalBlock"] button:hover:enabled,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div div[data-testid="stHorizontalBlock"] button:hover:enabled,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stButton"] button:hover:enabled {
            background: #eab308 !important;
            color: #111827 !important;
            border-color: #ca8a04 !important;
        }
        div[data-testid="column"]:has(.custom-action-a) div[data-testid="stButton"] button:hover:enabled,
        div[data-testid="stColumn"]:has(.custom-action-a) div[data-testid="stButton"] button:hover:enabled,
        div:has(> div[data-testid="stElementContainer"] .custom-action-a) div[data-testid="stButton"] button:hover:enabled {
            background: #bfdbfe !important;
            color: #1e3a8a !important;
            border-color: #60a5fa !important;
        }
        div[data-testid="column"]:has(.custom-action-b) div[data-testid="stButton"] button:hover:enabled,
        div[data-testid="stColumn"]:has(.custom-action-b) div[data-testid="stButton"] button:hover:enabled,
        div:has(> div[data-testid="stElementContainer"] .custom-action-b) div[data-testid="stButton"] button:hover:enabled {
            background: #eab308 !important;
            color: #111827 !important;
            border-color: #ca8a04 !important;
        }
        div[data-testid="column"]:has(.custom-action-c) div[data-testid="stButton"] button:hover:enabled,
        div[data-testid="stColumn"]:has(.custom-action-c) div[data-testid="stButton"] button:hover:enabled,
        div:has(> div[data-testid="stElementContainer"] .custom-action-c) div[data-testid="stButton"] button:hover:enabled {
            background: #b91c1c !important;
            color: #ffffff !important;
            border-color: #991b1b !important;
        }
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stHorizontalBlock"] button:disabled,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div div[data-testid="stHorizontalBlock"] button:disabled,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stButton"] button:disabled {
            background: #f3f4f6 !important;
            color: #9ca3af !important;
            border-color: #e5e7eb !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def save_custom_bet(
    email: str,
    bet_date: str,
    bet_type: str,
    nums: list[int],
    bet_unit: int,
    total_bets: int,
    total_cost: int,
    bankers: list[int] | None = None,
    legs: list[int] | None = None,
) -> bool:
    """儲存自定投注到會員投注紀錄。"""

    if bet_type == "單式 [6]":
        save_type = "六合彩單式"
    elif bet_type == "膽拖 [1-5]膽":
        save_type = "膽拖"
    else:
        save_type = "複式"

    if member_bet_exists(email, bet_date, "會員自定", save_type, nums):
        st.session_state["custom_saved_notice"] = "這筆自定投注已存在，沒有重複儲存。"
        return False

    add_member_bet(
        email=email,
        bet_date=bet_date,
        bet_source="會員自定",
        bet_type=save_type,
        numbers=nums,
        bankers=bankers or [],
        legs=legs or [],
        bet_unit=bet_unit,
        total_bets=total_bets,
        total_cost=total_cost,
        notes="會員自定投注",
    )
    return True


def clear_standard_custom_bet() -> None:
    st.session_state["custom_seed_numbers"] = []
    st.session_state["custom_picker_seed_numbers"] = []
    st.session_state["custom_seed_reset_token"] += 1
    reset_generated_numbers()


def generate_standard_custom_bet(seeds: list[int], bet_size: int, signature: tuple) -> None:
    st.session_state["custom_saved_notice"] = ""
    st.session_state["custom_save_locked"] = False
    st.session_state["custom_generated_numbers"] = generate_numbers(seeds, bet_size)
    st.session_state["custom_generated_signature"] = signature


def save_standard_custom_bet(
    email: str,
    bet_date: str,
    bet_type: str,
    nums: list[int],
    bet_unit: int,
    total_bets: int,
    total_cost: int,
) -> None:
    saved = save_custom_bet(
        email=email,
        bet_date=bet_date,
        bet_type=bet_type,
        nums=nums,
        bet_unit=bet_unit,
        total_bets=total_bets,
        total_cost=total_cost,
    )
    if saved:
        st.session_state["custom_direct_numbers"] = []
        st.session_state["custom_picker_seed_numbers"] = []
        st.session_state["custom_seed_reset_token"] += 1
        st.session_state["custom_saved_notice"] = "存檔成功，已加入會員投注紀錄。"
        st.session_state["custom_save_locked"] = False


def clear_banker_leg_custom_bet() -> None:
    st.session_state["custom_seed_numbers"] = []
    st.session_state["custom_picker_seed_numbers"] = []
    st.session_state["custom_seed_reset_token"] += 1
    reset_banker_leg_numbers()


def fill_banker_leg_custom_bet(
    bankers: list[int],
    legs: list[int],
    banker_count: int,
    leg_count: int,
) -> None:
    st.session_state["custom_saved_notice"] = ""
    st.session_state["custom_save_locked"] = False
    new_bankers, new_legs = fill_banker_leg_numbers(
        bankers,
        legs,
        banker_count=banker_count,
        leg_count=leg_count,
    )
    st.session_state["custom_banker_numbers"] = new_bankers
    st.session_state["custom_leg_numbers"] = new_legs
    st.session_state["custom_banker_reset_token"] += 1
    st.session_state["custom_leg_reset_token"] += 1


def save_banker_leg_custom_bet(
    email: str,
    bet_date: str,
    combined_nums: list[int],
    bankers: list[int],
    legs: list[int],
    bet_unit: int,
    total_bets: int,
    total_cost: int,
) -> None:
    saved = save_custom_bet(
        email=email,
        bet_date=bet_date,
        bet_type="膽拖 [1-5]膽",
        nums=combined_nums,
        bankers=bankers,
        legs=legs,
        bet_unit=bet_unit,
        total_bets=total_bets,
        total_cost=total_cost,
    )
    if saved:
        st.session_state["custom_banker_numbers"] = []
        st.session_state["custom_leg_numbers"] = []
        st.session_state["custom_saved_notice"] = "存檔成功，已加入會員投注紀錄。"
        st.session_state["custom_save_locked"] = False


def render_current_pending_bets(email: str, bet_date: str) -> None:
    """顯示目前開獎日、尚未開獎的會員投注紀錄及合計。"""
    if not bet_date:
        return
    pending_rows = [
        row
        for row in list_member_bets(email)
        if row.get("bet_date") == bet_date and row.get("result_status") in (None, "", "pending", "未開獎")
    ]
    if not pending_rows:
        return

    total_bets = sum(int(row.get("total_bets") or 1) for row in pending_rows)
    total_cost = sum(int(row.get("total_cost") or 0) for row in pending_rows)
    table_rows = []
    for index, row in enumerate(pending_rows, start=1):
        bankers = json.loads(row.get("bankers") or "[]")
        legs = json.loads(row.get("legs") or "[]")
        numbers = json.loads(row.get("numbers") or "[]")
        if bankers or legs:
            number_text = ",".join(map(str, bankers)) + " + " + ",".join(map(str, legs))
        else:
            number_text = ",".join(map(str, numbers))
        table_rows.append(
            {
                "序號": index,
                "來源": row.get("bet_source", ""),
                "投注種類": row.get("bet_type", ""),
                "號碼": number_text,
                "每注$": int(row.get("bet_unit") or 0),
                "注數": int(row.get("total_bets") or 1),
                "金額": int(row.get("total_cost") or 0),
            }
        )
    st.markdown("### 本期未開獎投注紀錄")
    st.dataframe(table_rows, hide_index=True, width="stretch")
    st.markdown(f"**最新開獎日：** {bet_date}，共 **{total_bets} 注**，總投注金額 **${total_cost}**。")


def render_banker_leg_bet_page(
    email: str,
    bet_date: str,
    bet_unit: int,
    banker_count: int,
    leg_count: int,
) -> None:
    """會員自定膽拖投注。"""

    bankers = sorted(int(num) for num in st.session_state.get("custom_banker_numbers", []))[:banker_count]
    legs = sorted(
        int(num)
        for num in st.session_state.get("custom_leg_numbers", [])
        if int(num) not in bankers
    )[:leg_count]
    seeds = sorted((bankers + legs)[:3])
    st.session_state["custom_seed_numbers"] = seeds
    if bankers != st.session_state.get("custom_banker_numbers", []):
        st.session_state["custom_banker_numbers"] = bankers
    if legs != st.session_state.get("custom_leg_numbers", []):
        st.session_state["custom_leg_numbers"] = legs

    has_selection = bool(bankers or legs)
    selections_complete = len(bankers) == banker_count and len(legs) == leg_count
    total_bets = math.comb(leg_count, 6 - banker_count)
    total_cost = total_bets * bet_unit
    combined_nums = sorted(bankers + legs)

    render_banker_leg_summary(seeds, bankers, legs)
    st.markdown(
        f"""
        <h7 style="display:block;font-size:0.95rem;font-weight:700;line-height:1.45;margin:2px 0 4px 0;color:#374151;">
            膽拖投注：{banker_count} 膽 + {leg_count} 腳｜每注 ${bet_unit}<br>
            注數：{total_bets:,}注｜投注金額：${total_cost:,}
            <div style="border-top:1px solid #d1d5db;margin:7px 0 6px 0;"></div>
            1， 用戶直接用 1-49 按鈕選擇膽號及配腳<br>
            2，已選膽號會在配腳選號中停用，已選配腳亦不能再選作膽號
        </h7>
        """,
        unsafe_allow_html=True,
    )
    render_banker_leg_picker(bankers, legs, banker_count, leg_count)
    render_saved_notice()

    st.markdown('<span class="custom-action-marker"></span>', unsafe_allow_html=True)
    clear_col, save_col = st.columns(2)
    clear_col.markdown('<span class="custom-action-a"></span>', unsafe_allow_html=True)
    clear_col.button(
        "重設種子選號",
        key="clear_banker_leg_seed_numbers",
        disabled=not has_selection,
        use_container_width=True,
        on_click=clear_banker_leg_custom_bet,
    )

    can_save = (
        bool(bet_date)
        and selections_complete
        and total_bets > 0
        and not st.session_state.get("custom_save_locked", False)
    )
    save_col.markdown('<span class="custom-action-c"></span>', unsafe_allow_html=True)
    save_col.button(
        "儲存至會員投注紀錄",
        key="save_banker_leg_bet",
        disabled=not can_save,
        use_container_width=True,
        on_click=save_banker_leg_custom_bet,
        args=(email, bet_date, combined_nums, bankers, legs, bet_unit, total_bets, total_cost),
    )
    render_current_pending_bets(email, bet_date)


def render_custom_bet_page(email: str) -> None:
    """會員自定投注頁。"""

    init_custom_bet_state()
    render_custom_action_styles()
    st.subheader("A. 會員自定種類投注")

    bet_date = load_next_draw_date()
    if bet_date:
        st.caption(f"投注日期：{format_date_with_weekday(bet_date)}")
    else:
        st.warning("找不到下期投注日期，暫時不能儲存投注。")

    bet_type, bet_size, bet_unit = get_bet_config()
    if bet_type == "膽拖 [1-5]膽":
        banker_count = int(
            st.selectbox(
                "膽",
                list(range(1, 6)),
                key="custom_banker_count",
                on_change=reset_banker_leg_numbers,
            )
        )
        min_leg_count = 7 - banker_count
        max_leg_count = 49 - banker_count
        if st.session_state.get("custom_last_banker_count") != banker_count:
            st.session_state["custom_last_banker_count"] = banker_count
            st.session_state[f"custom_leg_count_{banker_count}"] = min_leg_count
        leg_count = int(
            st.selectbox(
                "腳",
                list(range(min_leg_count, max_leg_count + 1)),
                key=f"custom_leg_count_{banker_count}",
                on_change=reset_banker_leg_numbers,
            )
        )
    else:
        banker_count = 0
        leg_count = 0
    render_abcd_pool_card()
    if bet_type == "膽拖 [1-5]膽":
        render_banker_leg_bet_page(email, bet_date, bet_unit, banker_count, leg_count)
        return

    total_bets = calculate_total_bets(bet_type, bet_size)
    total_cost = total_bets * bet_unit

    nums = render_direct_bet_picker(bet_size)

    if bet_type == "複式 [7-15]":
        st.markdown(
            f"""
            <h7 style="display:block;font-size:0.95rem;font-weight:700;line-height:1.45;margin:2px 0 4px 0;color:#374151;">
                複式投注：{bet_size} 球 每注 $ {bet_unit}<br>
                注數：{total_bets:,} 注｜投注金額：${total_cost:,}
            </h7>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <h7 style="display:block;font-size:0.95rem;font-weight:700;line-height:1.45;margin:2px 0 4px 0;color:#374151;">
                單式投注注數：{total_bets:,} 注｜投注金額：${total_cost:,}
            </h7>
            """,
            unsafe_allow_html=True,
        )

    signature = (bet_type, bet_size, bet_unit, tuple(nums), datetime.now().date().isoformat())

    if len(nums) < bet_size:
        st.info(f"請用 1-49 按鈕選擇 {bet_size} 球。")
    render_saved_notice()
    st.markdown('<span class="custom-action-marker"></span>', unsafe_allow_html=True)
    col1, col3 = st.columns(2)
    col1.markdown('<span class="custom-action-a"></span>', unsafe_allow_html=True)
    col1.button(
        "清除已選號碼",
        key="clear_custom_seed_numbers",
        disabled=not bool(nums),
        use_container_width=True,
        on_click=clear_direct_numbers,
    )

    can_save = (
        len(nums) == bet_size
        and bool(bet_date)
        and not st.session_state.get("custom_save_locked", False)
    )
    col3.markdown('<span class="custom-action-c"></span>', unsafe_allow_html=True)
    col3.button(
        "儲存至會員投注紀錄",
        key="save_custom_bet",
        disabled=not can_save,
        use_container_width=True,
        on_click=save_standard_custom_bet,
        args=(email, bet_date, bet_type, nums, bet_unit, total_bets, total_cost),
    )
    render_current_pending_bets(email, bet_date)
