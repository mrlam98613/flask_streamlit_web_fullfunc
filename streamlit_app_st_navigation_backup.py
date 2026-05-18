
import streamlit as st
from css import navigation_center_style


def init_login_state():
    st.session_state.setdefault("login_state", None)
    st.session_state.setdefault("login_email_val", None)
    st.session_state.setdefault("login_member_id", None)


def render_member_status_bar():
    """在全站頂部顯示會員登入狀態與登出按鈕。"""

    init_login_state()
    email = st.session_state.get("login_email_val")
    login_state = st.session_state.get("login_state")

    st.markdown(
        """
        <style>
        .member-topbar-text {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 14px;
            line-height: 1.4;
        }
        .member-id {
            font-weight: 700;
            color: #111827;
        }
        .member-role {
            display: inline-block;
            margin-left: 5px;
            padding: 1px 5px;
            border-radius: 999px;
            background: #eef6ff;
            color: #1d4ed8;
            font-size: 11px;
            font-weight: 700;
        }
        .member-muted {
            color: #6b7280;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.member-status-marker) {
            background: #fbfbfb;
            border-color: #e8e8e8;
            margin: 2px 0 10px 0;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.member-status-marker) button {
            width: 38px !important;
            min-width: 38px !important;
            max-width: 38px !important;
            height: 24px !important;
            min-height: 24px !important;
            padding: 0 !important;
            border-radius: 6px;
            font-size: 11px !important;
            line-height: 1 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.member-status-marker) button p {
            white-space: nowrap;
            font-size: 11px !important;
            line-height: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if email:
        role = "管理員" if login_state == "admin" else "會員"
        with st.container(border=True):
            st.markdown('<span class="member-status-marker"></span>', unsafe_allow_html=True)
            cols = st.columns([6.2, 0.55], vertical_alignment="center")
            cols[0].markdown(
                f"""
                <div class="member-topbar-text">
                    <span class="member-id">{email}</span><span class="member-role">{role}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with cols[1]:
                logout_clicked = st.button("登出", key="global_logout_btn")

        if logout_clicked:
            st.session_state["login_state"] = None
            st.session_state["login_email_val"] = None
            st.session_state["login_member_id"] = None
            st.rerun()
    else:
        with st.container(border=True):
            st.markdown('<span class="member-status-marker"></span>', unsafe_allow_html=True)
            st.markdown('<span class="member-muted">尚未登入會員</span>', unsafe_allow_html=True)


render_member_status_bar()

# 1. 定義頁面
pages = {
    # "主頁": [
    #     st.Page("pages/home.py", title="種子投注法說明", icon="🏠"),
    # ],
    "種子投注法": [
        st.Page("pages/0_predict_nextdraw.py", title="系統下期預測", icon="🏆"),
    ],
    "最新開獎紀錄": [
        st.Page("pages/1_lotto_results.py", title="最新及過往開獎紀錄", icon="❤️"),
        
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

if st.session_state.get("login_state") in ("user", "admin"):
    pages["會員投注中心"] = [
        st.Page("member/member_bet_center.py", title="會員投注中心", icon="🎯"),
    ]


# 2. 載入置中 CSS
st.markdown(navigation_center_style, unsafe_allow_html=True)

# 3. 建立導覽列，設定為置頂 (position="top")
pg = st.navigation(pages, position="top")

if (
    st.session_state.get("redirect_to_member_bet_center")
    and st.session_state.get("login_state") in ("user", "admin")
):
    st.session_state["redirect_to_member_bet_center"] = False
    st.switch_page("member/member_bet_center.py")

# # 3. 執行頁面
pg.run()

# streamlit run streamlit_app.py
