# AWS Cognito + Snowflake External OAuth Integration

AWS CognitoをOAuthプロバイダーとしてSnowflakeで外部OAuth認証を実装するためのサンプルプロジェクト。

## 🎯 成功した構成

- **OAuth標準**: Access TokenでSnowflake認証
- **Pre Token Generation v2.0**: Access TokenとID Token両方にカスタムクレーム追加
- **Advanced Security Features**: 不要（既存User Pool使用時）

## アーキテクチャ

```
Flask Client App ←→ AWS Cognito (OAuth Provider) ←→ Snowflake (External OAuth Integration)
```

- **AWS Cognito**: カスタムスコープ対応のOAuth 2.0プロバイダー
- **Flask App**: PKCE対応クライアントアプリケーション
- **Snowflake**: External OAuth統合でCognitoトークンを受け入れ

## セットアップ手順

### 1. AWS Cognito デプロイ（Terraform）

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvarsを編集して適切な値を設定
terraform init
terraform plan
terraform apply
```

**必要な設定:**
- `cognito_domain_prefix`: グローバルで一意なドメインプレフィックス
- `aws_region`: AWSリージョン
- `callback_urls`: OAuth コールバックURL

### 2. Snowflake External OAuth Integration

```bash
# Terraformの出力値を確認
terraform output

# SQLファイルのプレースホルダーを置換
# sql/external_oauth_integration.sql を編集
```

必要な置換:
- `{aws_region}`: AWSリージョン
- `{user_pool_id}`: Cognito User Pool ID
- `{client_id}`: Cognito Client ID

```sql
-- Snowflakeで実行
CREATE OR REPLACE SECURITY INTEGRATION cognito_oauth_integration
  TYPE = EXTERNAL_OAUTH
  ENABLED = TRUE
  EXTERNAL_OAUTH_TYPE = CUSTOM
  EXTERNAL_OAUTH_ISSUER = 'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_XXXXXXXXX'
  -- ...
```

### 3. クライアントアプリケーション セットアップ

```bash
cd client_app
pip install -r requirements.txt
cp .env.example .env
# .envファイルを編集
python app.py
```

## 機能

### OAuth認証フロー
- **Client Secret認証**: サーバーサイドアプリ向けセキュアなOAuth 2.0認証
- **カスタムスコープ**: `snowflake-api/session:role:ROLE_NAME`
- **ロール指定**: ログイン時に使用するSnowflakeロールを指定可能
- **JWT Token表示**: 認証情報の詳細表示

### Snowflake統合
- **External OAuth**: CognitoトークンでSnowflake認証
- **自動ロールマッピング**: JWT subクレームとSnowflakeユーザーのマッピング
- **SQL実行**: 認証されたユーザーでのクエリ実行

### セキュリティ機能
- **トークン自動更新**: Refresh Tokenによる長期認証維持
- **期限管理**: トークン期限の5分前に自動リフレッシュ
- **セッション管理**: Flask セッションでOAuth状態管理

## 🔧 重要な技術的知見

### 最小構成での実装

**必要最小限の構成**（シンプルなsession:role-any追加の場合）:
- **User Pool**: 基本設定のみ
- **User Pool Client**: 標準スコープ (`openid profile email`) のみ
- **Lambda**: Pre Token Generation v2.0 で `scp: "session:role-any"` 追加

**不要な複雑な設定**:
- ❌ Resource Server（カスタムスコープ定義）
- ❌ Custom Scopes Client（複雑なスコープ設定）
- ❌ Advanced Security Features

**理由**: Lambda で直接 `scp` クレーム追加するため、Cognito側でのカスタムスコープ定義は不要

### Pre Token Generation Lambda v2.0

**lambda_version = "V2_0"** 設定により:
- Access Token にカスタムクレーム追加可能
- ID Token にもカスタムクレーム追加可能
- Advanced Security Features は不要（既存User Pool）

```python
# 最小構成のLambda関数
def lambda_handler(event, context):
    event['response']['claimsAndScopeOverrideDetails'] = {
        'idTokenGeneration': {
            'claimsToAddOrOverride': {'scp': 'session:role-any'}
        },
        'accessTokenGeneration': {
            'claimsToAddOrOverride': {
                'scp': 'session:role-any',
                'aud': 'CLIENT_ID'  # 必須: Snowflakeのaud検証用
            }
        }
    }
    return event
```

### 必須クレーム

**Access Token** (Snowflake認証用):
- `aud`: Client ID（Snowflakeが検証）
- `scp`: "session:role-any"（スコープマッピング）
- `username`: ユーザーマッピング用

**ID Token** (ユーザー身元確認用):
- `aud`: Client ID（自動付与）
- `scp`: "session:role-any"（Lambda追加）
- `cognito:username`: ユーザー名

## カスタムスコープ

Cognitoで定義されるカスタムスコープ:

```
session/role-any        # 任意のロールアクセス
session/role:analyst    # ANALYSTロール専用
session/role:sales      # SALESロール専用
```

## ファイル構成

```
cognito/
├── terraform/                    # インフラストラクチャ
│   ├── provider.tf              # Terraform provider設定
│   ├── variables.tf             # 変数定義
│   ├── cognito.tf               # Cognito User Pool/Client設定
│   ├── outputs.tf               # 出力値
│   └── terraform.tfvars.example # 設定例
├── sql/                         # Snowflake設定
│   └── external_oauth_integration.sql
├── client_app/                  # Flask クライアントアプリ
│   ├── app.py                   # メインアプリケーション
│   ├── requirements.txt         # Python依存関係
│   ├── .env.example            # 環境変数例
│   └── templates/              # HTMLテンプレート
│       ├── base.html
│       ├── login.html
│       └── dashboard.html
└── README.md                   # このファイル
```

## 環境変数

`.env`ファイルで設定する環境変数:

```bash
COGNITO_CLIENT_ID=your_cognito_client_id
COGNITO_CLIENT_SECRET=your_cognito_client_secret
COGNITO_DOMAIN=your-unique-domain-prefix
AWS_REGION=us-west-2
SNOWFLAKE_ACCOUNT_IDENTIFIER=your_account.region
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
FLASK_SECRET_KEY=your_secret_key
```

## 使用方法

1. **ログイン画面でロール指定** - 使用したいSnowflakeロールを入力（オプション）
2. **Cognito認証** - AWSのログイン画面でユーザー認証
3. **トークン取得** - JWT Access Token + Refresh Token取得
4. **Snowflake接続** - External OAuth統合でSnowflakeアクセス
5. **SQL実行** - 認証済みユーザーでのクエリ実行

## 🐛 トラブルシューティング

### "Invalid OAuth access token" エラー
- **原因**: Access Tokenに `aud` クレームが不足
- **解決**: Lambda関数でAccess Tokenに `aud` 追加
- **確認**: `DESC SECURITY INTEGRATION` でAudience設定確認

### Lambda Triggerが動作しない
- **バージョン確認**: `lambda_version = "V2_0"` 設定
- **権限確認**: Lambda実行ロールのIAM権限
- **ログ確認**: CloudWatch Logsでエラー詳細確認

### スコープ変換問題
- **Cognito**: `session/role-any` (スラッシュ)
- **Snowflake**: `session:role-any` (コロン)
- **解決**: Lambda関数で自動変換

### よくある問題

1. **ドメインプレフィックス重複**: Cognitoドメインは全AWSでユニーク
2. **JWKS URL不一致**: Snowflake統合のJWKS URLが正しく設定されているか確認
3. **ユーザーマッピング**: Snowflakeユーザー名とCognito `username` クレームの対応

### デバッグ情報

- JWT Token内容は `dashboard.html` で確認可能
- Flask アプリのデバッグモードでエラー詳細を確認
- Snowflake `DESC SECURITY INTEGRATION cognito_oauth_integration` で統合状態確認

## 注意事項

- **開発用途**: ローカル開発環境での使用を想定
- **Cognito料金**: MAU（月間アクティブユーザー）による従量課金
- **JWT検証**: 本番環境では適切なJWT署名検証が必要
- **ロール管理**: Snowflakeでユーザーへの適切なロール付与が必要

## 📊 動作フロー

1. **認証開始**: ブラウザ → Cognito OAuth認証
2. **コールバック**: Cognito → Client App  
3. **トークン取得**: Authorization Code → Access/ID Token
4. **Lambda実行**: Pre Token Generation v2.0でクレーム追加
5. **Snowflake接続**: Access Token → Snowflake External OAuth
6. **SQL実行**: 認証済みセッションでクエリ実行