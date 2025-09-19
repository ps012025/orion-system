# 1. ベースイメージとしてPython 3.12-slimを選択
FROM python:3.12-slim

# 2. アプリケーションの作業ディレクトリを設定
WORKDIR /app

# 3. 依存関係のファイルをコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. アプリケーションのソースコードを全てコピー
COPY . .

# 5. ジョブ実行時に main.py を実行する (JobなのでWebサーバーは不要)
CMD ["python", "main.py"]
