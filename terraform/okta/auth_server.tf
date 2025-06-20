resource "okta_auth_server_default" "default" {
  audiences                 = ["api://default"]
  description               = "Default Authorization Server for your Applications"
  credentials_rotation_mode = "AUTO"
  issuer_mode               = "ORG_URL"
}


#data "okta_auth_server_scopes" "scopes" {
#  auth_server_id = "default"
#}

# output "scopes" {
#   value = [
#     for s in data.okta_auth_server_scopes.scopes.scopes : {
#       name = s.name
#       id   = s.id
#     }
#   ]
# }

# output "auth_server_id" {
#   value = okta_auth_server_default.default.id
# }

resource "okta_auth_server_scope" "role-any" {
  auth_server_id   = okta_auth_server_default.default.id
  metadata_publish = "NO_CLIENTS"
  name             = "session:role-any"
  consent          = "IMPLICIT"
  display_name     = "Any Snowflake Roles"
}

resource "okta_auth_server_policy" "snowflake_oauth" {
  auth_server_id   = okta_auth_server_default.default.id
  name             = "snowflake"
  description      = "snowflake用のポリシー"
  client_whitelist = [okta_app_oauth.gas_web_app.id]
  priority         = 1
}

resource "okta_auth_server_policy_rule" "snowflake_oauth" {
  auth_server_id  = okta_auth_server_default.default.id
  policy_id       = okta_auth_server_policy.snowflake_oauth.id
  name            = "Allow Auth Code for GAS"
  priority        = 1
  group_whitelist = ["EVERYONE"] # or snowflake-group

  grant_type_whitelist = [
    "authorization_code",
    "client_credentials",
    "urn:ietf:params:oauth:grant-type:device_code",
    "urn:ietf:params:oauth:grant-type:token-exchange",
  ]

  scope_whitelist = [
    "address",
    "email",
    "offline_access",
    "openid",
    "phone",
    "profile",
    "session:role-any", # This is the custom scope we created for Snowflake roles
  ]
  refresh_token_lifetime_minutes = 129600 # 90 days
}
# }
