import os
import json
import base64
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from typing import Optional

# Config from environment — safe, no hardcoded credentials
AWS_REGION = os.environ.get("AWS_REGION_NAME", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Products")

# Lazy-initialize the DynamoDB resource so moto can patch it in tests
_dynamodb = None
_table = None


def _get_table():
    """Return the DynamoDB table resource, creating it lazily."""
    global _dynamodb, _table
    if _table is None:
        _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        _table = _dynamodb.Table(TABLE_NAME)
    return _table


def reset_table():
    """Force re-initialization of the table reference (used in tests)."""
    global _dynamodb, _table
    _dynamodb = None
    _table = None


def _to_decimal(value: float) -> Decimal:
    """Convert float to Decimal for DynamoDB storage (boto3 resource API requirement)."""
    return Decimal(str(value))


def _from_item(item: dict) -> dict:
    """Convert DynamoDB Decimal types back to Python native float/int for API responses."""
    if item:
        item["price"] = float(item["price"])
        item["stock"] = int(item["stock"])
    return item


def get_product(product_id: str) -> Optional[dict]:
    """Fetch a single product by productId. Returns None if not found."""
    table = _get_table()
    try:
        response = table.get_item(Key={"productId": product_id})
        item = response.get("Item")
        return _from_item(item) if item else None
    except ClientError as e:
        raise RuntimeError(f"DynamoDB get_item failed: {e.response['Error']['Message']}") from e


def put_product(item: dict) -> None:
    """Write a product item to DynamoDB. Converts float/int numerics to Decimal."""
    table = _get_table()
    db_item = dict(item)
    db_item["price"] = _to_decimal(item["price"])
    db_item["stock"] = int(item["stock"])
    try:
        table.put_item(Item=db_item)
    except ClientError as e:
        raise RuntimeError(f"DynamoDB put_item failed: {e.response['Error']['Message']}") from e


def update_product(product_id: str, updates: dict) -> Optional[dict]:
    """
    Partially update a product. Only updates the provided fields.
    Returns the updated item, or None if not found.
    """
    table = _get_table()

    # Build the UpdateExpression dynamically
    update_parts = []
    expr_attr_names = {}
    expr_attr_values = {}

    for key, value in updates.items():
        safe_key = f"#attr_{key}"
        val_key = f":val_{key}"
        update_parts.append(f"{safe_key} = {val_key}")
        expr_attr_names[safe_key] = key
        # DynamoDB boto3 resource requires Decimal, not float
        if key == "price" and isinstance(value, float):
            value = _to_decimal(value)
        expr_attr_values[val_key] = value

    if not update_parts:
        return get_product(product_id)

    update_expression = "SET " + ", ".join(update_parts)

    try:
        response = table.update_item(
            Key={"productId": product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ConditionExpression=Attr("productId").exists(),
            ReturnValues="ALL_NEW",
        )
        item = response.get("Attributes", {})
        return _from_item(item) if item else None
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return None
        raise RuntimeError(f"DynamoDB update_item failed: {e.response['Error']['Message']}") from e


def delete_product(product_id: str) -> bool:
    """
    Delete a product by productId.
    Returns True if the item existed and was deleted, False if not found.
    """
    table = _get_table()
    try:
        table.delete_item(
            Key={"productId": product_id},
            ConditionExpression=Attr("productId").exists(),
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise RuntimeError(f"DynamoDB delete_item failed: {e.response['Error']['Message']}") from e


def list_products(limit: int = 20, last_key: Optional[str] = None) -> tuple[list, Optional[str]]:
    """
    Paginate over all products using a DynamoDB scan.
    Returns (items, next_cursor) where next_cursor is a base64-encoded JSON string.
    """
    table = _get_table()
    scan_kwargs: dict = {"Limit": limit}

    # Decode the pagination cursor if provided
    if last_key:
        try:
            decoded = base64.b64decode(last_key.encode()).decode()
            scan_kwargs["ExclusiveStartKey"] = json.loads(decoded)
        except Exception:
            pass  # Invalid cursor — start from beginning

    try:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        for item in items:
            _from_item(item)

        # Encode the next page cursor
        next_cursor = None
        if "LastEvaluatedKey" in response:
            encoded = base64.b64encode(
                json.dumps(response["LastEvaluatedKey"]).encode()
            ).decode()
            next_cursor = encoded

        return items, next_cursor
    except ClientError as e:
        raise RuntimeError(f"DynamoDB scan failed: {e.response['Error']['Message']}") from e


def list_by_category(category: str, max_price: Optional[float] = None) -> list:
    """
    Query the CategoryPriceIndex GSI to get products in a category,
    optionally filtered by max_price (sort key condition).
    Returns items sorted by price ascending (DynamoDB default sort for GSI).
    """
    table = _get_table()
    query_kwargs: dict = {
        "IndexName": "CategoryPriceIndex",
        "KeyConditionExpression": Key("category").eq(category),
    }

    if max_price is not None:
        query_kwargs["KeyConditionExpression"] = (
            Key("category").eq(category) & Key("price").lte(_to_decimal(max_price))
        )

    try:
        response = table.query(**query_kwargs)
        items = response.get("Items", [])
        for item in items:
            _from_item(item)
        return items
    except ClientError as e:
        raise RuntimeError(f"DynamoDB query failed: {e.response['Error']['Message']}") from e
