from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BET_FILE = PROJECT_ROOT / "A_new_bet_data_folder" / "my_bet_records.csv"
HISTORY_FILE = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M2_last_upgrade_lotto_data.csv"
RESULT_FILE = PROJECT_ROOT / "A_new_bet_data_folder" / "my_bet_check_result.csv"
LOTTO_UNIT_AMOUNT = 10  # 六合彩單式每注投注金額 HKD10

PRIZE_TABLE = {
    6.0: 10_000_000,
    5.5: 1_100_000,
    5.0: 300_000,
    4.5: 9_600,
    4.0: 640,
    3.5: 320,
    3.0: 40,
}

RED_BALLS = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
BLUE_BALLS = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
GREEN_BALLS = {5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49}

COLOR_STYLE = {
    "red": {"bg": "#FDECEC", "text": "#A11A1A", "border": "#F4B9B9"},
    "blue": {"bg": "#EAF2FF", "text": "#1E4E9D", "border": "#BFD4F7"},
    "green": {"bg": "#EAF8EF", "text": "#1D6E3A", "border": "#BFE7CC"},
    "gray": {"bg": "#F4F4F5", "text": "#555555", "border": "#D9D9DB"},
}


@st.cache_data(show_spinner=False)
def load_data():
    if not BET_FILE.exists() or not HISTORY_FILE.exists():
        return None, None

    bets = pd.read_csv(BET_FILE)
    history = pd.read_csv(HISTORY_FILE)
    history = history.dropna(subset=["ndate"]).copy()
    history["ndate"] = history["ndate"].astype(str)
    return bets, history


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_ball_color(num: int) -> str:
    if num in RED_BALLS:
        return "red"
    if num in BLUE_BALLS:
        return "blue"
    if num in GREEN_BALLS:
        return "green"
    return "gray"


def render_ball(num: int, hit: bool = False) -> str:
    key = get_ball_color(num)
    color = COLOR_STYLE[key]
    ring = "box-shadow:0 0 0 2px #FDBA74 inset;" if hit else ""
    return (
        f"<span style='display:inline-flex;align-items:center;justify-content:center;"
        f"width:24px;height:24px;border-radius:50%;margin-right:4px;"
        f"font-size:12px;font-weight:700;background:{color['bg']};"
        f"color:{color['text']};border:1px solid {color['border']};{ring}'>"
        f"{num:02d}</span>"
    )


def render_ball_row(nums, highlight_nums=None) -> str:
    highlight_set = set(highlight_nums) if isinstance(highlight_nums, list) else set()
    if not isinstance(nums, list) or not nums:
        return "<span style='color:#777;'>-</span>"

    balls_html = "".join(render_ball(int(n), int(n) in highlight_set) for n in nums)
    return balls_html


def render_special_ball(special_text) -> str:
    if special_text == "-":
        return "<span style='color:#777;'>-</span>"

    try:
        special_num = int(special_text)
        return render_ball(special_num, True)
    except ValueError:
        return "<span style='color:#777;'>-</span>"


def render_prize_cell(prize: int, score: float) -> str:
    prize_text = f"${int(prize):,}"

    # 中獎條件達到 3.0 或以上，以琥珀金底色強調。
    if score >= 3.0 and prize > 0:
        return (
            "<span style='display:inline-block;padding:2px 8px;border-radius:8px;"
            "background:#FFF4DB;color:#9A5A00;border:1px solid #F3D39A;font-weight:700;'>"
            f"{prize_text}</span>"
        )

    return f"<span>{prize_text}</span>"


def render_page_styles():
    """統一此頁字級，採手機優先的可讀尺寸。"""
    st.markdown(
        """
        <style>
        .vp-summary-wrap{max-width:520px;margin:0 auto 16px auto;text-align:left;}
        .vp-summary-panel{border:1px solid #e7e7e7;border-radius:12px;padding:14px 16px;background:#fff;}
        .vp-summary-title{font-size:16px;line-height:1.5;color:#222;font-weight:700;margin:0 0 10px 0;}
        .vp-summary-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f2f2f2;}
        .vp-summary-row:last-child{border-bottom:none;}
        .vp-summary-label{font-size:14px;line-height:1.5;color:#666;}
        .vp-summary-value{font-size:15px;line-height:1.5;color:#222;font-weight:700;}
        .vp-summary-value--profit{color:#0f766e;}
        .vp-summary-value--loss{color:#b42318;}
        .vp-page-note{font-size:14px;line-height:1.5;color:#555;margin:0 0 8px 0;}
        .vp-section-title{font-size:16px;line-height:1.5;font-weight:700;color:#222;margin:0 0 8px 0;}
        .vp-card{border:1px solid #e7e7e7;border-radius:10px;padding:10px 12px;margin-bottom:10px;background:#fff;}
        .vp-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
        .vp-no{font-size:14px;line-height:1.5;font-weight:600;color:#222;}
        .vp-date{font-size:14px;line-height:1.5;color:#666;white-space:nowrap;}
        .vp-row{display:flex;align-items:flex-start;gap:8px;margin:4px 0;}
        .vp-label{min-width:58px;font-size:14px;line-height:24px;color:#666;}
        .vp-balls{display:flex;align-items:center;flex-wrap:nowrap;overflow-x:auto;}
        .vp-foot{display:flex;flex-wrap:wrap;gap:12px;margin-top:8px;padding-top:8px;border-top:1px solid #f2f2f2;}
        .vp-kv{display:flex;align-items:center;gap:6px;font-size:14px;line-height:1.5;color:#222;}
        .vp-k{font-size:14px;line-height:1.5;color:#666;}
        .vp-download-wrap{max-width:520px;margin:16px auto 0 auto;text-align:center;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_detail_cards(visual_df: pd.DataFrame):
    """以響應式卡片顯示每注明細，兼容手機與桌面版。"""
    for _, row in visual_df.iterrows():
        bet_nums = row["投注號碼"] if isinstance(row["投注號碼"], list) else []
        hit_nums = row["命中號碼"] if isinstance(row["命中號碼"], list) else []
        special_text = row["特別號"]
        score = row["分數"]
        score_text = str(int(score)) if isinstance(score, float) and score.is_integer() else str(score)
        prize_html = render_prize_cell(int(row["獎金"]), float(score))

        hit_html = render_ball_row(hit_nums, hit_nums) if hit_nums else "<span style='color:#777;'>-</span>"

        st.markdown(
            f"""
            <div class="vp-card">
                <div class="vp-head">
                    <span class="vp-no">第 {int(row['注次'])} 注，投注日期 {row['投注日期']}</span>
                </div>
                <div class="vp-row">
                    <span class="vp-label">投注號碼</span>
                    <div class="vp-balls">{render_ball_row(bet_nums, hit_nums)}</div>
                </div>
                <div class="vp-row">
                    <span class="vp-label">中正號</span>
                    <div class="vp-balls">{hit_html}</div>
                </div>
                <div class="vp-foot">
                    <div class="vp-kv"><span class="vp-k">中特號</span><span>{render_special_ball(special_text)}</span></div>
                    <div class="vp-kv"><span class="vp-k">總中球數</span><span>{score_text}</span></div>
                    <div class="vp-kv"><span class="vp-k">獎金</span><span>{prize_html}</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_summary_metrics(summary: dict):
    """以較穩定的原生區塊顯示損益摘要。"""
    metrics = [
        ("投注注數", f"{summary['total_bets']:,}"),
        ("中獎注數", f"{summary['total_wins']:,}"),
        ("投注總額", f"${summary['total_cost']:,}"),
        ("中獎獎金", f"${summary['total_prize']:,}"),
        ("損益", f"${summary['profit_loss']:,}"),
    ]

    st.markdown('<div class="vp-summary-wrap">', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            '<div style="text-align:left;font-size:16px;font-weight:700;margin-bottom:8px;">中獎損益</div>',
            unsafe_allow_html=True,
        )

        for label, value in metrics:
            value_style = "color:#222;font-weight:700;"
            if label == "損益":
                value_style = "color:#0f766e;font-weight:700;" if summary["profit_loss"] >= 0 else "color:#b42318;font-weight:700;"

            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f2f2f2;text-align:left;">
                    <span style="color:#666;font-size:14px;">{label}</span>
                    <span style="{value_style}">{value}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)


def analyze_bets(bets: pd.DataFrame, history: pd.DataFrame):
    history_map = history.set_index("ndate")

    total_bets = 0
    total_wins = 0
    total_prize = 0
    no_result_dates = set()

    detail_rows = []
    export_rows = []

    for idx, row in bets.iterrows():
        total_bets += 1
        bet_date = str(row.get("bet_date", "")).strip()
        bet_nums = [_to_int(row.get(f"N{i}")) for i in range(1, 7)]

        if bet_date not in history_map.index:
            no_result_dates.add(bet_date)
            detail_rows.append(
                {
                    "注次": idx + 1,
                    "投注日期": f"{bet_date} ⏳ 尚未開獎",
                    "投注號碼": bet_nums,
                    "命中號碼": [],
                    "特別號": "-",
                    "分數": 0.0,
                    "獎金": 0,
                    "狀態": "尚未開獎",
                }
            )
            export_rows.append([bet_date] + ["未開獎"] * 6)
            continue

        draw = history_map.loc[bet_date]
        if isinstance(draw, pd.DataFrame):
            draw = draw.iloc[0]

        win_nums = [_to_int(draw.get(f"N{i}")) for i in range(1, 7)]
        special = _to_int(draw.get("N7"))

        hit = sorted(set(bet_nums) & set(win_nums))
        special_hit = special in bet_nums

        # 顯示規則：只要中特號，總中球數在中正號上加 0.5。
        hit_score = len(hit) + 0.5 if special_hit else float(len(hit))

        prize = PRIZE_TABLE.get(hit_score, 0)
        if prize > 0:
            total_wins += 1
            total_prize += prize

        status = "未中獎"
        if prize > 0:
            status = "中獎"
        elif hit or special_hit:
            status = "有命中號碼"

        detail_rows.append(
            {
                "注次": idx + 1,
                "投注日期": bet_date,
                "投注號碼": bet_nums,
                "命中號碼": hit,
                "特別號": str(special) if special_hit else "-",
                "分數": hit_score,
                "獎金": prize,
                "狀態": status,
            }
        )

        hit_marks = [n if n in hit else 0 for n in bet_nums]
        export_rows.append([bet_date] + hit_marks)

    total_cost = total_bets * LOTTO_UNIT_AMOUNT

    summary = {
        "total_bets": total_bets,
        "total_wins": total_wins,
        "total_prize": total_prize,
        "total_cost": total_cost,
        "profit_loss": total_prize - total_cost,
    }

    details_df = pd.DataFrame(detail_rows)
    export_df = pd.DataFrame(export_rows, columns=["bet_date", "N1", "N2", "N3", "N4", "N5", "N6"])

    return summary, details_df, export_df, sorted(d for d in no_result_dates if d)


def render_check_lottery_page():
    render_page_styles()
    st.markdown(
        '<p class="vp-page-note">來對過往投注紀錄進行總損益分析。</p>',
        unsafe_allow_html=True,
    )

    if not BET_FILE.exists() or not HISTORY_FILE.exists():
        st.error("找不到核對所需檔案，請確認投注紀錄與開獎資料是否存在。")
        st.write(f"投注檔：{BET_FILE}")
        st.write(f"開獎檔：{HISTORY_FILE}")
        return

    bets, history = load_data()
    if bets is None or history is None or bets.empty:
        st.warning("投注資料為空，暫時無法核對。")
        return

    with st.spinner("正在核對投注紀錄..."):
        summary, details_df, export_df, no_result_dates = analyze_bets(bets, history)

    # ── 開獎資料版本提示 ──────────────────────────────
    latest_draw_date = history["ndate"].max() if not history.empty else "-"
    st.success(f"✅ 開獎資料已是最新：最後一期開獎日期為 {latest_draw_date}")

    if no_result_dates:
        pending_list = "、".join(sorted(no_result_dates))
        st.warning(f"⏳ 以下投注日期尚未開獎，等待結果中：{pending_list}")

    st.markdown("---")
    st.markdown('<div class="vp-section-title">每注核對明細</div>', unsafe_allow_html=True)

    st.markdown(
        '<p class="vp-page-note">彩色球號：紅 / 藍 / 綠（淺色小圓圈，命中號碼有內圈標示）</p>',
        unsafe_allow_html=True,
    )

    total_rows = int(len(details_df))
    st.markdown(
        f'<p class="vp-page-note">實際投注要核對資料總筆數：{total_rows:,} 筆</p>',
        unsafe_allow_html=True,
    )

    show_all_rows = st.checkbox("顯示全部", value=False)
    if show_all_rows:
        visual_df = details_df.copy()
    else:
        max_rows = max(1, total_rows)
        default_rows = min(10, max_rows) # 預設顯示前 10 筆，若總筆數不足則顯示全部
        show_rows = st.number_input(
            "視覺化明細顯示筆數",
            min_value=1,
            max_value=max_rows,
            value=default_rows,
            step=10,
        )
        visual_df = details_df.tail(int(show_rows)).copy()

    render_detail_cards(visual_df)

    st.markdown("---")
    render_summary_metrics(summary)

    export_df.to_csv(RESULT_FILE, index=False, encoding="utf-8-sig")

    st.markdown("---")
    st.markdown('<div class="vp-section-title">下載 CSV 紀錄</div>', unsafe_allow_html=True)
    st.markdown('<div class="vp-download-wrap">', unsafe_allow_html=True)
    st.download_button(
        label="下載核對結果 CSV",
        data=export_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name=RESULT_FILE.name,
        mime="text/csv",
    )
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    render_check_lottery_page()
