# Lambda関数のZIPファイル作成
data "archive_file" "pre_token_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/pre_token_generation.py"
  output_path = "${path.module}/pre_token_generation.zip"
}

# Lambda実行ロール
resource "aws_iam_role" "pre_token_lambda_role" {
  name = "${var.project_name}-pre-token-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda基本実行ポリシーをアタッチ
resource "aws_iam_role_policy_attachment" "pre_token_lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.pre_token_lambda_role.name
}

# Lambda関数
resource "aws_lambda_function" "pre_token_generation" {
  filename      = data.archive_file.pre_token_lambda_zip.output_path
  function_name = "${var.project_name}-pre-token-generation"
  role          = aws_iam_role.pre_token_lambda_role.arn
  handler       = "pre_token_generation.lambda_handler"
  runtime       = "python3.9"
  timeout       = 10

  environment {
    variables = {
      COGNITO_CLIENT_ID = var.cognito_client_id
    }
  }

  source_code_hash = data.archive_file.pre_token_lambda_zip.output_base64sha256

  tags = {
    Name        = "${var.project_name}-pre-token-generation"
    Environment = "development"
    Purpose     = "cognito-token-generation"
  }
}

# Cognito User PoolにLambda実行権限を付与
resource "aws_lambda_permission" "cognito_invoke_pre_token" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_token_generation.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.snowflake_oauth.arn
}
