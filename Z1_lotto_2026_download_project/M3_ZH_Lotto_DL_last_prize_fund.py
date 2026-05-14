import requests
from bs4 import BeautifulSoup
import csv

#---- Config Path
from A0_config import Lotto_data_DIR

# 抓取網站
URL = "https://zh.lottolyzer.com/home/hong-kong/mark-six"
response = requests.get(URL)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, 'html.parser')

# 解析最新一期開獎資訊
def get_latest_draw_info(soup):
    draw_number = soup.find("span", id="latest_draw").text.strip()
    draw_date = soup.find("span", id="latest_date").text.strip()
    number_imgs = soup.select('#latest_numbers img.ball')
    numbers = [img["alt"] for img in number_imgs]

    prize_table = soup.select_one(".divisions-full table")
    prize_rows = prize_table.select("tbody tr")
    prizes = []
    for row in prize_rows:
        tds = row.find_all("td")
        prize_name = tds[0].text.strip()
        prize_amount = tds[1].text.strip()
        winner_count = tds[2].text.strip()
        prizes.append((prize_name, prize_amount, winner_count))
    
    return {
        "期數": draw_number,
        "日期": draw_date,
        "號碼": numbers,
        "獎項": prizes
    }

# 解析下一期預告資訊
def get_next_draw_info(soup):
    next_draw = soup.select_one("div.upcoming")
    draw_name = next_draw.select_one("span.draw-data").text.strip()
    date = next_draw.select_one("span.date-data").text.strip()
    prize = next_draw.select_one("span.prize-data").text.strip()
    
    return {
        "期數名稱": draw_name,
        "開獎日期": date,
        "預估頭獎": prize
    }



def main():
    # 取得資料
    latest = get_latest_draw_info(soup)
    next_draw = get_next_draw_info(soup)

    # 寫入 CSV
    with open(Lotto_data_DIR / "M3_lotto_prize_results.csv", mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)

        # 最新一期資訊
        writer.writerow(["🔴 最新一期"])
        writer.writerow(["期數", latest["期數"]])
        writer.writerow(["日期", latest["日期"]])
        writer.writerow(["號碼", ", ".join(latest["號碼"])])
        writer.writerow([])

        writer.writerow(["獎項", "獎金", "中獎注數"])
        for prize in latest["獎項"]:
            writer.writerow(prize)
        writer.writerow([])

        # 下一期資訊
        writer.writerow(["🟢 下一期"])
        writer.writerow(["期數名稱", next_draw["期數名稱"]])
        writer.writerow(["開獎日期", next_draw["開獎日期"]])
        writer.writerow(["預估頭獎", next_draw["預估頭獎"]])
    
    
    # print()
    # print('\U0001F7E2 M3_prize fund download finish !!')

if __name__ == '__main__':
    main() 