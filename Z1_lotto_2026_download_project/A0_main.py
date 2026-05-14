#!/usr/bin/env python3.9
# -*- encoding: utf-8 -*-
'''
改成macOS 自動背景執行。
bash ~/scripts/run_lotto_tasks.sh
# A0_main.py = '/Users/mrlammac/vscode_folder/msk_20250402_folder/z1_MSK_lotto_download_2025/'

@File    :  main.py url = 'https://zh.lottolyzer.com/
@Time    :   2022/09/10 20:30:18
@Author  :   mrLam
'''
import time



from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_PATH = PROJECT_ROOT / "log" / "lotto_download_log.txt"
#--- import

import M1_ZH_download_lotto
import M2_Concat_newOld_Table
import M3_ZH_Lotto_DL_last_prize_fund
import M4_ZH_last_next_draw_summary
import M5_copy_to_msk2026_X 
#--------------
def run():
    # Test Pass !
    # ===如果不是設 def(), 不要加 () ===
    # M1..M5 一定要加入 fun 否則, schedule 不能運行.
    M1_ZH_download_lotto.main()
    time.sleep(1)
    #----------------------
    M2_Concat_newOld_Table.main()
    time.sleep(1)
    #----------------------
    M3_ZH_Lotto_DL_last_prize_fund.main()
    time.sleep(1)

    M4_ZH_last_next_draw_summary.main()
    time.sleep(1)

    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # auto copy M1-M4 csv to msk_2026_X → A_msk_lotto_data_folder
    nbool = M5_copy_to_msk2026_X.main()
    if nbool:
        # 將 now 寫入 /log/lotto_download_log.txt
        if not LOG_PATH.parent.exists():
            LOG_PATH.parent.mkdir(parents=True)
        # 覆蓋模式 'w' 'a' 追尾加：每次運行都覆蓋舊 log
        with open(LOG_PATH, 'w') as f:
            f.write(f"{now} M1-M5 下載、處理、複製完成！\n")
    else:
        with open(LOG_PATH, 'w') as f:
            f.write(f"{now} M5 複製失敗！\n")
        
    print(f"✅ M1-M5 下載、處理、複製完成！時間：{now}")

if __name__ == '__main__':
    run()

    # schedule.every(1).hour.do(run)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)