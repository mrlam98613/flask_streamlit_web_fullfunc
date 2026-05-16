FROM python:3.12-slim
LABEL "language"="python"
LABEL "framework"="streamlit"

WORKDIR /app

# 安裝必要套件（包括 cron）
RUN apt-get update && apt-get install -y curl cron && rm -rf /var/lib/apt/lists/*

# 複製 requirements 並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼
COPY . .

# 建立日誌目錄
RUN mkdir -p /var/log/cron

# 複製並載入 crontab.txt
COPY crontab.txt /tmp/crontab.txt
RUN crontab /tmp/crontab.txt

# 預設開放 8501 (Streamlit) 及 8080 (Flask/Gunicorn)
EXPOSE 8501 8080

# 啟動 cron 和 Streamlit
CMD cron && exec streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0

