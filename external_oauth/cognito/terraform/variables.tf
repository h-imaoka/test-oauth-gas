variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "snowflake-cognito-oauth"
}

variable "cognito_domain_prefix" {
  description = "Cognito domain prefix (must be globally unique)"
  type        = string
}

variable "callback_urls" {
  description = "List of callback URLs for OAuth"
  type        = list(string)
  default     = ["http://localhost:5000/callback"]
}

variable "logout_urls" {
  description = "List of logout URLs"
  type        = list(string)
  default     = ["http://localhost:5000/logout"]
}