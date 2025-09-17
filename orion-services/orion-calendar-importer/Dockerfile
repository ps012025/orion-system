# Python 3.10をベースイメージとして使用
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係をインストール
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# Run Gunicorn listening on the port defined by the PORT environment variable
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main:app
