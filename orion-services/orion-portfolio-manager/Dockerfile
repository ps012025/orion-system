# /orion-services/orion-portfolio-manager/Dockerfile

# Python 3.12の公式スリムイメージをベースとして使用
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt requirements.txt

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY main.py .

# Gunicorn Webサーバーを起動
# PORT環境変数はCloud Runによって自動的に設定される
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
