import re
import os
import pandas as pd
from pathlib import Path
from A0_config import Lotto_data_DIR

def extract_lotto_info(text):
    week_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}

    # 擷取日期
    last_draw_date_match = re.search(r"日期,(\d{4})年(\d{2})月(\d{2})日", text)
    last_draw_date = f"{last_draw_date_match.group(1)}-{last_draw_date_match.group(2)}-{last_draw_date_match.group(3)}"

    # 擷取號碼
    lotto_match = re.search(r"號碼,\"([^\"]+)\"", text)
    lotto_str = lotto_match.group(1)
    lotto_list = [num.strip() for num in lotto_str.split(",") if num.strip()]

    if len(lotto_list) != 7:
        raise ValueError(f"⚠️ 號碼數量不等於 7，實際為 {len(lotto_list)}：{lotto_list}")

    # 擷取下一期資料
    next_match = re.search(r"開獎日期,(\d{4})年(\d{2})月(\d{2})日\s+\((.)\)", text)
    next_draw_date = f"{next_match.group(1)}-{next_match.group(2)}-{next_match.group(3)}"
    week = week_map.get(next_match.group(4), "")

    # 擷取預估頭獎金額
    prize_match = re.search(r"預估頭獎,\"?\$([\d,]+)\"?", text)
    next_draw_prize_fund = prize_match.group(1).replace(",", "")

    return {
        "last_draw_date": last_draw_date,
        "N1": lotto_list[0],
        "N2": lotto_list[1],
        "N3": lotto_list[2],
        "N4": lotto_list[3],
        "N5": lotto_list[4],
        "N6": lotto_list[5],
        "N7": lotto_list[6],
        "next_draw_date": next_draw_date,
        "week": week,
        "next_draw_prize_fund": next_draw_prize_fund
    }

def save_to_csv(row_data, filename="M4_lotto_prize_summary.csv"):
    csv_file = Lotto_data_DIR / filename
    new_df = pd.DataFrame([row_data])

    if not os.path.exists(csv_file):
        new_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        # print("✅ M4 建立新檔並寫入第一筆資料")
    else:
        existing_df = pd.read_csv(csv_file, encoding="utf-8-sig")
        if row_data["last_draw_date"] not in existing_df["last_draw_date"].values:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
            # print("✅ M4 已新增資料到現有檔案")
        else:
            # print("⚠️ M4 相同資料已存在，未有重複新增")
            pass

def main():
    
    
    # # 🔹 模擬你貼的原始資料
    # raw_text = """
    # 🔴 最新一期
    # 期數,第25/059期
    # 日期,2025年05月29日
    # 號碼,"5, 6, 16, 21, 24, 35, 33"

    # 🟢 下一期
    # 期數名稱,25/060
    # 開獎日期,2025年06月01日 (日)
    # 預估頭獎,"$8,000,000"
    # """
    
    
    # # 🔁 從 M3_lotto_prize_results.csv 讀入一段純文字
    # csv_path = Lotto_data_DIR / 'M3_lotto_prize_results.csv'
    # df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # # 假設內容都在第一列第一欄
    # raw_text = df.iloc[0, 0]
    
    # 🔁 從 M3_lotto_prize_results.csv 讀入純文字
    csv_path = Lotto_data_DIR / 'M3_lotto_prize_results.csv'
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        raw_text = f.read()
    # 並儲存
    row_data = extract_lotto_info(raw_text)
    # print(row_data)
    save_to_csv(row_data)

if __name__ == "__main__":
    main()
