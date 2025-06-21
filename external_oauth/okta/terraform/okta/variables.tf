variable "okta_org_name" {
  description = "Okta organization name"
  type        = string
}

variable "okta_api_token" {
  description = "Okta API token"
  type        = string
}

variable "script_id" {
  description = "Google Apps Script ID for the OAuth redirect URI"
  type        = string
}
