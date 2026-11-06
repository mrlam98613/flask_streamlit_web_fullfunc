# Hostinger / Dokploy 部署檢查

## 必需提交到 GitHub 的檔案

- `Dockerfile`
- `requirements.txt`（以及 `pyproject.toml`、`uv.lock`）
- `streamlit_app.py`
- `pages/`、各功能程式目錄、`A_msk_balls_png/`
- 程式實際讀取的六合彩資料 CSV

`.gitignore` 只應排除本機環境、資料庫、秘密設定及程式執行後產生的資料；不能排除 Streamlit 頁面、Python 模組、球圖或預測所需的來源 CSV。

## Docker 檔案

`.dockerignore` 只控制 Docker build context，不會控制 GitHub。它目前排除本機資料庫、虛擬環境、快取與預測執行輸出；Docker build 仍會複製應用程式與必要的來源 CSV。

`Dockerfile` 是 Dokploy 使用 Docker 部署時的主要入口。建議 Dokploy：

- Repository：此 GitHub repository
- Branch：`main`
- Build method：`Dockerfile`
- Dockerfile path：`Dockerfile`
- Build context：repository root（`.`）
- Port：`8501`
- Start command：使用 Dockerfile 的 `CMD`

會員資料庫及 `S5_All_Recored` 屬於執行時資料，應掛載 Dokploy volume；不要依賴容器內檔案保存，因為重新部署會建立新容器。

## 更新仍是舊版時的檢查順序

1. 確認 GitHub `main` 的最新 commit 已出現，並與本機 `git rev-parse HEAD` 相同。
2. 確認 Dokploy source branch 是 `main`，不是其他 branch 或固定 commit。
3. 確認 GitHub webhook／Dokploy auto-deploy 已啟用，而且 webhook 回應成功。
4. 在 Dokploy 執行 Redeploy／重建，清除 build cache；不要只重啟舊 container。
5. 確認 Dokploy 的 build context 是 repository root，否則可能使用舊的子目錄內容。
6. 部署後查看 container log，確認啟動的是最新 commit；可在 Dokploy 加入 `GIT_COMMIT` environment variable 或在啟動頁面顯示版本作辨識。

若 GitHub 已更新但 Dokploy 沒有出現新的 build，問題通常是 webhook、branch、固定 commit 或 Dokploy build cache，不是 `.gitignore`。
