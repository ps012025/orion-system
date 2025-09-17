# 1. ベースイメージとして公式のPythonイメージを使用
FROM python:3.12-slim

# 2. コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 3. 依存関係をインストール
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. アプリケーションのコードと設定ファイルをコピー
COPY main.py .
COPY orion-config-final.yaml .

# 5. アプリケーションがリッスンするポートをコンテナに通知
EXPOSE 8080

# 6. 本番環境用のgunicornサーバーでアプリケーションを実行
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app