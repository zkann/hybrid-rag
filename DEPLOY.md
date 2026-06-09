# Deploy to AWS

Provisions RDS Postgres (pgvector) + a container-image Lambda (FastAPI via
Mangum) + an API Gateway HTTP API. **RDS is a paid resource (~$12-15/mo for
`db.t4g.micro`); this is not free-tier-forever.** Run deliberately.

Prereqs: AWS credentials configured (`aws sts get-caller-identity` works),
Docker, Terraform, an OpenAI key, an Anthropic key.

## 1. Create the ECR repo first

```bash
cd infra
terraform init
terraform apply -target=aws_ecr_repository.app \
  -var="db_password=$(openssl rand -hex 16)" \
  -var="image_uri=placeholder" \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="anthropic_api_key=$ANTHROPIC_API_KEY"
ECR_URL=$(terraform output -raw ecr_repo_url)
```

## 2. Build and push the image

```bash
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin "${ECR_URL%/*}"
docker build --platform linux/amd64 -t "$ECR_URL:latest" ..
docker push "$ECR_URL:latest"
```

## 3. Apply the rest

```bash
terraform apply \
  -var="db_password=<same-as-step-1>" \
  -var="image_uri=$ECR_URL:latest" \
  -var="openai_api_key=$OPENAI_API_KEY" \
  -var="anthropic_api_key=$ANTHROPIC_API_KEY"
API=$(terraform output -raw api_url)
```

The app applies its own schema on cold start (`ensure_schema()`), so the
`vector` extension and tables are created on first request.

## 4. Seed the index (one time)

Ingestion runs from your machine against the RDS endpoint. Either open the RDS
SG to your IP temporarily, or run the seed from a bastion / Cloud9 in the VPC:

```bash
DATABASE_URL="postgresql://rag:<pw>@<rds-endpoint>:5432/rag" \
  python -m scripts.ingest_docs --dir docs_corpus
```

## 5. Use it

```bash
curl "$API/health"
curl -s "$API/ask" -H 'content-type: application/json' \
  -d '{"query":"How do I add a dependency to a path operation?"}' | jq
```

## Teardown (stop paying)

```bash
terraform destroy -var="db_password=<pw>" -var="image_uri=$ECR_URL:latest" \
  -var="openai_api_key=x" -var="anthropic_api_key=x"
```
