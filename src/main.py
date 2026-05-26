from fastapi import FastAPI
from mangum import Mangum
from src.routers import products

app = FastAPI(
    title="Serverless Inventory API",
    description="Cloud-native product inventory management on AWS Lambda + API Gateway + DynamoDB",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(products.router, prefix="/api/v1")

# Lambda handler — Mangum wraps the FastAPI ASGI app for API Gateway (HTTP API)
handler = Mangum(app, lifespan="off")
