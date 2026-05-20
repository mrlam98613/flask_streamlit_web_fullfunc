import pandas as pd
from pathlib import Path
import os
import random
import datetime

import res_func_marksix_next_BetDate
import seed_lotto_strategy

current_dir = Path(__file__).resolve().parent
workspace_root = current_dir.parent
save_path      = current_dir / "bet_data" / "my_bet_records.csv"
win_save_path  = current_dir / "bet_data" / "my_win_results.csv"
next_save_path = current_dir / "bet_data" / "nextBetDraw_record.csv"

# ── 參數設定 ────────────────────────────────────────────────────
BACKTEST_LAST_DRAW  = 28   # 初始化模式：回測最近 N 期
BET_UNIT            = 10   # 每注金額（港元）

# ── RBG 策略參數 ────────────────────────────────────────────────
COLLECT_BALLS_BREAK = 11    # RBG 收集球數門檻（至少收集 N 球才停止增加窗口期）
DRAW_SAME_COLOR     = 3    # 同期同色球數條件（==N 個同色球時視為熱門）

PRIZE_TABLE = {
    6.0: 10000000,
    5.5: 1100000,
    5.0: 300000,
    4.5: 9600,
    4.0: 640,
    3.5: 320,
    3.0: 40,
}

PRIZE_LABELS = {
    6.0: '一獎  6 正號      ',
    5.5: '二獎  5 正 + 特別號',
    5.0: '三獎  5 正號      ',
    4.5: '四獎  4 正 + 特別號',
    4.0: '五獎  4 正號      ',
    3.5: '六獎  3 正 + 特別號',
    3.0: '七獎  3 正號      ',
}


# ══════════════════════════════════════════════════════════════════
#  共用輔助函式
# ══════════════════════════════════════════════════════════════════

def load_draw_data_func():
    """讀取歷史開獎資料（含特別號 N7）。"""
    df_ = pd.read_csv(workspace_root / "A_msk_lottery_data_folder" / "M2_last_upgrade_lotto_data.csv")
    return df_.iloc[:, [0, 1, 2, 3, 4, 5, 6, 7]]  # ndate, N1..N6, N7


def random_base_draw_func(n_balls=6, seed_val=None):
    """隨機生成一注。"""
    if seed_val is not None:
        random.seed(seed_val)
    return sorted(random.sample(range(1, 50), n_balls))


def build_next_bets_from_seed(sorted_matched, last_bet_vals, seed_base, anchor_date, df_all):
    """依中獎種子號 + 區間/RBG 策略生成下期投注。"""
    return seed_lotto_strategy.generate_next_bets_with_strategy(
        sorted_matched=sorted_matched,
        last_bet_vals=last_bet_vals,
        anchor_date=anchor_date,
        df_all=df_all,
        seed_base=seed_base,
        collect_balls_break=COLLECT_BALLS_BREAK,
        draw_same_color=DRAW_SAME_COLOR,
    )


def check_and_score(bet_vals, y_6balls, y_special):
    """核對單注，回傳 (matched_set, sp_hit, hit_score, prize)。"""
    matched = set(bet_vals) & set(y_6balls)
    sp_hit  = 1 if y_special in set(bet_vals) else 0
    hit_n   = len(matched)
    hit_score = float(hit_n) + 0.5 if sp_hit else float(hit_n)
    prize = PRIZE_TABLE.get(hit_score, 0)
    return matched, sp_hit, hit_score, prize


# ══════════════════════════════════════════════════════════════════
#  CSV 讀寫函式
# ══════════════════════════════════════════════════════════════════

def _ensure_dir(path):
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    

def append_bet_record_func(bet_date, bet_numbers_list):
    """追加投注記錄（同一 bet_date 先刪後寫，確保冪等）。"""
    if bet_numbers_list and not isinstance(bet_numbers_list[0], (list, tuple)):
        bet_numbers_list = [bet_numbers_list]
    rows = [{'bet_date': bet_date, 'N1': b[0], 'N2': b[1], 'N3': b[2],
             'N4': b[3], 'N5': b[4], 'N6': b[5]} for b in bet_numbers_list]
    _ensure_dir(save_path)
    if save_path.exists() and save_path.stat().st_size > 0:
        df = pd.read_csv(save_path)
        df = df[df['bet_date'] != bet_date]
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    else:
        df = pd.DataFrame(rows)
    df.to_csv(save_path, index=False)


def append_win_record_func(bet_date, win_numbers_list):
    """追加中獎記錄（同一 bet_date 先刪後寫）。"""
    if win_numbers_list and not isinstance(win_numbers_list[0], (list, tuple)):
        win_numbers_list = [win_numbers_list]
    rows = [{'bet_date': bet_date, 'N1': w[0], 'N2': w[1], 'N3': w[2],
             'N4': w[3], 'N5': w[4], 'N6': w[5]} for w in win_numbers_list]
    _ensure_dir(win_save_path)
    if win_save_path.exists() and win_save_path.stat().st_size > 0:
        df = pd.read_csv(win_save_path)
        df = df[df['bet_date'] != bet_date]
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    else:
        df = pd.DataFrame(rows)
    df.to_csv(win_save_path, index=False)


def write_next_pred_func(bet_date, bet_numbers_list):
    """覆寫下期預測（只保留最新一期）。"""
    if bet_numbers_list and not isinstance(bet_numbers_list[0], (list, tuple)):
        bet_numbers_list = [bet_numbers_list]
    rows = [{'bet_date': bet_date, 'N1': b[0], 'N2': b[1], 'N3': b[2],
             'N4': b[3], 'N5': b[4], 'N6': b[5]} for b in bet_numbers_list]
    _ensure_dir(next_save_path)
    pd.DataFrame(rows).to_csv(next_save_path, index=False)


def read_bet_for_date(y_date):
    """讀取指定日期的投注記錄，若無返回空 DataFrame。"""
    if save_path.exists() and save_path.stat().st_size > 0:
        df = pd.read_csv(save_path)
        return df[df['bet_date'] == y_date]
    return pd.DataFrame()


def read_next_pred_safe():
    """安全讀取下期預測；若檔案不存在/空檔/僅表頭/格式不完整，回傳空 DataFrame。"""
    if not next_save_path.exists() or next_save_path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        df = pd.read_csv(next_save_path)
    except Exception:
        return pd.DataFrame()

    if df.empty or 'bet_date' not in df.columns:
        return pd.DataFrame()

    # 只留有效 bet_date 列，避免清空後殘留空列造成 iloc 取值錯誤
    df = df[df['bet_date'].astype(str).str.strip() != '']
    if df.empty:
        return pd.DataFrame()
    return df


# ══════════════════════════════════════════════════════════════════
#  模式一：初始化回測
# ══════════════════════════════════════════════════════════════════

def _is_initialized():
    """判斷是否已完成初始化（兩個 CSV 均存在且非空）。"""
    return (save_path.exists() and save_path.stat().st_size > 0 and
            win_save_path.exists() and win_save_path.stat().st_size > 0)


def rebuild_next_prediction_from_history(df_all, valid_next_draw_date):
    """當 nextBetDraw_record 缺失時，依最近已核對期重建下期預測。"""
    if (not win_save_path.exists() or win_save_path.stat().st_size == 0 or
            not save_path.exists() or save_path.stat().st_size == 0):
        print('缺少歷史投注/中獎資料，無法自動重建下期預測。')
        return False

    df_win = pd.read_csv(win_save_path)
    if df_win.empty:
        print('中獎記錄為空，無法自動重建下期預測。')
        return False

    # 以最近已核對日期作為策略錨點（可讓參數修改立即影響新預測）
    last_settled_date = str(df_win['bet_date'].astype(str).max())
    win_rows = df_win[df_win['bet_date'].astype(str) == last_settled_date]

    all_matched = set()
    for _, row in win_rows.iterrows():
        vals = [int(x) for x in row.iloc[1:7].values.tolist()]
        all_matched |= {n for n in vals if n > 0}
    sorted_matched = sorted(all_matched)

    bet_record = read_bet_for_date(last_settled_date)
    if bet_record is not None and not bet_record.empty:
        last_bet_vals = [int(x) for x in bet_record.iloc[-1, 1:7].values.tolist()]
    else:
        last_bet_vals = random_base_draw_func(seed_val=int(datetime.datetime.now().timestamp()) % 100000)

    seed_base = int(datetime.datetime.now().timestamp()) % 100000
    next_bets = build_next_bets_from_seed(
        sorted_matched=sorted_matched,
        last_bet_vals=last_bet_vals,
        seed_base=seed_base,
        anchor_date=last_settled_date,
        df_all=df_all,
    )

    append_bet_record_func(valid_next_draw_date, next_bets)
    write_next_pred_func(valid_next_draw_date, next_bets)

    # ── 提取策略上下文以顯示詳細信息 ────────────────────────────────────
    ctx = seed_lotto_strategy.get_strategy_context(last_settled_date, collect_balls_break=COLLECT_BALLS_BREAK, draw_same_color=DRAW_SAME_COLOR)
    pred_interval = ctx.get("pred_interval", [])
    rbg_collect = ctx.get("rbg_collect", {})
    _w = rbg_collect.get(0, [None, None, None])

    print(f'\n' + '=' * 56)
    print(f'下期投注日期: {valid_next_draw_date}')
    print('下期預測投注號碼：')
    for i, b in enumerate(next_bets, 1):
        print(f'   {i}. {b}')
    print('-' * 56)
    print(f'上期種子號 ：{sorted_matched}')
    print(f'預測下期 N1..N6 區間號: {pred_interval}')
    print(f'RBG 窗口期： R={_w[0]}  B={_w[1]}  G={_w[2]}')
    print(f'/> R 集合球: {rbg_collect.get(1, [])}')
    print(f'/> B 集合球: {rbg_collect.get(2, [])}')
    print(f'/> G 集合球: {rbg_collect.get(3, [])}')
    print('=' * 56)
    return True


def run_backtest_init(df_all, valid_next_draw_date):
    """模式一：用最近 BACKTEST_LAST_DRAW 期做回測，建立初始 CSV。"""
    print('=' * 56)
    print(f'【初始化模式】bet_data/ 無資料，執行 {BACKTEST_LAST_DRAW} 期回測建立基礎資料')
    print('=' * 56)

    start_draw  = max(len(df_all) - BACKTEST_LAST_DRAW, 0)
    recent_draws = df_all.iloc[start_draw:].reset_index(drop=True)

    if recent_draws.empty:
        print('沒有可回測的開獎資料。')
        return

    # 清空舊檔，確保全新開始
    for _p in [save_path, win_save_path, next_save_path]:
        if _p.exists():
            _p.unlink()

    # 第一期：隨機產生 1 注作為起始投注
    first_date = str(recent_draws.iloc[0, 0])
    base_bet = random_base_draw_func(seed_val=start_draw)
    append_bet_record_func(first_date, [base_bet])

    hit_counter = {k: 0 for k in PRIZE_TABLE}
    total_bets  = 0
    total_prize = 0

    for idx, row in recent_draws.iterrows():
        x_data   = row.values
        y_date   = str(x_data[0])
        y_nlist  = [int(x) for x in x_data[1:8]]
        y_6balls = y_nlist[:6]
        y_special = y_nlist[6]
        print(f'/> {y_date} 真實開獎: {y_6balls} + 特[{y_special}]')

        next_draw_date = None
        if idx + 1 < len(recent_draws):
            next_draw_date = str(recent_draws.iloc[idx + 1, 0])

        # 讀取本期投注記錄
        bet_record = read_bet_for_date(y_date)
        if bet_record is None or bet_record.empty:
            print(f'  [{y_date}] 無投注記錄，重新隨機開局。')
            base_bet = random_base_draw_func(seed_val=start_draw + idx)
            append_bet_record_func(y_date, [base_bet])
            bet_record = read_bet_for_date(y_date)

        all_matched = set()
        win_rows    = []
        last_bet_vals = None

        for _, bet_row in bet_record.iterrows():
            total_bets += 1
            bet_vals = [int(x) for x in bet_row.iloc[1:7].values.tolist()]
            last_bet_vals = bet_vals
            matched, sp_hit, hit_score, prize = check_and_score(bet_vals, y_6balls, y_special)

            if prize > 0:
                hit_counter[hit_score] += 1
                total_prize += prize

            all_matched |= matched
            win_result = [n if n in matched else 0 for n in bet_vals]
            win_rows.append(win_result)

            sp_tag = f' + 特[{y_special}]✨' if sp_hit else ''
            if prize > 0:
                print(f'   投注: {sorted(bet_vals)} -> 中 {sorted(matched)}{sp_tag} 命中={hit_score} 派彩 ${prize:,} 🎉')
            elif matched or sp_hit:
                print(f'   投注: {sorted(bet_vals)} -> 中 {sorted(matched)}{sp_tag} 命中={hit_score} ✅')
            else:
                print(f'   投注: {sorted(bet_vals)} 未中獎 ❌')

        print('-' * 50)
        append_win_record_func(y_date, win_rows)

        sorted_matched = sorted(all_matched)
        if sorted_matched:
            print(f'  種子號: {sorted_matched} ({len(sorted_matched)} 個)')

        seed_base  = start_draw + idx
        next_bets  = build_next_bets_from_seed(
            sorted_matched=sorted_matched,
            last_bet_vals=last_bet_vals,
            seed_base=seed_base,
            anchor_date=y_date,
            df_all=df_all,
        )

        # 最後一期：生成真實下期預測
        if idx == len(recent_draws) - 1:
            future_seed = start_draw + idx + 1000
            future_bets = build_next_bets_from_seed(
                sorted_matched=sorted_matched,
                last_bet_vals=last_bet_vals,
                seed_base=future_seed,
                anchor_date=y_date,
                df_all=df_all,
            )
            write_next_pred_func(valid_next_draw_date, future_bets)
            append_bet_record_func(valid_next_draw_date, future_bets)
            
            # ── 提取策略上下文以顯示詳細信息 ────────────────────────────────────
            ctx = seed_lotto_strategy.get_strategy_context(y_date, collect_balls_break=COLLECT_BALLS_BREAK, draw_same_color=DRAW_SAME_COLOR)
            pred_interval = ctx.get("pred_interval", [])
            rbg_collect = ctx.get("rbg_collect", {})
            _w = rbg_collect.get(0, [None, None, None])
            
            print(f'\n/> 已寫入下期預測: {valid_next_draw_date}')
            for i, b in enumerate(future_bets, 1):
                print(f'   {i}. {b}')
            print('-' * 56)
            print(f'上期種子號 ：{sorted_matched}')
            print(f'預測下期 N1..N6 區間號: {pred_interval}')
            print(f'RBG 窗口期： R={_w[0]}  B={_w[1]}  G={_w[2]}')
            print(f'/> R 集合球: {rbg_collect.get(1, [])}')
            print(f'/> B 集合球: {rbg_collect.get(2, [])}')
            print(f'/> G 集合球: {rbg_collect.get(3, [])}')
            print('=' * 56)

        if next_draw_date is not None:
            append_bet_record_func(next_draw_date, next_bets)

    # ── 回測統計 ─────────────────────────────────────────────────
    total_amount = total_bets * BET_UNIT
    print('\n' + '=' * 56)
    print('【回測統計】')
    print(f'總投注: {total_bets} 注 / 總金額: ${total_amount:,} （每注 ${BET_UNIT}）')
    print('-' * 56)
    for score, label in PRIZE_LABELS.items():
        cnt = hit_counter.get(score, 0)
        amt = PRIZE_TABLE[score] * cnt
        tag = f'  獎金 ${amt:,}' if cnt > 0 else ''
        print(f'  {label} (命中={score}): {cnt} 次{tag}')
    print('-' * 56)
    print(f'回測中獎總額: ${total_prize:,}')
    print(f'損益:         ${total_prize - total_amount:,}')
    print('=' * 56)


# ══════════════════════════════════════════════════════════════════
#  模式二：真實投注核對
# ══════════════════════════════════════════════════════════════════

def run_live_check(df_all, valid_next_draw_date):
    """模式二：核對上次預測，追加結果，生成下期投注。"""
    # print('=' * 56)
    # print('【真實投注模式】核對上期投注，追加新資料')
    # print('=' * 56)

    # 讀取下期預測記錄，找出尚未核對的投注日期
    df_next = read_next_pred_safe()
    if df_next.empty:
        print('找不到 nextBetDraw_record.csv，改為以最近已核對資料自動重建下期預測。')
        rebuild_next_prediction_from_history(df_all, valid_next_draw_date)
        return

    pending_date = str(df_next['bet_date'].iloc[0])
    print(f'待核對期數: {pending_date}')

    # 從開獎資料找對應期的開獎結果
    row_match = df_all[df_all['ndate'].astype(str) == pending_date]
    if row_match.empty:
        print(f'開獎資料中找不到 {pending_date}，彩票資料可能尚未更新。')
        # print('請先執行 Z1_lotto_2026_download_project 更新開獎資料後再試。')
        # print('=' * 56)
        return

    row      = row_match.iloc[0]
    y_6balls  = [int(row[f'N{i}']) for i in range(1, 7)]
    y_special = int(row['N7'])
    print(f'開獎號碼: {y_6balls} + 特[{y_special}]')
    print('-' * 50)

    # 讀取該期投注記錄（可能來自 nextBetDraw_record 或 my_bet_records）
    bet_record = read_bet_for_date(pending_date)
    if bet_record is None or bet_record.empty:
        # fallback: 直接使用 nextBetDraw_record
        bet_record = df_next

    all_matched   = set()
    win_rows      = []
    last_bet_vals = None
    total_prize   = 0

    for _, bet_row in bet_record.iterrows():
        bet_vals = [int(x) for x in bet_row.iloc[1:7].values.tolist()]
        last_bet_vals = bet_vals
        matched, sp_hit, hit_score, prize = check_and_score(bet_vals, y_6balls, y_special)
        total_prize += prize

        all_matched |= matched
        win_result = [n if n in matched else 0 for n in bet_vals]
        win_rows.append(win_result)

        sp_tag = f' + 特[{y_special}]✨' if sp_hit else ''
        if prize > 0:
            print(f'   投注: {sorted(bet_vals)} -> 中 {sorted(matched)}{sp_tag} 命中={hit_score} 派彩 ${prize:,} 🎉')
        elif matched or sp_hit:
            print(f'   投注: {sorted(bet_vals)} -> 中 {sorted(matched)}{sp_tag} 命中={hit_score} ✅')
        else:
            print(f'   投注: {sorted(bet_vals)} 未中獎 ❌')

    print('-' * 50)

    # 確保 my_bet_records 也有本期記錄（若來自 nextBetDraw_record fallback 則補寫）
    existing = read_bet_for_date(pending_date)
    if existing is None or existing.empty:
        bet_list = [bet_row.iloc[1:7].values.tolist() for _, bet_row in bet_record.iterrows()]
        append_bet_record_func(pending_date, bet_list)

    # 追加中獎記錄
    append_win_record_func(pending_date, win_rows)
    print(f'已追加中獎記錄: {pending_date} -> {win_save_path.name}')

    sorted_matched = sorted(all_matched)
    if sorted_matched:
        print(f'種子號: {sorted_matched} ({len(sorted_matched)} 個)')
    if total_prize > 0:
        print(f'本期派彩: ${total_prize:,} 🎉')

    # 依種子 + 區間/RBG 策略生成下期投注
    seed_base  = int(datetime.datetime.now().timestamp()) % 100000
    next_bets  = build_next_bets_from_seed(
        sorted_matched=sorted_matched,
        last_bet_vals=last_bet_vals,
        seed_base=seed_base,
        anchor_date=pending_date,
        df_all=df_all,
    )

    append_bet_record_func(valid_next_draw_date, next_bets)
    write_next_pred_func(valid_next_draw_date, next_bets)

    # ── 提取策略上下文以顯示詳細信息 ────────────────────────────────────
    ctx = seed_lotto_strategy.get_strategy_context(pending_date, collect_balls_break=COLLECT_BALLS_BREAK, draw_same_color=DRAW_SAME_COLOR)
    pred_interval = ctx.get("pred_interval", [])
    rbg_collect = ctx.get("rbg_collect", {})
    _w = rbg_collect.get(0, [None, None, None])

    print(f'\n/> 下期投注: {valid_next_draw_date}')
    for i, b in enumerate(next_bets, 1):
        print(f'   {i}. {b}')
    # print('-' * 56)
    # print(f'上期種子號 ：{sorted_matched}')
    # print(f'預測下期 N1..N6 區間號: {pred_interval}')
    # print(f'RBG 窗口期： R={_w[0]}  B={_w[1]}  G={_w[2]}')
    # print(f'/> R 集合球: {rbg_collect.get(1, [])}')
    # print(f'/> B 集合球: {rbg_collect.get(2, [])}')
    # print(f'/> G 集合球: {rbg_collect.get(3, [])}')
    # print('=' * 56)


# ══════════════════════════════════════════════════════════════════
#  主程式
# ══════════════════════════════════════════════════════════════════

_WEEK_ZH = {1: '星期一', 2: '星期二', 3: '星期三', 4: '星期四',
            5: '星期五', 6: '星期六', 7: '星期日', 0: '星期日'}

import math
def _print_next_pred_header(valid_next_draw_date, week):
    
    """打印下期投注日期及目前預測號碼（若有）。"""
    if week is None or (isinstance(week, float) and math.isnan(week)):
        week_zh = str(week)  # 或 week_zh = "未知"
    else:
        week_zh = _WEEK_ZH.get(int(week), str(week))
    print('=' * 56)
    

    print(f'下期投注日期: {valid_next_draw_date} ({week_zh})')
    df_next = read_next_pred_safe()
    if not df_next.empty:
        pred_date = str(df_next['bet_date'].iloc[0])
        if pred_date == valid_next_draw_date:
            print('下期預測投注號碼：')
            for i, pred_row in df_next.iterrows():
                bet_vals = [int(pred_row[f'N{j}']) for j in range(1, 7)]
                print(f'   {i + 1}. {bet_vals}')
    print('=' * 56)
    print()


def _print_strategy_info():
    """每次執行固定顯示：種子號、區間預測、RBG 窗口期、三色集合球。"""
    # 取最近已核對日期作為錨定日期（bet_records 倒數第二筆，排除下期預測）
    anchor_date = None
    seeds = []
    try:
        df_next = read_next_pred_safe()
        next_date = str(df_next['bet_date'].iloc[0]) if not df_next.empty else None

        df_bets = pd.read_csv(save_path)
        df_bets['bet_date'] = df_bets['bet_date'].astype(str)
        settled = df_bets[df_bets['bet_date'] != next_date] if next_date else df_bets
        if not settled.empty:
            anchor_date = settled['bet_date'].iloc[-1]
    except Exception:
        pass

    if not anchor_date:
        return  # 尚未初始化，無法顯示

    # 從 win_results 取最近已核對日期的種子號
    try:
        df_win = pd.read_csv(win_save_path)
        df_win['bet_date'] = df_win['bet_date'].astype(str)
        row_win = df_win[df_win['bet_date'] == anchor_date]
        if not row_win.empty:
            last_win = row_win.iloc[-1]
            seeds = sorted([int(v) for v in last_win.iloc[1:7] if int(v) != 0])
    except Exception:
        pass

    # 呼叫策略上下文
    try:
        ctx = seed_lotto_strategy.get_strategy_context(
            anchor_date,
            collect_balls_break=COLLECT_BALLS_BREAK,
            draw_same_color=DRAW_SAME_COLOR,
        )
    except Exception:
        return

    pred_interval = ctx.get("pred_interval", [])
    rbg_collect   = ctx.get("rbg_collect", {})
    _w = rbg_collect.get(0, [None, None, None])

    # print('=' * 56)
    # print(f'【策略參數資訊】錨定日期: {anchor_date}')
    # print(f'上期種子號 ：{seeds}')
    # print(f'預測下期 N1..N6 區間號: {pred_interval}')
    # print(f'RBG 窗口期： R={_w[0]}  B={_w[1]}  G={_w[2]}')
    # print(f'/> R 集合球: {rbg_collect.get(1, [])}')
    # print(f'/> B 集合球: {rbg_collect.get(2, [])}')
    # print(f'/> G 集合球: {rbg_collect.get(3, [])}')
    # print('=' * 56)
    # print()


def main():
    # os.system('clear')
    print('\n')
    df_all = load_draw_data_func()
    valid_next_draw_date, week = res_func_marksix_next_BetDate.main()
    _print_next_pred_header(valid_next_draw_date, week)
    _print_strategy_info()

    if not _is_initialized():
        run_backtest_init(df_all, valid_next_draw_date)
    else:
        run_live_check(df_all, valid_next_draw_date)


if __name__ == "__main__":
    main()
