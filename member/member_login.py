import sqlite3

# -------- import 
import streamlit as st
import hashlib

# 加入 member.db path 模組，確保資料庫檔案在正確位置
# from pathlib import Path

# PROJECT_ROOT = Path(__file__).resolve().parent
# DB_PATH = PROJECT_ROOT / "member" / "members.db"

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import init_db, add_member, get_member

def get_all_members():
    conn = sqlite3.connect("members.db")
    cur = conn.cursor()
    cur.execute('SELECT id, email, phone, is_admin FROM members')
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_member(member_id):
    conn = sqlite3.connect("members.db")
    cur = conn.cursor()
    cur.execute('DELETE FROM members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()

def update_member(member_id, new_email, new_phone):
    conn = sqlite3.connect("members.db")
    cur = conn.cursor()
    cur.execute('UPDATE members SET email = ?, phone = ? WHERE id = ?', (new_email, new_phone, member_id))
    conn.commit()
    conn.close()
    


# --- 這裡設定第一個 admin 帳號 ---
ADMIN_EMAIL = "mrlam98613@gmail.com"  # 請修改為你的管理員信箱
ADMIN_PHONE = "98687989"         # 請修改為你的管理員手機
ADMIN_PASSWORD = "98687989"        # 請修改為你的管理員密碼

def create_first_admin():
	if not get_member(ADMIN_EMAIL):
		add_member(ADMIN_EMAIL, ADMIN_PHONE, hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(), 1)

# tab1:會員登入 tab2:會員註冊 tab3:忘記密碼。Tab 分頁
# ...existing code...

def hash_password(password):
	return hashlib.sha256(password.encode()).hexdigest()


# init_db()  # 確保資料庫和表格已建立
init_db()
# create_first_admin()  # 確保第一個 admin 帳號存在
create_first_admin()



tabs = st.tabs(["會員登入", "會員註冊", "忘記密碼"])

with tabs[0]:
    st.header("會員登入")
    email = st.text_input("信箱", key="login_email")
    password = st.text_input("密碼", type="password", key="login_pwd")
    admin_login = st.checkbox("管理員登入", key="login_admin")
    if 'login_state' not in st.session_state:
        st.session_state['login_state'] = None
    if 'login_email_val' not in st.session_state:
        st.session_state['login_email_val'] = None
    if st.button("登入", key="login_btn"):
        member = get_member(email)
        if member and member[3] == hash_password(password):
            if admin_login:
                if member[4] == 1:
                    st.success(f"管理員登入成功，{email}")
                    st.session_state["login_state"] = "admin"
                    st.session_state["login_email_val"] = email
                else:
                    st.error("非管理員帳號")
            else:
                st.success(f"歡迎回來，{email}")
                st.session_state["login_state"] = "user"
                st.session_state["login_email_val"] = email
        else:
            st.error("帳號或密碼錯誤")

    # 管理員登入後顯示會員表格
    if st.session_state.get("login_state") == "admin":
        st.subheader("會員管理")
        members = get_all_members()
        for m in members:
            col1, col2, col3, col4, col5 = st.columns([2,2,2,1,1])
            col1.write(m[1])  # email
            col2.write(m[2])  # phone
            col3.write("管理員" if m[3] else "普通會員")
            if m[1] != ADMIN_EMAIL:
                if col4.button("修改", key=f"edit_{m[0]}"):
                    new_email = st.text_input(f"新信箱_{m[0]}", value=m[1], key=f"edit_email_{m[0]}")
                    new_phone = st.text_input(f"新手機_{m[0]}", value=m[2], key=f"edit_phone_{m[0]}")
                    if st.button(f"確認修改_{m[0]}"):
                        update_member(m[0], new_email, new_phone)
                        st.success("修改成功，請重新整理頁面！")
                if col5.button("刪除", key=f"del_{m[0]}"):
                    delete_member(m[0])
                    st.warning("已刪除會員，請重新整理頁面！")

with tabs[1]:
    st.header("會員註冊")
    reg_email = st.text_input("註冊信箱", key="reg_email")
    reg_phone = st.text_input("手機號碼", key="reg_phone")
    reg_password = st.text_input("密碼 (6-12字元)", type="password", key="reg_pwd")
    if st.button("註冊", key="reg_btn"):
        if len(reg_password) < 6 or len(reg_password) > 12:
            st.warning("密碼長度需 6-12 字元")
        elif not reg_email or not reg_phone:
            st.warning("信箱與手機號碼皆必填")
        elif get_member(reg_email):
            st.warning("此信箱已註冊")
        else:
            add_member(reg_email, reg_phone, hash_password(reg_password), 0)
            st.success("註冊成功，請登入！")

with tabs[2]:
    st.header("忘記密碼")
    forgot_email = st.text_input("註冊信箱", key="forgot_email")
    forgot_phone = st.text_input("手機號碼", key="forgot_phone")
    new_password = st.text_input("新密碼 (6-12字元)", type="password", key="forgot_pwd")
    if st.button("重設密碼", key="forgot_btn"):
        if len(new_password) < 6 or len(new_password) > 12:
            st.warning("密碼長度需 6-12 字元")
        elif not forgot_email or not forgot_phone:
            st.warning("信箱與手機號碼皆必填")
        elif not get_member(forgot_email):
            st.warning("此信箱尚未註冊")
        else:
            from db import reset_password
            if reset_password(forgot_email, forgot_phone, hash_password(new_password)):
                st.success("密碼重設成功，請重新登入！")
            else:
                st.error("信箱或手機號碼錯誤，請確認輸入")

# -------------------------------------------------｜
# tab1:會員登入 tab2:會員註冊 tab3:忘記密碼。Tab 分頁
# 普通會員登入
# mPage1:系統下期預測 

# mPage2:會員新增投注
# mPage3:會員投注紀錄

# 管理員登入，(包括普通會員功能)
# mPage1:系統下期預測 
# mPage2:會員新增投注
# mPage3:會員投注紀錄
# aPage1:會員管理新增/刪除/修改
# aPage2:系統預測管理

# 新會員註冊
# rPage1: ( 輸入信箱 + 輸入手機號碼 ) 必要 2 樣齊。
# rPage2: 1.系統產生密碼，2.自定密碼，最少 6-12 個數字就可。
# rPage3: 註冊成功


# 忘記密碼
# fPage1:輸入註冊信箱 + 輸入手機號碼
# fPage2:申請重設密碼 --> 發送按鈕
# fPage3: 系統確認 (email + 手機號碼) 正確，立即可重設密碼，確認新密碼，重設成功
