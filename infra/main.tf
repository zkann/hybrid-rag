# Deploy path: RDS Postgres (pgvector) + container-image Lambda (FastAPI via
# Mangum) + API Gateway HTTP API, in the account's default VPC.
#
# This provisions PAID resources (RDS is not free-tier-forever). Review and run
# deliberately. See DEPLOY.md for the build-push-apply order.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# --- networking: lambda -> rds on 5432 only ---------------------------------
resource "aws_security_group" "lambda" {
  name_prefix = "${var.project}-lambda-"
  vpc_id      = data.aws_vpc.default.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.project}-rds-"
  vpc_id      = data.aws_vpc.default.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }
}

# --- database ----------------------------------------------------------------
resource "aws_db_subnet_group" "this" {
  name       = "${var.project}-subnets"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "this" {
  identifier             = "${var.project}-db"
  engine                 = "postgres"
  engine_version         = "17.10"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  skip_final_snapshot     = true
  apply_immediately       = true
}

# --- container registry for the lambda image ---------------------------------
resource "aws_ecr_repository" "app" {
  name                 = var.project
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# --- lambda ------------------------------------------------------------------
resource "aws_iam_role" "lambda" {
  name_prefix = "${var.project}-lambda-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_function" "api" {
  function_name = "${var.project}-api"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = 30
  memory_size   = 1024

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DATABASE_URL      = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.this.address}:5432/${var.db_name}"
      OPENAI_API_KEY    = var.openai_api_key
      ANTHROPIC_API_KEY = var.anthropic_api_key
      GEN_PROVIDER      = var.gen_provider
    }
  }
}

# --- http api ----------------------------------------------------------------
resource "aws_apigatewayv2_api" "http" {
  name          = "${var.project}-http"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
