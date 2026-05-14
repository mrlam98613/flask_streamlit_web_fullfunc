import numpy as np
import pandas as pd

from datetime import datetime
from datetime import date
import os
#---- Config Path
from A0_config import Lotto_data_DIR


def get_concat_df_func():
    

    # 讀取兩個 CSV 文件
    df_old = pd.read_csv(Lotto_data_DIR / 'M0_MSK_2002_2024.csv')
    df_new = pd.read_csv(Lotto_data_DIR / 'M1_ZH_lotto_data.csv')

    # 確保欄位名稱一致
    df_old.columns = ['ndate', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7']
    df_new.columns = ['ndate', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7']
    
    # 合併兩個 DataFrame
    df_combined = pd.concat([df_old, df_new])

    # 移除重複日期的資料，保留最早出現的條目
    df_combined = df_combined.drop_duplicates(subset='ndate', keep='first')

    # 移除多餘的欄位，只保留需要的8個欄位
    df_combined = df_combined[['ndate', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7']]

    # 按日期排序，並重新排序索引
    df_combined = df_combined.sort_values(by='ndate', ascending=True).reset_index(drop=True)

    # 打印結果
    # print(df_combined)

    # 保存結果到 CSV 文件
    df_combined.to_csv(Lotto_data_DIR / 'M2_last_upgrade_lotto_data.csv', index=False)
    # df_combined.to_csv(Lotto_data_DIR / 'lotto_history.csv', index=False)
    # print("M2 Combined data saved to 'M2_last_lotto_data.csv'")


def main():

    
    get_concat_df_func()

if __name__ == '__main__':
    main() 


        