variable "region" {
  type    = string
  default = "us-east-2"
}

variable "project" {
  type    = string
  default = "hybrid-rag"
}

variable "db_name" {
  type    = string
  default = "rag"
}

variable "db_username" {
  type    = string
  default = "rag"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro" # smallest; ~\$12-15/mo. Not free.
}

variable "image_uri" {
  type        = string
  description = "ECR image URI for the Lambda (build + push first, see DEPLOY.md)."
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
}

variable "gen_provider" {
  type    = string
  default = "anthropic"
}
