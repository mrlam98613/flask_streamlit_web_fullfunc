#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Z3 新版六合彩爬蟲主程式。

功能：
1. 建立 Lotto_Data_Folder，並複製歷史底表 M0_MSK_2002_2024.csv
2. 從 lottolyzer 下載最新六合彩歷史資料，儲存為 Lotto_Data_Folder/M1_ZH_lotto_data.csv
3. 合併 M0 舊歷史資料與 M1 新下載資料，儲存為 Lotto_Data_Folder/M2_last_upgrade_lotto_data.csv
4. 下載最新一期獎金及下一期資料，儲存為 Lotto_Data_Folder/M3_lotto_prize_results.csv
5. 從 M3 摘要出下一期資訊，儲存為 Lotto_Data_Folder/M4_lotto_prize_summary.csv
6. 複製 M1-M4 CSV 到專案根目錄的 A_msk_lottery_data_folder/
"""

from __future__ import annotations

import csv
import re
import shutil
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# === 路徑設定 ===
PROJECT_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_DIR.parent

# 新版資料一律存放在自己的資料夾下。
DATA_DIR = PROJECT_DIR / "Lotto_Data_Folder"
LOG_PATH = PROJECT_DIR / "log" / "lotto_download_log.txt"

# M1-M4 最後會複製到這個資料夾，供 Streamlit / Web App 使用。
WEBAPP_DATA_DIR = REPO_ROOT / "A_msk_lottery_data_folder"

# 合併 M2 時需要歷史底表；第一次執行會先從舊專案複製一份到新版資料夾。
LOCAL_HISTORY_CSV = DATA_DIR / "M0_MSK_2002_2024.csv"
OLD_HISTORY_CSV = (
    REPO_ROOT
    / "Z1_lotto_2026_download_project"
    / "Lotto_Data_Folder"
    / "M0_MSK_2002_2024.csv"
)

M1_CSV = DATA_DIR / "M1_ZH_lotto_data.csv"
M2_CSV = DATA_DIR / "M2_last_upgrade_lotto_data.csv"
M3_CSV = DATA_DIR / "M3_lotto_prize_results.csv"
M4_CSV = DATA_DIR / "M4_lotto_prize_summary.csv"

LOTTO_HISTORY_URL = (
    "https://zh.lottolyzer.com/history/hong-kong/mark-six/page/"
    "{page}/per-page/50/summary-view"
)
LOTTO_HOME_URL = "https://zh.lottolyzer.com/home/hong-kong/mark-six"

# connect timeout, read timeout；避免網站回應太慢時長時間卡住。
REQUEST_TIMEOUT = (8, 12)
DOWNLOAD_PAGES = range(1, 7)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}


def ensure_folders() -> None:
    """建立本程式需要的資料夾。"""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEBAPP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def ensure_local_history_csv() -> None:
    """確保新版資料夾內有 M0 歷史底表，M2 合併才有完整資料來源。"""

    if LOCAL_HISTORY_CSV.exists():
        return

    if not OLD_HISTORY_CSV.exists():
        raise FileNotFoundError(f"找不到可複製的 M0 歷史底表：{OLD_HISTORY_CSV}")

    shutil.copy2(OLD_HISTORY_CSV, LOCAL_HISTORY_CSV)


def now_string() -> str:
    """回傳統一格式的目前時間字串。"""

    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def write_log(message: str) -> None:
    """寫入執行結果；每次執行覆蓋舊 log。"""

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(message + "\n", encoding="utf-8")


def build_http_session() -> requests.Session:
    """建立可重試的 HTTP Session，降低偶發網絡慢速或斷線造成的失敗。"""

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_soup(url: str) -> BeautifulSoup:
    """下載網頁並轉成 BeautifulSoup，失敗時直接拋出錯誤。"""

    response = HTTP_SESSION.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")


HTTP_SESSION = build_http_session()


def download_lotto_page(page: int) -> pd.DataFrame:
    """下載單頁六合彩歷史資料，整理成 ndate, N1-N7 欄位。"""

    soup = fetch_soup(LOTTO_HISTORY_URL.format(page=page))
    table = soup.find("table")

    if table is None:
        raise ValueError(f"Page {page} 找不到資料表")

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows: list[list[str]] = []

    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)

    df = pd.DataFrame(rows, columns=headers)
    required_columns = {"日期", "中獎號碼", "特別號碼"}

    if not required_columns.issubset(df.columns):
        raise ValueError(f"Page {page} 缺少必要欄位：{required_columns}")

    df = df[["日期", "中獎號碼", "特別號碼"]].copy()
    df["中獎號碼"] = df["中獎號碼"].str.replace(" ", ",", regex=False)
    number_df = df["中獎號碼"].str.split(",", expand=True)

    if number_df.shape[1] != 6:
        raise ValueError(f"Page {page} 中獎號碼數量不是 6 個")

    df[["N1", "N2", "N3", "N4", "N5", "N6"]] = number_df
    df = df[["日期", "N1", "N2", "N3", "N4", "N5", "N6", "特別號碼"]]
    df.columns = ["ndate", "N1", "N2", "N3", "N4", "N5", "N6", "N7"]
    return df[df["ndate"] != "日期"]


def create_m1_latest_history() -> None:
    """產生 M1：下載最近數頁六合彩歷史資料。"""

    dataframes = []
    for page in DOWNLOAD_PAGES:
        # print(f"   - 下載歷史資料第 {page} 頁 ...", flush=True)
        dataframes.append(download_lotto_page(page))

    combined_df = pd.concat(dataframes, ignore_index=True)
    combined_df = combined_df.sort_values(by="ndate", ascending=True).reset_index(drop=True)
    combined_df.to_csv(M1_CSV, index=False)


def get_history_csv_path() -> Path:
    """取得 M2 合併時要使用的舊歷史底表。"""

    ensure_local_history_csv()
    return LOCAL_HISTORY_CSV


def create_m2_merged_history() -> None:
    """產生 M2：合併歷史底表和 M1 最新資料。"""

    history_csv = get_history_csv_path()
    old_df = pd.read_csv(history_csv)
    new_df = pd.read_csv(M1_CSV)

    columns = ["ndate", "N1", "N2", "N3", "N4", "N5", "N6", "N7"]
    old_df.columns = columns
    new_df.columns = columns

    combined_df = pd.concat([old_df, new_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset="ndate", keep="first")
    combined_df = combined_df[columns]
    combined_df = combined_df.sort_values(by="ndate", ascending=True).reset_index(drop=True)
    combined_df.to_csv(M2_CSV, index=False)


def parse_latest_draw_info(soup: BeautifulSoup) -> dict[str, object]:
    """解析最新一期開獎資料和獎金資料。"""

    draw_number = soup.find("span", id="latest_draw").get_text(strip=True)
    draw_date = soup.find("span", id="latest_date").get_text(strip=True)
    numbers = [img["alt"] for img in soup.select("#latest_numbers img.ball")]

    prize_table = soup.select_one(".divisions-full table")
    if prize_table is None:
        raise ValueError("找不到最新一期獎金表")

    prizes: list[tuple[str, str, str]] = []
    for row in prize_table.select("tbody tr"):
        tds = row.find_all("td")
        if len(tds) >= 3:
            prizes.append(
                (
                    tds[0].get_text(strip=True),
                    tds[1].get_text(strip=True),
                    tds[2].get_text(strip=True),
                )
            )

    return {
        "期數": draw_number,
        "日期": draw_date,
        "號碼": numbers,
        "獎項": prizes,
    }


def parse_next_draw_info(soup: BeautifulSoup) -> dict[str, str]:
    """解析下一期開獎日期和預估頭獎。"""

    next_draw = soup.select_one("div.upcoming")
    if next_draw is None:
        raise ValueError("找不到下一期開獎資料")

    return {
        "期數名稱": next_draw.select_one("span.draw-data").get_text(strip=True),
        "開獎日期": next_draw.select_one("span.date-data").get_text(strip=True),
        "預估頭獎": next_draw.select_one("span.prize-data").get_text(strip=True),
    }


def create_m3_prize_results() -> None:
    """產生 M3：最新一期開獎、獎金，以及下一期資料。"""

    soup = fetch_soup(LOTTO_HOME_URL)
    latest = parse_latest_draw_info(soup)
    next_draw = parse_next_draw_info(soup)

    with M3_CSV.open(mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)

        writer.writerow(["🔴 最新一期"])
        writer.writerow(["期數", latest["期數"]])
        writer.writerow(["日期", latest["日期"]])
        writer.writerow(["號碼", ", ".join(latest["號碼"])])
        writer.writerow([])

        writer.writerow(["獎項", "獎金", "中獎注數"])
        for prize in latest["獎項"]:
            writer.writerow(prize)
        writer.writerow([])

        writer.writerow(["🟢 下一期"])
        writer.writerow(["期數名稱", next_draw["期數名稱"]])
        writer.writerow(["開獎日期", next_draw["開獎日期"]])
        writer.writerow(["預估頭獎", next_draw["預估頭獎"]])


def extract_lotto_summary(text: str) -> dict[str, str]:
    """從 M3 文字內容抽出 M4 需要的一列摘要資料。"""

    week_map = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "日": "7"}

    last_draw_date_match = re.search(r"日期,(\d{4})年(\d{2})月(\d{2})日", text)
    lotto_match = re.search(r"號碼,\"([^\"]+)\"", text)
    next_draw_match = re.search(r"開獎日期,(\d{4})年(\d{2})月(\d{2})日\s+\((.)\)", text)
    prize_match = re.search(r"預估頭獎,\"?\$([\d,]+)\"?", text)

    if not all([last_draw_date_match, lotto_match, next_draw_match, prize_match]):
        raise ValueError("M3 內容格式不符合預期，無法產生 M4 摘要")

    lotto_list = [num.strip() for num in lotto_match.group(1).split(",") if num.strip()]
    if len(lotto_list) != 7:
        raise ValueError(f"號碼數量不等於 7，實際為 {len(lotto_list)}：{lotto_list}")

    return {
        "last_draw_date": (
            f"{last_draw_date_match.group(1)}-"
            f"{last_draw_date_match.group(2)}-"
            f"{last_draw_date_match.group(3)}"
        ),
        "N1": lotto_list[0],
        "N2": lotto_list[1],
        "N3": lotto_list[2],
        "N4": lotto_list[3],
        "N5": lotto_list[4],
        "N6": lotto_list[5],
        "N7": lotto_list[6],
        "next_draw_date": (
            f"{next_draw_match.group(1)}-"
            f"{next_draw_match.group(2)}-"
            f"{next_draw_match.group(3)}"
        ),
        "week": week_map.get(next_draw_match.group(4), ""),
        "next_draw_prize_fund": prize_match.group(1).replace(",", ""),
    }


def create_m4_prize_summary() -> None:
    """產生 M4：若同一期已存在，就不重複新增。"""

    raw_text = M3_CSV.read_text(encoding="utf-8-sig")
    row_data = extract_lotto_summary(raw_text)
    new_df = pd.DataFrame([row_data])

    if not M4_CSV.exists():
        new_df.to_csv(M4_CSV, index=False, encoding="utf-8-sig")
        return

    existing_df = pd.read_csv(M4_CSV, encoding="utf-8-sig")
    if row_data["last_draw_date"] in existing_df["last_draw_date"].values:
        return

    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    combined_df.to_csv(M4_CSV, index=False, encoding="utf-8-sig")


def copy_m1_to_m4_to_webapp_folder() -> None:
    """複製 M1-M4 CSV 到 A_msk_lottery_data_folder。"""

    for csv_path in [M1_CSV, M2_CSV, M3_CSV, M4_CSV]:
        if not csv_path.exists():
            raise FileNotFoundError(f"找不到要複製的檔案：{csv_path}")
        shutil.copy2(csv_path, WEBAPP_DATA_DIR / csv_path.name)


def run() -> bool:
    """主流程：依序產生 M1-M4，最後複製到 Web App 資料夾。"""

    ensure_folders()

    try:
        # print("▶️ 準備 M0 歷史底表 ...")
        ensure_local_history_csv()

        # print("▶️ M1 下載最新六合彩歷史資料 ...")
        create_m1_latest_history()

        # print("▶️ M2 合併新舊歷史資料 ...")
        create_m2_merged_history()

        # print("▶️ M3 下載最新獎金和下一期資料 ...")
        create_m3_prize_results()

        # print("▶️ M4 產生下一期摘要 ...")
        create_m4_prize_summary()

        print("▶️ 複製 M1-M4 到 A_msk_lottery_data_folder ...")
        copy_m1_to_m4_to_webapp_folder()

    except KeyboardInterrupt:
        message = f"{now_string()} 使用者中斷下載，流程未完成。"
        write_log(message)
        print(f"\n⚠️ {message}")
        return False
    except Exception as exc:
        message = f"{now_string()} 執行失敗：{exc}"
        write_log(message)
        print(f"❌ {message}")
        return False

    message = f"{now_string()} M1-M4 下載、合併、摘要、複製完成！"
    write_log(message)
    print(f"✅ {message}")
    return True


if __name__ == "__main__":
    run()
