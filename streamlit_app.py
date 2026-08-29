from pathlib import Path
import runpy

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent


PAGES = {
    "predict": {
        "label": "下期預測",
        "icon": "🏆",
        "path": PROJECT_ROOT / "pages" / "0_predict_nextdraw.py",
        "login_required": False,
    },
    "results": {
        "label": "開獎紀錄",
        "icon": "📊",
        "path": PROJECT_ROOT / "pages" / "1_lotto_results.py",
        "login_required": False,
    },
    "member": {
        "label": "會員登入投注",
        "icon": "👤",
        "path": PROJECT_ROOT / "member" / "member_login.py",
        "bet_path": PROJECT_ROOT / "member" / "member_bet_center.py",
        "login_required": False,
    },
}


def init_state() -> None:
    """初始化全站狀態。"""

    st.session_state.setdefault("login_state", None)
    st.session_state.setdefault("login_email_val", None)
    st.session_state.setdefault("login_member_id", None)
    st.session_state.setdefault("current_page", "predict")


def apply_styles() -> None:
    """自製頂部導航列與會員狀態列樣式。"""

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        #MainMenu,
        header,
        footer {
            display: none !important;
            visibility: hidden !important;
        }
        .block-container {
            padding-top: 0.75rem;
        }
        .top-shell {
            position: sticky;
            top: 0;
            z-index: 999;
            background: rgba(255, 255, 255, 0.96);
            backdrop-filter: blur(10px);
            border-bottom: 0;
            padding: 2px 0 8px 0;
            margin-bottom: 10px;
        }
        .member-card-marker {
            display: none;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.member-card-marker) {
            background: #fbfbfb;
            border-color: #e8e8e8;
            margin-bottom: 6px;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.member-card-marker) [data-testid="stVerticalBlock"] {
            gap: 0;
        }
        .member-text {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 12px;
            font-weight: 700;
            color: #111827;
            line-height: 1.15;
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
            font-size: 13px;
        }
        .nav-hint {
            font-size: 12px;
            color: #6b7280;
            margin: 0 0 3px 2px;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.35rem;
        }
        .top-shell button {
            min-height: 34px !important;
            height: 34px !important;
            padding: 2px 8px !important;
            border-radius: 8px !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            white-space: nowrap !important;
        }
        .top-shell button p {
            white-space: nowrap !important;
            font-size: 13px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.member-card-marker) button {
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            height: 28px !important;
            min-height: 28px !important;
            padding: 0 8px !important;
            font-size: 11px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.member-card-marker) button p {
            font-size: 11px !important;
        }
        .subnav button {
            height: 30px !important;
            min-height: 30px !important;
            font-size: 12px !important;
        }
        div[data-testid="stSegmentedControl"] {
            width: 100%;
            margin: 0 0 8px 0;
        }
        div[data-testid="stSegmentedControl"] button {
            min-height: 32px !important;
            border-radius: 8px !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
        div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
            background: #dbeafe;
            border-color: #93c5fd !important;
            color: #1d4ed8 !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] p,
        div[data-testid="stSegmentedControl"] button[aria-selected="true"] p {
            color: #1d4ed8 !important;
            font-weight: 700 !important;
        }
        @media (max-width: 430px) {
            .block-container {
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
            .top-shell button {
                padding-left: 4px !important;
                padding-right: 4px !important;
                font-size: 12px !important;
            }
            .top-shell button p {
                font-size: 12px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def set_page(page_key: str) -> None:
    """切換主頁面。"""

    if st.session_state.get("current_page") == "member" and page_key != "member":
        reset_member_custom_bet_state()
    st.session_state["current_page"] = page_key


def reset_member_custom_bet_state() -> None:
    """離開會員投注中心時清空自定投注暫存畫面。"""

    for key in [
        "custom_seed_numbers",
        "custom_picker_seed_numbers",
        "custom_generated_numbers",
        "custom_generated_signature",
        "custom_banker_numbers",
        "custom_leg_numbers",
        "custom_saved_notice",
    ]:
        st.session_state.pop(key, None)
    for key in [
        "custom_seed_reset_token",
        "custom_banker_reset_token",
        "custom_leg_reset_token",
    ]:
        st.session_state[key] = int(st.session_state.get(key, 0)) + 1


def render_member_status() -> None:
    """顯示會員 email 和登出。"""

    email = st.session_state.get("login_email_val")
    login_state = st.session_state.get("login_state")

    with st.container(border=True):
        st.markdown('<span class="member-card-marker"></span>', unsafe_allow_html=True)
        if email:
            role = "管理員" if login_state == "admin" else "會員"
            st.markdown(
                f'<div class="member-text">{email}<span class="member-role">{role}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("登出", key="custom_nav_logout", use_container_width=True):
                reset_member_custom_bet_state()
                st.session_state["login_state"] = None
                st.session_state["login_email_val"] = None
                st.session_state["login_member_id"] = None
                st.session_state["current_page"] = "predict"
                st.rerun()
        else:
            st.markdown('<span class="member-muted">尚未登入會員</span>', unsafe_allow_html=True)


def render_top_nav() -> None:
    """顯示自製頂部導航列。"""

    current_page = st.session_state.get("current_page", "predict")
    render_member_status()

    nav_cols = st.columns(len(PAGES))
    for col, (page_key, item) in zip(nav_cols, PAGES.items()):
        selected = current_page == page_key
        label = f"{item['icon']} {item['label']}"
        button_type = "primary" if selected else "secondary"
        if col.button(label, key=f"nav_{page_key}", type=button_type, use_container_width=True):
            set_page(page_key)
            st.rerun()


def handle_redirects() -> None:
    """處理登入後由 member_login.py 設定的導向旗標。"""

    if (
        st.session_state.get("redirect_to_member_bet_center")
        and st.session_state.get("login_state") in ("user", "admin")
    ):
        st.session_state["redirect_to_member_bet_center"] = False
        st.session_state["current_page"] = "member"


def run_page_file(path: Path) -> None:
    """執行原本 pages/member 檔案，保留現有功能。"""

    runpy.run_path(str(path), run_name="__main__")


def get_current_page_path(page_key: str) -> Path:
    """會員入口依登入狀態切換：未登入是登入頁，已登入是投注中心。"""

    if page_key == "member" and st.session_state.get("login_state") in ("user", "admin"):
        return PAGES["member"]["bet_path"]
    return PAGES[page_key]["path"]


def main() -> None:
    st.set_page_config(page_title="MSK 6 六合彩投注預測", page_icon="🎯", layout="centered")
    
    init_state()
    handle_redirects()
    apply_styles()
    render_top_nav()

    current_page = st.session_state.get("current_page", "predict")
    run_page_file(get_current_page_path(current_page))
#  streamlit run streamlit_app.py

if __name__ == "__main__":
    main()
