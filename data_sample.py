import streamlit as st
import pandas as pd
from css import card_style, container_style  # 匯入 CSS
from pathlib import Path
import base64
import csv

def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

PROJECT_ROOT = Path(__file__).resolve().parent
PRIZE_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M3_lotto_prize_results.csv"
LOTTO_RESULTS_PATH = PROJECT_ROOT / "A_msk_lottery_data_folder" / "M2_last_upgrade_lotto_data.csv"
BALLS_DIR = PROJECT_ROOT / "A_msk_balls_png"



st.markdown("#### 從外部 CSS 檔案載入卡片樣式")

# # 載入樣式 (這行會把 CSS 注入到頁面中)
st.markdown(container_style, unsafe_allow_html=True)

df = pd.read_csv(LOTTO_RESULTS_PATH, encoding="utf-8-sig")
# 讓用戶選擇顯示期數（20 或 50 期）
period_options = [20, 50] if len(df) >= 50 else [20]
num_periods = st.selectbox("顯示最近幾期", period_options, index=0, format_func=lambda x: f"{x} 期")
df2 = df.iloc[-num_periods:, 0:8].copy()  # 取最後N筆資料的前8欄
# 重新命名欄位，配合下方卡片顯示
df2.columns = ["ndate", "N1", "N2", "N3", "N4", "N5", "N6", "N7"]
df2 = df2[::-1].reset_index(drop=True)  # 由新到舊排序
df2.insert(0, "期數", range(len(df), len(df)-len(df2), -1))

st.markdown('<h6 style="font-size:1.8rem; font-weight:bold;">開獎紀錄</h6>', unsafe_allow_html=True)
cols_per_row = 1  # 每行顯示幾張卡片
for i, (index, row_data) in enumerate(df2.iterrows()):
    balls_html = '<div class="balls-row">'
    for n in [row_data['N1'], row_data['N2'], row_data['N3'], row_data['N4'], row_data['N5'], row_data['N6']]:
        img_path = f"A_msk_balls_png/{int(n)}.png"
        img_b64 = img_to_base64(img_path)
        balls_html += f"<img src='data:image/png;base64,{img_b64}' alt='{int(n)}'>"
    balls_html += "<span style='font-weight:bold; font-size:1.2em; margin:0 4px;'>+</span>"
    img_path = f"A_msk_balls_png/{int(row_data['N7'])}.png"
    img_b64 = img_to_base64(img_path)
    balls_html += f"<img src='data:image/png;base64,{img_b64}' alt='{int(row_data['N7'])}'>"
    balls_html += '</div>'
    st.markdown(f'''<div class="my-card">
        <h6>[第{row_data['期數']}期] 開獎日期：{row_data["ndate"]}</h6>
        {balls_html}
    </div>''', unsafe_allow_html=True)
     
# 注意：如果你在 div 內部需要 Streamlit 原生元件（如按鈕），
# 建議改用 st.container(border=True) 搭配 CSS 修改其原本的 class。



