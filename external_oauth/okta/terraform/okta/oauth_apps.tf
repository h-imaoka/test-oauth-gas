resource "okta_app_oauth" "gas_web_app" {
  label                      = "GAS snowflake OAuth"
  type                       = "web"
  redirect_uris              = ["https://script.google.com/macros/d/${var.script_id}/usercallback"]
  response_types             = ["code"]
  grant_types                = ["authorization_code", "refresh_token"]
  token_endpoint_auth_method = "client_secret_basic"
  consent_method             = "REQUIRED"
  issuer_mode                = "DYNAMIC"
}
