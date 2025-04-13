# ブラジリアン柔術師範AI - Streamlit フロントエンド

ブラジリアン柔術に関する質問に答えるAIチャットボットのStreamlitフロントエンドアプリケーションです。このアプリはDify APIを使用して柔術知識ベースにアクセスし、ユーザーの質問に回答します。

## 機能

- 柔術に関する質問に対する回答
- 会話履歴の保存と表示
- 会話のリセット機能
- モバイルフレンドリーなレスポンシブデザイン

## インストール方法

```bash
# リポジトリをクローン
git clone https://github.com/あなたのユーザー名/bjj-knowledge-bot.git
cd bjj-knowledge-bot

# 仮想環境を作成（任意）
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt
```

## 使用方法

```bash
streamlit run app.py
```

ブラウザが自動的に開き、アプリケーションが表示されます。通常は http://localhost:8501 でアクセスできます。

## 設定

アプリを使用するには、Dify APIの設定が必要です：

1. サイドバーにDify API Keyを入力します
2. 必要に応じてDify API Endpointを変更します
3. チャット入力欄から質問を入力します

## Streamlit Cloudへのデプロイ

1. GitHubにリポジトリをプッシュします
2. [Streamlit Cloud](https://streamlit.io/cloud)にアクセスします
3. 「New app」をクリックし、リポジトリを選択します
4. 必要に応じてシークレット（API KEYなど）を設定します

## 注意事項

- API Keyは安全に管理してください
- 本番環境では`.streamlit/secrets.toml`またはStreamlit Cloudのシークレット機能を使用することをお勧めします

## ライセンス

MIT

## 謝辞

- このアプリケーションはStreamlitとDifyを使用して構築されています
- ブラジリアン柔術のナレッジベースは専門家の監修のもと作成されています 