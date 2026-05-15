FROM python:3.12-slim

WORKDIR /app

# 安裝必要套件
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 複製 requirements 並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼
COPY . .

# 預設開放 8501 (Streamlit) 及 8080 (Flask/Gunicorn)
EXPOSE 8501 8080

# 啟動指令（可依需求切換 Flask 或 Streamlit）
# Flask (Gunicorn)
# CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]

# Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]