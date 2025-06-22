# Cognito User Pool
resource "aws_cognito_user_pool" "snowflake_oauth" {
  name = "${var.project_name}-user-pool"


  # パスワードポリシー
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # アカウント回復設定
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # 自動確認設定
  auto_verified_attributes = ["email"]

  # 既存のschema設定を維持（変更不可のため）
  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true
  }

  schema {
    attribute_data_type      = "String"
    name                     = "snowflake_role"
    required                 = false
    mutable                  = true
    developer_only_attribute = false
  }

  # Lambda Triggers
  lambda_config {
    pre_token_generation_config {
      lambda_arn     = aws_lambda_function.pre_token_generation.arn
      lambda_version = "V2_0"
    }
  }



  tags = {
    Name        = "${var.project_name}-user-pool"
    Environment = "development"
    Purpose     = "snowflake-oauth"
  }

  lifecycle {
    ignore_changes = [schema] # schemaは本当はsetで指定すべきだがprovider実装が糞で 無限drift状態になる、仕方なくignore_changesを設定
  }
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "snowflake_oauth" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.snowflake_oauth.id
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "snowflake_oauth" {
  name         = "${var.project_name}-client"
  user_pool_id = aws_cognito_user_pool.snowflake_oauth.id

  # OAuth設定
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "profile", "email"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls
  supported_identity_providers         = ["COGNITO"]

  # Client Secret設定
  generate_secret = true # サーバーサイドアプリのためtrue

  # トークン有効期限
  access_token_validity  = 60 # 60分
  id_token_validity      = 60 # 60分  
  refresh_token_validity = 30 # 30日

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # セッション設定
  prevent_user_existence_errors = "ENABLED"

  # 読み取り・書き込み属性
  read_attributes  = ["email", "custom:snowflake_role"]
  write_attributes = ["email", "custom:snowflake_role"]
}

# Resource Server (カスタムスコープ用)
resource "aws_cognito_resource_server" "snowflake_oauth" {
  identifier   = "session" # よりシンプルに
  name         = "Snowflake Session Resource Server"
  user_pool_id = aws_cognito_user_pool.snowflake_oauth.id

  scope {
    scope_name        = "role-any"
    scope_description = "Access any Snowflake role"
  }

  scope {
    scope_name        = "role:analyst"
    scope_description = "Access Snowflake ANALYST role"
  }

  scope {
    scope_name        = "role:public"
    scope_description = "Access Snowflake PUBLIC role"
  }

  scope {
    scope_name        = "role:sales"
    scope_description = "Access Snowflake SALES role"
  }
}

# App Client用にカスタムスコープを追加
resource "aws_cognito_user_pool_client" "snowflake_oauth_with_custom_scopes" {
  name         = "${var.project_name}-client-custom-scopes"
  user_pool_id = aws_cognito_user_pool.snowflake_oauth.id

  # OAuth設定
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = [
    "openid",
    "profile",
    "email",
    "session/role-any",
    "session/role:analyst",
    "session/role:public",
    "session/role:sales"
  ]
  callback_urls                = var.callback_urls
  logout_urls                  = var.logout_urls
  supported_identity_providers = ["COGNITO"]

  # Client Secret設定
  generate_secret = true

  # トークン有効期限
  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  prevent_user_existence_errors = "ENABLED"
  read_attributes               = ["email", "custom:snowflake_role"]
  write_attributes              = ["email", "custom:snowflake_role"]

  depends_on = [aws_cognito_resource_server.snowflake_oauth]
}
