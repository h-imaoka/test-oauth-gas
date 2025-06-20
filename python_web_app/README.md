# Snowflake OAuth Web App

Snowflake OAuth認証を使用してSQL実行を行うシンプルなWebアプリケーションです。

## セットアップ

1. 依存関係をインストール:
   ```bash
   pip install -r requirements.txt
   ```

2. 環境変数を設定:
   `.env.example`を`.env`にコピーして、以下の値を設定してください:
   ```
   SNOWFLAKE_CLIENT_ID=your_client_id_here
   SNOWFLAKE_CLIENT_SECRET=your_client_secret_here
   SNOWFLAKE_ACCOUNT_IDENTIFIER=your_account_identifier_here
   FLASK_SECRET_KEY=your_flask_secret_key_here
   ```

3. Snowflake OAuth Integration設定:
   - Snowflakeで新しいOAuth integrationを作成
   - リダイレクトURI: `http://0.0.0.0:5000/callback`
   - スコープ: `session:role-any`

## 実行

```bash
python app.py
```

アプリケーションは `http://0.0.0.0:5000` で起動します。

## 機能

- Snowflake OAuth認証
- SQL実行とテーブル形式での結果表示
- トークンのローカルファイル保存
- シンプルなWeb UI

## 注意事項

- このアプリはローカル開発用です
- トークンは`tokens.json`ファイルに保存されます
- プロダクション使用時は適切なセキュリティ対策を実装してください