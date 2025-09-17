# 1. ベースイメージとして公式のPythonイメージを使用
FROM python:3.12-slim

# 2. コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 3. Pythonの依存関係をインストール
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. キャッシュ破壊用のラベルを追加
LABEL cache_buster="2025-09-09T08:30:00Z"

# 5. アプリケーションのコードと設定ファイルをコピー
COPY main.py .
COPY orion-config-final.yaml .

# 6. アプリケーションがリッスンするポートをコンテナに通知
EXPOSE 8080

# 7. 本番環境用のgunicornサーバーでアプリケーションを実行
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app