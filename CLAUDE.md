# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains OAuth integration testing components for Snowflake authentication, with two main implementation paths:

1. **Snowflake Native OAuth** (`python_web_app/`) - Direct OAuth with Snowflake using PKCE
2. **External OAuth via Okta** (`exteral_oauth/`) - Okta as OAuth provider with Snowflake integration

## Development Commands

### Python Web App
```bash
# Setup
cd python_web_app
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials

# Run the Flask application
python app.py
# Application runs on http://127.0.0.1:5000
```

### Terraform Infrastructure
```bash
# Okta OAuth setup
cd exteral_oauth/terraform/okta
terraform init
terraform plan
terraform apply
```

## Architecture

### Python Web App (Snowflake Native OAuth)
- **Flask application** with PKCE-compliant OAuth 2.0 flow
- **Token management**: Automatic refresh with 5-minute buffer before expiration
- **Snowflake integration**: Direct SQL execution with OAuth token authentication
- **Session handling**: State management for OAuth flow security

Key components:
- `app.py`: Main Flask application with OAuth flow implementation
- `tokens.json`: Local token storage (access + refresh tokens)
- Templates in `templates/`: HTML UI for login/dashboard

### External OAuth (Okta Integration)
- **Terraform configuration** for Okta authorization server setup
- **Snowflake External OAuth** integration via SQL configuration
- **Google Apps Script** redirect URI support

Key files:
- `exteral_oauth/sql/oauth_integration.sql`: Snowflake external OAuth setup
- `exteral_oauth/terraform/okta/`: Terraform configs for Okta auth server, policies, and scopes

## Configuration Requirements

### Environment Variables (.env)
```
SNOWFLAKE_CLIENT_ID=<oauth_client_id>
SNOWFLAKE_CLIENT_SECRET=<oauth_client_secret>
SNOWFLAKE_ACCOUNT_IDENTIFIER=<account_name>
SNOWFLAKE_WAREHOUSE=<warehouse_name>
FLASK_SECRET_KEY=<random_secret>
```

### Snowflake OAuth Integration
For native OAuth, create integration with:
- Redirect URI: `http://127.0.0.1:5000/callback`
- PKCE enforcement enabled
- Refresh token support

### Okta Configuration
Terraform variables needed:
- `okta_org_name`: Okta organization name
- `okta_api_token`: API token for Terraform operations
- `script_id`: Google Apps Script ID for redirect handling

## Security Notes

- Tokens stored locally in plain text (development only)
- PKCE implementation prevents authorization code interception
- Automatic token refresh prevents session interruption
- State parameter validation prevents CSRF attacks

## Cognito + Snowflake External OAuth 重要な知見

### 最終解決策 - Access Token使用（OAuth標準）
- **Pre Token Generation v2.0**: `lambda_version = "V2_0"` 設定で Access Token にクレーム追加可能
- **Advanced Security Features**: 不要（2024年11月22日以前作成のUser Poolの場合）
- **Access Token**: `aud`と`scp`クレーム両方が必要
- **成功パターン**: Access Token でSnowflake認証（OAuth 2.0標準）

### 問題と解決の経緯
1. **初期問題**: Cognitoスコープ `session/role-any` → Snowflakeは `session:role-any` を期待
2. **v1.0解決**: ID Token に `scp: "session:role-any"` 追加で成功
3. **v2.0課題**: Access Token に `scp` は追加されるが `aud` クレームが不足
4. **最終解決**: Access Token に `aud` と `scp` 両方追加で成功

### Lambda Trigger v2.0 設定
- 関数: `snowflake-cognito-oauth-pre-token-generation`
- バージョン: `V2_0`
- 役割: Access Token と ID Token 両方にクレーム追加
- 重要クレーム:
  - `scp: "session:role-any"` (両トークン)
  - `aud: "{client_id}"` (Access Token のみ追加)

### Snowflake統合設定
- `EXTERNAL_OAUTH_AUDIENCE_LIST = ('{client_id}')`
- `EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'username'`
- `EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE'`

### Access Token vs ID Token クレーム比較
**Access Token** (API アクセス用):
- `aud`: Client ID (必須)
- `scp`: "session:role-any" (Lambda で追加)
- `username`: ユーザー名 (Snowflake マッピング用)
- `scope`: "openid profile session/role-any email"

**ID Token** (ユーザー身元確認用):
- `aud`: Client ID (自動)
- `scp`: "session:role-any" (Lambda で追加)
- `cognito:username`: ユーザー名
- `email`, `at_hash` など