output "user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.snowflake_oauth.id
}

output "user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.snowflake_oauth.arn
}

output "client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.snowflake_oauth_with_custom_scopes.id
}

output "client_secret" {
  description = "Cognito User Pool Client Secret"
  value       = aws_cognito_user_pool_client.snowflake_oauth_with_custom_scopes.client_secret
  sensitive   = true
}

output "client_id_basic" {
  description = "Basic Cognito User Pool Client ID (without custom scopes)"
  value       = aws_cognito_user_pool_client.snowflake_oauth.id
}

output "cognito_domain" {
  description = "Cognito Domain"
  value       = aws_cognito_user_pool_domain.snowflake_oauth.domain
}

output "authorization_endpoint" {
  description = "OAuth Authorization Endpoint"
  value       = "https://${aws_cognito_user_pool_domain.snowflake_oauth.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/authorize"
}

output "token_endpoint" {
  description = "OAuth Token Endpoint"
  value       = "https://${aws_cognito_user_pool_domain.snowflake_oauth.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/token"
}

output "jwks_uri" {
  description = "JWKS URI for token validation"
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.snowflake_oauth.id}/.well-known/jwks.json"
}

output "issuer" {
  description = "JWT Issuer"
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.snowflake_oauth.id}"
}

output "userinfo_endpoint" {
  description = "UserInfo Endpoint"
  value       = "https://${aws_cognito_user_pool_domain.snowflake_oauth.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/userInfo"
}