import pandas as pd  
from pathlib import Path


def get_JC_next_Date():
    
    current_dir = Path(__file__).resolve().parent

    ''' 在自已目錄下,讀取某個Folder '''

    df = pd.read_csv(current_dir.parent / 'A_msk_lottery_data_folder' / 'M4_lotto_prize_summary.csv')
    
    # last_data = df.iloc[-1:,0:8]
    # print(last_data)
    
    # ✅ 取出最後一列的 'next_draw_date' 與 'week' 欄位
    last_row = df.iloc[-1]
    next_draw_date = last_row['next_draw_date']
    next_draw_week = last_row['week']
    # print("下一期開獎日期：", next_draw_date)
    # print("星期幾（數字）：", next_draw_week)
    
    return next_draw_date, next_draw_week
def main():

    next_draw_date, next_draw_week = get_JC_next_Date()
    return next_draw_date, next_draw_week

if __name__ == '__main__':
    main()