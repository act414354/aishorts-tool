# 使用官方 Python 輕量版映像檔
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 1. 安裝系統層級的依賴 (包含 FFmpeg)
# 這是雲端處理影片必須的步驟
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. 複製需求清單並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 複製所有程式碼到容器內
COPY . .

# 4. 建立必要的資料夾
RUN mkdir -p downloads static/outputs

# 5. 設定環境變數 (讓 Flask 在生產環境更穩定)
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# 6. 啟動指令 (使用 Gunicorn 作為生產環境伺服器)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "300", "app:app"]
