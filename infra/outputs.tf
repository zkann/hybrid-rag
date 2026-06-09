output "api_url" {
  value       = aws_apigatewayv2_api.http.api_endpoint
  description = "Base URL of the deployed API."
}

output "ecr_repo_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "Push the Lambda image here, then set image_uri."
}

output "db_endpoint" {
  value       = aws_db_instance.this.address
  description = "RDS endpoint (private)."
}
