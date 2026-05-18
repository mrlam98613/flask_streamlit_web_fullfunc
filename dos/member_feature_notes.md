記錄：

會員登入系統
會員投注中心
自定投注選號盤
custom component
Dockerfile 加 Node.js

flask_st_webApp/
├─ Dockerfile
├─ streamlit_app.py
├─ db.py
├─ member/
├─ pages/
├─ custom_components/
└─ docs/
   └─ member_feature_notes.md

# Member Feature Notes

## 已完成
- 會員登入系統
- 會員註冊
- 忘記密碼
- 會員投注中心
- 系統預測投注加入會員紀錄
- 會員自定投注
- 自定投注選號盤
- Custom component: `custom_components/number_picker`
- Dockerfile 加入 Node.js 22

## 主要檔案
- `streamlit_app.py`
- `member/member_login.py`
- `member/member_bet_center.py`
- `member/member_custom_bet.py`
- `custom_components/number_picker.py`
- `custom_components/number_picker_frontend/index.html`
- `db.py`
- `Dockerfile`