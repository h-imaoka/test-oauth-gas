# Snowflake OAuth Web App

Snowflake OAuth認証（PKCE対応）を使用してSQL実行を行うWebアプリケーションです。

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
   SNOWFLAKE_WAREHOUSE=your_warehouse_name_here (optional)
   FLASK_SECRET_KEY=your_flask_secret_key_here
   ```

3. Snowflake OAuth Integration設定:
   - Snowflakeで新しいOAuth integrationを作成
   - リダイレクトURI: `http://127.0.0.1:5000/callback`
   - スコープ: `refresh_token` (+ ロール指定時は `session:role:ROLE_NAME`)
   - PKCE必須設定を有効化 (賛否あり)

```sql
CREATE or replace SECURITY INTEGRATION test_oauth_integration
  TYPE = OAUTH
  ENABLED = TRUE
  OAUTH_CLIENT = CUSTOM
  OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
  OAUTH_REDIRECT_URI = 'http://127.0.0.1:5000/callback' 
  OAUTH_ISSUE_REFRESH_TOKENS = TRUE
  OAUTH_REFRESH_TOKEN_VALIDITY = 86400
  OAUTH_ALLOW_NON_TLS_REDIRECT_URI = TRUE -- for dev only
  OAUTH_ENFORCE_PKCE = TRUE;
```

## 実行

```bash
python app.py
```

アプリケーションは `http://127.0.0.1:5000` で起動します。

## 機能

### OAuth認証
- **PKCE対応**: セキュアなOAuth 2.0認証
- **ロール指定認証**: ログイン時に使用するSnowflakeロールを指定可能
- **自動トークン更新**: アクセストークン期限切れ前（5分前）に自動リフレッシュ
- **リフレッシュトークン**: 長期間の認証維持（通常90日）

### SQL実行
- **Warehouse指定**: SQL実行前にwarehouseを指定可能
- **結果表示**: クエリ結果をテーブル形式で表示
- **エラーハンドリング**: SQL実行エラーの詳細表示

### トークン管理
- **ローカル保存**: `tokens.json`にトークンを保存
- **期限管理**: トークン取得時刻と有効期限を記録
- **自動クリーンアップ**: リフレッシュ失敗時の自動ファイル削除

## 技術詳細

### 使用ライブラリ
- **Flask**: Webフレームワーク
- **authlib**: PKCE実装
- **snowflake-connector-python**: Snowflake接続
- **requests**: HTTP通信

### OAuth フロー
1. ログイン画面でロール指定（オプション）
2. PKCE Code Challenge/Verifier生成
3. 指定ロールを含むスコープでSnowflake認証ページへリダイレクト
4. 認証コードとcode_verifierでトークン交換
5. 指定ロール権限付きアクセストークン + リフレッシュトークン取得

### 自動トークン更新
- アクセストークン期限の5分前に自動検出
- リフレッシュトークンで新しいアクセストークンを取得
- 更新失敗時は再ログインを促す

## 注意事項

- **開発用途**: ローカル開発環境での使用を想定
- **セキュリティ**: プロダクション環境では適切なセキュリティ対策が必要
- **トークン保存**: ローカルファイルに平文保存（暗号化推奨）
- **ロール制限**: `ACCOUNTADMIN`, `SECURITYADMIN`等の強力なロールはOAuth制限される場合があります
- **ロール切り替え**: 異なるロール使用時は再ログインが必要
- **エラーログ**: リフレッシュ失敗の詳細はコンソールに出力