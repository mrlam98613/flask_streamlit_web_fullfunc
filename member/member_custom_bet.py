from __future__ import annotations

import base64
import csv
import math
import random
from datetime import datetime
from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import add_member_bet, member_bet_exists  # noqa: E402
from custom_components.number_picker import number_picker  # noqa: E402


BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"
PRIZE_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M3_lotto_prize_results.csv"
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
    st.session_state.setdefault("custom_generated_numbers", [])
    st.session_state.setdefault("custom_generated_signature", None)
    st.session_state.setdefault("custom_seed_reset_token", 0)
    st.session_state.setdefault("custom_banker_numbers", [])
    st.session_state.setdefault("custom_leg_numbers", [])
    st.session_state.setdefault("custom_banker_reset_token", 0)
    st.session_state.setdefault("custom_leg_reset_token", 0)


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


def reset_generated_numbers() -> None:
    """種子或投注設定改變後，清空舊發球結果。"""

    st.session_state["custom_generated_numbers"] = []
    st.session_state["custom_generated_signature"] = None


def reset_banker_leg_numbers() -> None:
    """清空膽拖選號。"""

    st.session_state["custom_banker_numbers"] = []
    st.session_state["custom_leg_numbers"] = []
    st.session_state["custom_banker_reset_token"] += 1
    st.session_state["custom_leg_reset_token"] += 1


def reset_custom_bet_outputs() -> None:
    """投注種類或金額改變時，清空已產生投注。"""

    reset_generated_numbers()
    reset_banker_leg_numbers()


def render_seed_picker(seeds: list[int], nums: list[int]) -> None:
    """顯示 1-49 球號，最多可選 3 個種子球。"""

    render_selected_and_generated_numbers(seeds, nums)
    render_seed_only_picker(seeds)


def render_seed_only_picker(seeds: list[int]) -> None:
    """只顯示種子選號盤。"""

    selected = number_picker(
        selected=seeds,
        max_select=3,
        reset_token=st.session_state["custom_seed_reset_token"],
        key=f"custom_seed_number_picker_{st.session_state['custom_seed_reset_token']}",
    )
    selected = sorted(int(num) for num in selected)
    if selected != seeds:
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

    pick_mode = st.radio(
        "選號模式",
        ["膽", "配腳"],
        horizontal=True,
        key="custom_banker_leg_pick_mode",
    )

    if pick_mode == "膽":
        selected = number_picker(
            selected=bankers,
            max_select=banker_count,
            reset_token=st.session_state["custom_banker_reset_token"],
            key=f"custom_banker_leg_picker_banker_{st.session_state['custom_banker_reset_token']}_{banker_count}",
        )
        selected_bankers = sorted(int(num) for num in selected)
        if selected_bankers != bankers:
            st.session_state["custom_banker_numbers"] = selected_bankers
            st.session_state["custom_leg_numbers"] = [num for num in legs if num not in selected_bankers]
            st.rerun()
    else:
        selected = number_picker(
            selected=legs,
            max_select=leg_count,
            reset_token=st.session_state["custom_leg_reset_token"],
            key=f"custom_banker_leg_picker_leg_{st.session_state['custom_leg_reset_token']}_{leg_count}",
        )
        selected_legs = sorted(int(num) for num in selected if int(num) not in bankers)
        if selected_legs != legs:
            st.session_state["custom_leg_numbers"] = selected_legs
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


def render_selected_and_generated_numbers(seeds: list[int], nums: list[int]) -> None:
    """把用戶種子球和系統補足號碼集中顯示。"""

    with st.container(border=True):
        render_generated_numbers_inline("選種子號 最多 1-3 球：", seeds, empty_text="未選")
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
        render_generated_numbers_inline("選種子號 最多 1-3 球：", seeds, empty_text="未選")
        render_generated_numbers_inline("選膽：", bankers, empty_text="未選")
        render_generated_numbers_inline("配腳：", legs, empty_text="未選")
        if combined_body:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0 4px 0;line-height:34px;">
                    <span style="font-size:1.05rem;font-weight:700;line-height:34px;display:inline-flex;align-items:center;">投注：</span>
                    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:2px;min-height:34px;">{combined_body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            render_generated_numbers_inline("投注：", [], empty_text="未選膽/配腳")


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
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stHorizontalBlock"] button:hover:enabled,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div div[data-testid="stHorizontalBlock"] button:hover:enabled,
        div[data-testid="stElementContainer"]:has(.custom-action-marker) + div[data-testid="stButton"] button:hover:enabled {
            background: #eab308 !important;
            color: #111827 !important;
            border-color: #ca8a04 !important;
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
        st.warning("這筆自定投注已存在：相同日期、來源、種類及號碼不可重複投注。")
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
    st.success("已儲存至會員投注紀錄。")
    return True


def render_banker_leg_bet_page(email: str, bet_date: str, bet_unit: int) -> None:
    """會員自定膽拖投注。"""

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
    leg_count = int(
        st.selectbox(
            "配腳",
            list(range(min_leg_count, max_leg_count + 1)),
            key="custom_leg_count",
            on_change=reset_banker_leg_numbers,
        )
    )

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

    selections_complete = len(bankers) == banker_count and len(legs) == leg_count
    total_bets = math.comb(leg_count, 6 - banker_count)
    total_cost = total_bets * bet_unit
    combined_nums = sorted(bankers + legs)

    st.markdown(
        f"**每注 ${bet_unit} ｜投注注數：{total_bets:,} 注｜投注金額：${total_cost:,}**"
    )
    if not selections_complete:
        st.caption(f"膽拖：{banker_count} 膽 + {leg_count} 腳｜已選膽 {len(bankers)}/{banker_count}｜配腳 {len(legs)}/{leg_count}")

    render_banker_leg_summary(seeds, bankers, legs)
    st.markdown("---")
    render_banker_leg_picker(bankers, legs, banker_count, leg_count)

    st.markdown('<span class="custom-action-marker"></span>', unsafe_allow_html=True)
    clear_col, fill_col, save_col = st.columns(3)
    if clear_col.button("清除種子球號", key="clear_banker_leg_seed_numbers", use_container_width=True):
        st.session_state["custom_seed_numbers"] = []
        st.session_state["custom_seed_reset_token"] += 1
        reset_banker_leg_numbers()
        st.rerun()

    if fill_col.button("發球補足", key="custom_generate_banker_leg_numbers", use_container_width=True):
        new_bankers, new_legs = generate_banker_leg_numbers(
            st.session_state.get("custom_seed_numbers", []),
            banker_count=banker_count,
            leg_count=leg_count,
        )
        st.session_state["custom_banker_numbers"] = new_bankers
        st.session_state["custom_leg_numbers"] = new_legs
        st.session_state["custom_banker_reset_token"] += 1
        st.session_state["custom_leg_reset_token"] += 1
        st.rerun()

    can_save = bool(bet_date) and selections_complete and total_bets > 0
    if save_col.button("存會員投注紀錄", key="save_banker_leg_bet", disabled=not can_save, use_container_width=True):
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
            st.session_state["custom_seed_numbers"] = []
            st.session_state["custom_seed_reset_token"] += 1
            reset_banker_leg_numbers()
            st.rerun()

    if not selections_complete:
        st.info(
            f"請完成選號：膽 {len(bankers)}/{banker_count}，配腳 {len(legs)}/{leg_count}。"
        )


def render_custom_bet_page(email: str) -> None:
    """會員自定投注頁。"""

    init_custom_bet_state()
    render_custom_action_styles()
    st.subheader("B. 會員自定種類投注")

    bet_date = load_next_draw_date()
    if bet_date:
        st.caption(f"投注日期：{format_date_with_weekday(bet_date)}")
    else:
        st.warning("找不到下期投注日期，暫時不能儲存投注。")

    bet_type, bet_size, bet_unit = get_bet_config()
    if bet_type == "膽拖 [1-5]膽":
        render_banker_leg_bet_page(email, bet_date, bet_unit)
        return

    total_bets = calculate_total_bets(bet_type, bet_size)
    total_cost = total_bets * bet_unit
    st.markdown(f"**投注注數：{total_bets:,} 注｜投注金額：${total_cost:,}**")

    seeds = st.session_state["custom_seed_numbers"]
    nums = st.session_state.get("custom_generated_numbers", [])
    render_seed_picker(seeds, nums)

    if not seeds:
        st.info("請先選擇 1 至 3 個種子球。")
        st.markdown('<span class="custom-action-marker"></span>', unsafe_allow_html=True)
        if st.button("清除種子號", key="clear_custom_seed_numbers_empty", disabled=True):
            pass
        return

    signature = (bet_type, bet_size, bet_unit, tuple(sorted(seeds)), datetime.now().date().isoformat())

    st.markdown('<span class="custom-action-marker"></span>', unsafe_allow_html=True)
    if st.button("清除種子號", key="clear_custom_seed_numbers", use_container_width=True):
        st.session_state["custom_seed_numbers"] = []
        st.session_state["custom_seed_reset_token"] += 1
        reset_generated_numbers()
        st.rerun()

    st.markdown("---")
    st.markdown('<span class="custom-action-marker"></span>', unsafe_allow_html=True)
    col2, col3 = st.columns(2)
    if col2.button("系統補足 發球", key="custom_generate_numbers", use_container_width=True):
        st.session_state["custom_generated_numbers"] = generate_numbers(seeds, bet_size)
        st.session_state["custom_generated_signature"] = signature
        st.rerun()

    if col3.button("儲存至投注紀錄", key="save_custom_bet", disabled=(not bool(nums) or not bool(bet_date)), use_container_width=True):
        if nums:
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
                st.session_state["custom_seed_numbers"] = []
                st.session_state["custom_generated_numbers"] = []
                st.session_state["custom_generated_signature"] = None
                st.session_state["custom_seed_reset_token"] += 1
                st.rerun()
