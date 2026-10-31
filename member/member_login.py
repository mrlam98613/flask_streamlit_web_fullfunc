from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import (  # noqa: E402
    add_member,
    delete_member,
    ensure_first_admin,
    get_all_members,
    get_member,
    hash_password,
    init_db,
    init_member_bet_db,
    is_valid_local_phone,
    set_member_password,
    update_member,
)


ADMIN_PHONE = "98687989"
ADMIN_PASSWORD = "7989"
AUTH_TABS = ["會員登入", "會員註冊", "忘記登入號碼"]


def init_login_state() -> None:
    """初始化全站登入狀態。"""

    st.session_state.setdefault("login_state", None)
    st.session_state.setdefault("login_email_val", None)
    st.session_state.setdefault("login_nickname", None)
    st.session_state.setdefault("login_member_id", None)


def set_logged_in(member) -> None:
    """登入成功後，把會員資料寫入 session state。"""

    st.session_state["login_member_id"] = member[0]
    st.session_state["login_email_val"] = member[2]
    st.session_state["login_nickname"] = member[6] or ""
    st.session_state["login_state"] = "admin" if int(member[4]) == 1 else "user"
    init_member_bet_db(member[2])


def switch_to_bet_center() -> None:
    """登入成功後直接前往會員投注中心。"""

    st.session_state["redirect_to_member_bet_center"] = True
    st.rerun()


def switch_auth_tab(tab_name: str) -> None:
    """安排下一次 rerun 切換登入頁分頁。"""

    st.session_state["member_auth_tab"] = tab_name
    st.session_state["member_auth_tab_pending"] = tab_name


def sync_auth_tab_from_widget() -> None:
    """把 radio widget 的選擇同步到登入頁目前分頁。"""

    st.session_state["member_auth_tab"] = st.session_state["member_auth_tab_widget"]


def render_admin_member_manager() -> None:
    """管理員登入後可查看、修改、刪除會員。"""

    st.subheader("會員管理")
    members = get_all_members()

    if not members:
        st.info("目前沒有會員資料。")
        return

    for member_id, phone_id, phone, is_admin, created_at, nickname in members:
        cols = st.columns([2.6, 1.4, 1.2, 1, 1])
        cols[0].write(nickname or phone_id)
        cols[1].write(phone)
        cols[2].write("管理員" if is_admin else "普通會員")

        if phone == ADMIN_PHONE:
            cols[3].caption("保留")
            cols[4].caption("-")
            continue

        if cols[3].button("修改", key=f"edit_member_{member_id}"):
            st.session_state[f"editing_member_{member_id}"] = True

        if cols[4].button("刪除", key=f"delete_member_{member_id}"):
            delete_member(member_id)
            st.warning("已刪除會員。")
            st.rerun()

        if st.session_state.get(f"editing_member_{member_id}"):
            with st.container(border=True):
                new_nickname = st.text_input("新暱稱（最多 20 字）", value=nickname, key=f"nickname_{member_id}")
                new_phone = st.text_input("新手機號碼", value=phone, key=f"phone_{member_id}")
                if st.button("確認修改", key=f"save_member_{member_id}"):
                    new_nickname = str(new_nickname or "").strip()
                    new_phone = str(new_phone or "").strip()
                    if not new_nickname or len(new_nickname) > 20:
                        st.error("暱稱必須輸入，且不可超過 20 字。")
                    elif not is_valid_local_phone(new_phone):
                        st.error("電話號碼請輸入 8 至 12 位數字，不需要地區號。")
                    else:
                        update_member(member_id, new_nickname, new_phone)
                        st.success("會員資料已更新。")
                        st.session_state.pop(f"editing_member_{member_id}", None)
                        st.rerun()


def render_login_tab() -> None:
    st.header("會員登入")
    st.markdown(
        """
        <style>
        input[aria-label="登入密碼"] {
            autocomplete: current-password;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    notice = st.session_state.pop("member_login_notice", None)
    if notice:
        st.success(notice)

    phone = st.text_input("電話號碼", key="login_phone")
    password = st.text_input("密碼（電話號碼最後 4 位數字）", type="password", key="member_login_password")

    if st.button("登入", key="login_btn", type="primary"):
        phone = str(phone or "").strip()
        password = str(password or "")

        if not is_valid_local_phone(phone):
            st.error("電話號碼請輸入 8 至 12 位數字。")
            return

        member = get_member(phone)
        if member and password == phone[-4:] and member[3] == hash_password(password):
            set_logged_in(member)
            st.success(f"登入成功，{member[6] or phone}")
            switch_to_bet_center()
        else:
            st.error("電話號碼或密碼錯誤。")

    if st.session_state.get("login_state") == "admin":
        render_admin_member_manager()


def render_register_tab() -> None:
    st.header("會員註冊")

    reg_phone = st.text_input("電話號碼（8 至 12 位數字，不用地區號）", key="reg_phone")
    reg_nickname = st.text_input("暱稱（必填，最多 20 字）", max_chars=20, key="reg_nickname")

    if st.button("註冊", key="reg_btn", type="primary"):
        reg_phone = str(reg_phone or "").strip()

        reg_nickname = str(reg_nickname or "").strip()
        if not is_valid_local_phone(reg_phone):
            st.warning("電話號碼請輸入 8 至 12 位數字，不需要地區號。")
        elif not reg_nickname or len(reg_nickname) > 20:
            st.warning("請輸入暱稱，最多 20 字。")
        elif get_member(reg_phone):
            st.warning("此電話號碼已註冊。")
        else:
            generated_password = reg_phone[-4:]
            add_member(reg_phone, reg_phone, hash_password(generated_password), 0, reg_nickname)
            init_member_bet_db(reg_phone)
            st.session_state["member_login_notice"] = (
                f"註冊成功。登入密碼是電話號碼最後 4 位數字：{generated_password}"
            )
            switch_auth_tab("會員登入")
            st.rerun()


def render_forgot_password_tab() -> None:
    st.header("忘記登入號碼")

    forgot_phone = st.text_input("電話號碼", key="forgot_phone")
    last_four = st.text_input("電話號碼最後 4 位數字", max_chars=4, key="forgot_last_four")

    if st.button("檢證並登入", key="forgot_btn", type="primary"):
        forgot_phone = str(forgot_phone or "").strip()
        last_four = str(last_four or "").strip()

        if not is_valid_local_phone(forgot_phone):
            st.warning("電話號碼請輸入 8 至 12 位數字。")
        elif not last_four.isdigit() or len(last_four) != 4:
            st.warning("請輸入電話號碼最後 4 位數字。")
        elif last_four != forgot_phone[-4:]:
            st.error("電話號碼或末四位數字不正確。")
        else:
            member = get_member(forgot_phone)
            if member:
                set_member_password(member[0], hash_password(forgot_phone[-4:]))
                set_logged_in(member)
                st.success("檢證成功，正在進入會員網頁。")
                switch_to_bet_center()
            else:
                st.error("找不到此電話號碼的會員資料。")


def main() -> None:
    init_db()
    ensure_first_admin(ADMIN_PHONE, ADMIN_PHONE, ADMIN_PASSWORD)
    init_login_state()

    st.session_state.setdefault("member_auth_tab", "會員登入")
    pending_tab = st.session_state.pop("member_auth_tab_pending", None)
    if pending_tab in AUTH_TABS:
        st.session_state["member_auth_tab_widget"] = pending_tab

    current_tab = st.radio(
        "會員功能",
        AUTH_TABS,
        index=AUTH_TABS.index(st.session_state["member_auth_tab"]),
        horizontal=True,
        key="member_auth_tab_widget",
        on_change=sync_auth_tab_from_widget,
        label_visibility="collapsed",
    )

    if current_tab == "會員登入":
        render_login_tab()
    elif current_tab == "會員註冊":
        render_register_tab()
    else:
        render_forgot_password_tab()


main()
