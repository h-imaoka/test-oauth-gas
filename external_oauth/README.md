# External OAuth Integration (Okta + GAS + Snowflake)

Okta外部OAuth認証を使用してGoogle Apps Script（GAS）経由でSnowflakeにアクセスするためのセットアップです。

## アーキテクチャ

```
GAS ←→ Okta (OAuth Provider) ←→ Snowflake (External OAuth Integration)
```

- **Okta**: OAuth認証プロバイダー
- **GAS**: Webアプリとしてトークン取得・管理
- **Snowflake**: External OAuth統合でOktaトークンを受け入れ

## セットアップ手順

### 1. Terraform でOkta設定

```bash
cd terraform/okta
terraform init
terraform plan
terraform apply
```

必要な変数：
- `okta_org_name`: Okta組織名
- `okta_api_token`: Okta API トークン
- `script_id`: Google Apps Script ID

### 2. Snowflake External OAuth Integration

```sql
-- sql/oauth_integration.sql を実行
CREATE SECURITY INTEGRATION okta_oauth_integration
  TYPE = EXTERNAL_OAUTH
  ENABLED = TRUE
  EXTERNAL_OAUTH_TYPE = OKTA
  EXTERNAL_OAUTH_ISSUER = 'https://{okta_org_name}.okta.com/oauth2/default'
  EXTERNAL_OAUTH_JWS_KEYS_URL = 'https://{okta_org_name}.okta.com/oauth2/default/v1/keys'
  EXTERNAL_OAUTH_AUDIENCE_LIST = ('api://default')
  EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
  EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'LOGIN_NAME';
```

### 3. Google Apps Script デプロイ

1. `gas/.clasp.json`のscriptIdを実際のIDに変更
2. スクリプトプロパティを設定：
   - `OKTA_DOMAIN`: Okta組織ドメイン
   - `OKTA_CLIENT_ID`: OktaアプリのクライアントID
   - `OKTA_CLIENT_SECRET`: OktaアプリのクライアントSecret

```bash
cd gas
clasp push
clasp deploy
```

## 使用方法

1. **GAS Webアプリにアクセス** - デプロイ後のURLを開く
2. **Okta認証** - "Okta で認可してトークン取得"をクリック
3. **トークン確認** - Access Token、Refresh Token、有効期限を表示
4. **Snowflake接続** - 取得したトークンでSnowflakeにアクセス

## 機能

### OAuth フロー
- **PKCE対応**: セキュアなOAuth 2.0認証
- **スコープ**: `openid profile email offline_access session:role-any`
- **自動リフレッシュ**: Refresh Tokenによる長期認証維持

### セキュリティ機能
- トークン表示の部分マスク化
- スクリプトプロパティでの機密情報管理
- アクセス制限（デプロイユーザーのみ）

## ファイル構成

```
external_oauth/
├── terraform/okta/     # Okta OAuth設定（Terraform）
│   ├── auth_server.tf  # 認証サーバー・ポリシー設定
│   ├── oauth_apps.tf   # OAuthアプリケーション設定
│   └── variables.tf    # 変数定義
├── sql/                # Snowflake設定
│   └── oauth_integration.sql  # External OAuth統合SQL
└── gas/                # Google Apps Script
    ├── get_token.js    # OAuth認証・トークン管理
    ├── appsscript.json # GASマニフェスト
    └── .clasp.json     # clasp設定（要ID設定）
```

## 注意事項

- **Okta設定**: 組織内ユーザーのみアクセス可能
- **トークン管理**: GAS上でユーザープロパティに保存
- **ロール制限**: `session:role-any`で複数ロール対応
- **セキュリティ**: 本番環境では適切な権限設定が必要