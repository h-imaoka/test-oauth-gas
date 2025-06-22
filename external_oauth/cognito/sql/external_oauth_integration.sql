-- AWS Cognito External OAuth Integration for Snowflake
-- 
-- Prerequisites:
-- 1. Deploy Cognito User Pool via Terraform
-- 2. Replace {aws_region} and {user_pool_id} with actual values from Terraform output
-- 3. Ensure Snowflake user login names match Cognito user 'sub' claim

-- Create External OAuth Integration
CREATE OR REPLACE SECURITY INTEGRATION cognito_oauth_integration
  TYPE = EXTERNAL_OAUTH
  ENABLED = TRUE
  EXTERNAL_OAUTH_TYPE = CUSTOM
  EXTERNAL_OAUTH_ISSUER = 'https://cognito-idp.{aws_region}.amazonaws.com/{user_pool_id}'
  EXTERNAL_OAUTH_JWS_KEYS_URL = 'https://cognito-idp.{aws_region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
  EXTERNAL_OAUTH_AUDIENCE_LIST = ('{client_id}')
  EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'username'
  EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'LOGIN_NAME'
  EXTERNAL_OAUTH_SCOPE_DELIMITER = ' ';

-- Enable any role mode (allows role switching)
ALTER SECURITY INTEGRATION cognito_oauth_integration
  SET EXTERNAL_OAUTH_ANY_ROLE_MODE = 'ENABLE';

-- Grant usage to appropriate roles
-- GRANT USAGE ON INTEGRATION cognito_oauth_integration TO ROLE SYSADMIN;
-- GRANT USAGE ON INTEGRATION cognito_oauth_integration TO ROLE ACCOUNTADMIN;

-- Show integration details
DESC SECURITY INTEGRATION cognito_oauth_integration;
