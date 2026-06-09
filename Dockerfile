# Lambda container image. Same code runs locally via uvicorn (see Makefile).
FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY sql ./sql

# API Gateway -> Mangum -> FastAPI
CMD ["app.lambda_handler.handler"]
