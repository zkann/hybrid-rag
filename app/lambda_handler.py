"""AWS Lambda entrypoint. Wraps the FastAPI app with Mangum so the same code
runs locally (uvicorn) and behind API Gateway."""

from mangum import Mangum

from .main import app

handler = Mangum(app)
