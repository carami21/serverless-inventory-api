import os
import pytest
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient

# Set env vars BEFORE importing app so database.py picks them up
os.environ["DYNAMODB_TABLE"] = "Products"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"

from src.main import app  # noqa: E402
from src import database  # noqa: E402


def _create_table(client):
    """Helper to create the Products table with GSI inside a moto context."""
    client.create_table(
        TableName="Products",
        KeySchema=[{"AttributeName": "productId", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "productId", "AttributeType": "S"},
            {"AttributeName": "category", "AttributeType": "S"},
            {"AttributeName": "price", "AttributeType": "N"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "CategoryPriceIndex",
                "KeySchema": [
                    {"AttributeName": "category", "KeyType": "HASH"},
                    {"AttributeName": "price", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def mock_dynamodb():
    """
    Spins up a moto-mocked DynamoDB with the Products table.
    Resets the lazy table reference before/after so moto patches cleanly.
    """
    database.reset_table()
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        _create_table(client)
        yield
    database.reset_table()


@pytest.fixture
def client(mock_dynamodb):
    """FastAPI TestClient with mocked DynamoDB active."""
    return TestClient(app)


@pytest.fixture
def sample_product_payload():
    return {
        "name": "Mechanical Keyboard",
        "category": "electronics",
        "price": 129.99,
        "description": "TKL layout, Cherry MX Blue switches",
        "stock": 50,
    }


@pytest.fixture
def created_product(client, sample_product_payload):
    """Convenience fixture: creates a product and returns the response JSON."""
    response = client.post("/api/v1/products", json=sample_product_payload)
    assert response.status_code == 201
    return response.json()
