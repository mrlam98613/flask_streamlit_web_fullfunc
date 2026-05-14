
import streamlit as st
from css import navigation_center_style

# 1. 定義頁面
pages = {
    # "Home": [
    #     st.Page("app.py", title="首頁", icon="🏠"),
    # ],
    "預測紀錄": [
        st.Page("pages/0_card_lottoResults.py", title="下期預測", icon="🏆"),
    ],
    "開獎紀錄": [
        st.Page("pages/2_verifyPrize_results.py", title="最新開獎", icon="❤️"),
        
    ],
    "會員登入/註冊": [
        st.Page("member/member_login.py", title="會員登入", icon="❤️"),
        # test pass
    ],
    "投注計算機": [
        st.Page("pages/3_multiple_bet.py", title="複式計算機", icon="❤️"),
        st.Page("pages/4_banker_leg_bet.py", title="膽拖計算機", icon="🛎️"),
    ],
    
}


# 2. 載入置中 CSS
st.markdown(navigation_center_style, unsafe_allow_html=True)

# 3. 建立導覽列，設定為置頂 (position="top")
pg = st.navigation(pages, position="top")

# # 3. 執行頁面
pg.run()
