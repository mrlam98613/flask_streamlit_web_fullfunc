import streamlit as st
import pandas as pd
from css import card_style, container_style  # 匯入 CSS
from pathlib import Path
import base64
import csv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIZE_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M3_lotto_prize_results.csv"
LOTTO_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M2_last_upgrade_lotto_data.csv"
BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"



st.markdown("#### 從外部 CSS 檔案載入卡片樣式")

# # 載入樣式 (這行會把 CSS 注入到頁面中)
st.markdown(container_style, unsafe_allow_html=True)

df = pd.read_csv(LOTTO_RESULTS_PATH, encoding="utf-8-sig")
df2 = df.iloc[-20:, 0:8].copy()  # 取最後20筆資料的前8欄
# 重新命名欄位，配合下方卡片顯示
df2.columns = ["ndate", "N1", "N2", "N3", "N4", "N5", "N6", "N7"]

st.markdown('<h5 style="font-size:1.8rem; font-weight:bold;">最新開獎紀錄</h5>', unsafe_allow_html=True)
cols_per_row = 1  # 每行顯示幾張卡片
for i, (index, row_data) in enumerate(df2.iterrows()):
    cols = st.columns(cols_per_row)
    with cols[0].container(border=True):  # 只用第一個欄位
        st.markdown(
            f"""
            <div class="my-card">
                <h5>開獎日期：{row_data['ndate']}</h5>
                <h5>
                <p>開獎號：{row_data['N1']} {row_data['N2']} {row_data['N3']} {row_data['N4']} {row_data['N5']} {row_data['N6']} + {row_data['N7']}</p>
                </h5>
            </div>
            """,
            unsafe_allow_html=True
        )
        
     
#     # 注意：如果你在 div 內部需要 Streamlit 原生元件（如按鈕），
#     # 建議改用 st.container(border=True) 搭配 CSS 修改其原本的 class。



