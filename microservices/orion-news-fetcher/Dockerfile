# ベースイメージとしてPython 3.12-slimを選択
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係のファイルをコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# gunicornを使ってFlaskアプリケーションを起動
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app