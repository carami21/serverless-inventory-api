"""
Unit tests for database.py helper functions.
Uses moto to mock DynamoDB — no AWS credentials required.
"""
from src import database


class TestGetProduct:
    def test_returns_none_for_missing(self, mock_dynamodb):
        database.reset_table()
        result = database.get_product("nonexistent-id")
        assert result is None

    def test_returns_item_after_put(self, mock_dynamodb):
        database.reset_table()
        item = {
            "productId": "test-001",
            "name": "Widget",
            "category": "misc",
            "price": 9.99,
            "description": None,
            "stock": 5,
            "createdAt": "2025-01-01T00:00:00+00:00",
            "updatedAt": "2025-01-01T00:00:00+00:00",
        }
        database.put_product(item)
        result = database.get_product("test-001")
        assert result is not None
        assert result["productId"] == "test-001"
        assert result["name"] == "Widget"

    def test_price_is_float(self, mock_dynamodb):
        database.reset_table()
        item = {
            "productId": "test-002",
            "name": "Gadget",
            "category": "tech",
            "price": 49.99,
            "description": None,
            "stock": 10,
            "createdAt": "2025-01-01T00:00:00+00:00",
            "updatedAt": "2025-01-01T00:00:00+00:00",
        }
        database.put_product(item)
        result = database.get_product("test-002")
        assert isinstance(result["price"], float)

    def test_stock_is_int(self, mock_dynamodb):
        database.reset_table()
        item = {
            "productId": "test-003",
            "name": "Thing",
            "category": "misc",
            "price": 1.99,
            "description": None,
            "stock": 7,
            "createdAt": "2025-01-01T00:00:00+00:00",
            "updatedAt": "2025-01-01T00:00:00+00:00",
        }
        database.put_product(item)
        result = database.get_product("test-003")
        assert isinstance(result["stock"], int)


class TestDeleteProduct:
    def test_delete_existing_returns_true(self, mock_dynamodb):
        database.reset_table()
        item = {
            "productId": "del-001",
            "name": "Temp",
            "category": "x",
            "price": 1.0,
            "description": None,
            "stock": 1,
            "createdAt": "2025-01-01T00:00:00+00:00",
            "updatedAt": "2025-01-01T00:00:00+00:00",
        }
        database.put_product(item)
        result = database.delete_product("del-001")
        assert result is True

    def test_delete_nonexistent_returns_false(self, mock_dynamodb):
        database.reset_table()
        result = database.delete_product("ghost-999")
        assert result is False

    def test_deleted_item_not_retrievable(self, mock_dynamodb):
        database.reset_table()
        item = {
            "productId": "del-002",
            "name": "Gone",
            "category": "x",
            "price": 1.0,
            "description": None,
            "stock": 0,
            "createdAt": "2025-01-01T00:00:00+00:00",
            "updatedAt": "2025-01-01T00:00:00+00:00",
        }
        database.put_product(item)
        database.delete_product("del-002")
        assert database.get_product("del-002") is None


class TestListProducts:
    def test_empty_table_returns_empty_list(self, mock_dynamodb):
        database.reset_table()
        items, cursor = database.list_products()
        assert items == []
        assert cursor is None

    def test_returns_all_items(self, mock_dynamodb):
        database.reset_table()
        for i in range(3):
            database.put_product({
                "productId": f"list-{i}",
                "name": f"Product {i}",
                "category": "test",
                "price": float(i + 1),
                "description": None,
                "stock": i,
                "createdAt": "2025-01-01T00:00:00+00:00",
                "updatedAt": "2025-01-01T00:00:00+00:00",
            })
        items, cursor = database.list_products(limit=10)
        assert len(items) == 3

    def test_pagination_returns_cursor(self, mock_dynamodb):
        database.reset_table()
        for i in range(5):
            database.put_product({
                "productId": f"page-{i}",
                "name": f"Product {i}",
                "category": "test",
                "price": float(i + 1),
                "description": None,
                "stock": i,
                "createdAt": "2025-01-01T00:00:00+00:00",
                "updatedAt": "2025-01-01T00:00:00+00:00",
            })
        items, cursor = database.list_products(limit=2)
        assert len(items) == 2
        assert cursor is not None

    def test_invalid_cursor_starts_from_beginning(self, mock_dynamodb):
        database.reset_table()
        # Should not raise — just ignore bad cursor
        items, cursor = database.list_products(last_key="not-valid-base64!!!")
        assert isinstance(items, list)


class TestListByCategory:
    def test_filters_by_category(self, mock_dynamodb):
        database.reset_table()
        database.put_product({
            "productId": "cat-1",
            "name": "Laptop",
            "category": "electronics",
            "price": 999.0,
            "description": None,
            "stock": 5,
            "createdAt": "2025-01-01T00:00:00+00:00",
            "updatedAt": "2025-01-01T00:00:00+00:00",
        })
        database.put_product({
            "productId": "cat-2",
            "name": "Desk",
            "category": "furniture",
            "price": 300.0,
            "description": None,
            "stock": 2,
            "createdAt": "2025-01-01T00:00:00+00:00",
            "updatedAt": "2025-01-01T00:00:00+00:00",
        })
        results = database.list_by_category("electronics")
        assert len(results) == 1
        assert results[0]["productId"] == "cat-1"

    def test_max_price_filter(self, mock_dynamodb):
        database.reset_table()
        for price in [10.0, 50.0, 100.0, 200.0]:
            database.put_product({
                "productId": f"price-{int(price)}",
                "name": f"Item {price}",
                "category": "gadgets",
                "price": price,
                "description": None,
                "stock": 1,
                "createdAt": "2025-01-01T00:00:00+00:00",
                "updatedAt": "2025-01-01T00:00:00+00:00",
            })
        results = database.list_by_category("gadgets", max_price=100.0)
        assert all(r["price"] <= 100.0 for r in results)
        assert len(results) == 3
