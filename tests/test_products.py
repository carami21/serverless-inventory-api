"""
Product endpoint tests — targets 85%+ coverage.
All DynamoDB calls are mocked via moto (no AWS account needed).
"""
# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_body(self, client):
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "table" in data


# ---------------------------------------------------------------------------
# POST /products — Create
# ---------------------------------------------------------------------------

class TestCreateProduct:
    def test_create_returns_201(self, client, sample_product_payload):
        response = client.post("/api/v1/products", json=sample_product_payload)
        assert response.status_code == 201

    def test_create_returns_correct_fields(self, client, sample_product_payload):
        response = client.post("/api/v1/products", json=sample_product_payload)
        data = response.json()
        assert data["name"] == sample_product_payload["name"]
        assert data["category"] == sample_product_payload["category"]
        assert data["price"] == sample_product_payload["price"]
        assert data["stock"] == sample_product_payload["stock"]
        assert "productId" in data
        assert "createdAt" in data
        assert "updatedAt" in data

    def test_create_assigns_unique_ids(self, client, sample_product_payload):
        r1 = client.post("/api/v1/products", json=sample_product_payload)
        r2 = client.post("/api/v1/products", json=sample_product_payload)
        assert r1.json()["productId"] != r2.json()["productId"]

    def test_create_missing_name_returns_422(self, client):
        payload = {"category": "electronics", "price": 99.99}
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 422

    def test_create_missing_category_returns_422(self, client):
        payload = {"name": "Widget", "price": 9.99}
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 422

    def test_create_negative_price_returns_422(self, client):
        payload = {"name": "Widget", "category": "misc", "price": -1.0}
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 422

    def test_create_zero_price_returns_422(self, client):
        payload = {"name": "Widget", "category": "misc", "price": 0}
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 422

    def test_create_negative_stock_returns_422(self, client):
        payload = {"name": "Widget", "category": "misc", "price": 5.0, "stock": -1}
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 422

    def test_create_no_description_defaults_to_none(self, client):
        payload = {"name": "Widget", "category": "misc", "price": 5.0}
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 201
        assert response.json()["description"] is None

    def test_create_default_stock_is_zero(self, client):
        payload = {"name": "Widget", "category": "misc", "price": 5.0}
        response = client.post("/api/v1/products", json=payload)
        assert response.json()["stock"] == 0


# ---------------------------------------------------------------------------
# GET /products/{id} — Single product
# ---------------------------------------------------------------------------

class TestGetProduct:
    def test_get_existing_returns_200(self, client, created_product):
        pid = created_product["productId"]
        response = client.get(f"/api/v1/products/{pid}")
        assert response.status_code == 200

    def test_get_returns_correct_product(self, client, created_product):
        pid = created_product["productId"]
        response = client.get(f"/api/v1/products/{pid}")
        assert response.json()["productId"] == pid
        assert response.json()["name"] == created_product["name"]

    def test_get_nonexistent_returns_404(self, client):
        response = client.get("/api/v1/products/does-not-exist-xyz")
        assert response.status_code == 404

    def test_get_404_has_detail(self, client):
        response = client.get("/api/v1/products/ghost")
        assert "detail" in response.json()


# ---------------------------------------------------------------------------
# GET /products — List (paginated)
# ---------------------------------------------------------------------------

class TestListProducts:
    def test_list_returns_200(self, client):
        response = client.get("/api/v1/products")
        assert response.status_code == 200

    def test_list_empty_returns_empty_list(self, client):
        response = client.get("/api/v1/products")
        data = response.json()
        assert data["items"] == []
        assert data["count"] == 0
        assert data["next_cursor"] is None

    def test_list_returns_created_products(self, client, created_product):
        response = client.get("/api/v1/products")
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["productId"] == created_product["productId"]

    def test_list_pagination_limit(self, client, sample_product_payload):
        # Create 5 products
        for _ in range(5):
            client.post("/api/v1/products", json=sample_product_payload)

        response = client.get("/api/v1/products?limit=3")
        data = response.json()
        assert len(data["items"]) <= 3

    def test_list_invalid_limit_returns_422(self, client):
        response = client.get("/api/v1/products?limit=0")
        assert response.status_code == 422

    def test_list_pagination_cursor(self, client, sample_product_payload):
        # Create 4 products, fetch with limit=2, use cursor to get next page
        for _ in range(4):
            client.post("/api/v1/products", json=sample_product_payload)

        page1 = client.get("/api/v1/products?limit=2").json()
        if page1["next_cursor"]:
            page2 = client.get(f"/api/v1/products?limit=2&cursor={page1['next_cursor']}").json()
            # All product IDs across pages should be unique
            ids_page1 = {p["productId"] for p in page1["items"]}
            ids_page2 = {p["productId"] for p in page2["items"]}
            assert ids_page1.isdisjoint(ids_page2)


# ---------------------------------------------------------------------------
# PUT /products/{id} — Partial update
# ---------------------------------------------------------------------------

class TestUpdateProduct:
    def test_update_name_persists(self, client, created_product):
        pid = created_product["productId"]
        response = client.put(f"/api/v1/products/{pid}", json={"name": "Updated Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_update_price_persists(self, client, created_product):
        pid = created_product["productId"]
        response = client.put(f"/api/v1/products/{pid}", json={"price": 199.99})
        assert response.status_code == 200
        assert response.json()["price"] == 199.99

    def test_update_stock_persists(self, client, created_product):
        pid = created_product["productId"]
        response = client.put(f"/api/v1/products/{pid}", json={"stock": 100})
        assert response.status_code == 200
        assert response.json()["stock"] == 100

    def test_update_updates_updated_at(self, client, created_product):
        pid = created_product["productId"]
        original_ts = created_product["updatedAt"]
        response = client.put(f"/api/v1/products/{pid}", json={"stock": 5})
        assert response.json()["updatedAt"] >= original_ts

    def test_update_nonexistent_returns_404(self, client):
        response = client.put("/api/v1/products/ghost", json={"stock": 5})
        assert response.status_code == 404

    def test_update_no_fields_returns_400(self, client, created_product):
        pid = created_product["productId"]
        response = client.put(f"/api/v1/products/{pid}", json={})
        assert response.status_code == 400

    def test_update_invalid_price_returns_422(self, client, created_product):
        pid = created_product["productId"]
        response = client.put(f"/api/v1/products/{pid}", json={"price": -5.0})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /products/{id}
# ---------------------------------------------------------------------------

class TestDeleteProduct:
    def test_delete_returns_204(self, client, created_product):
        pid = created_product["productId"]
        response = client.delete(f"/api/v1/products/{pid}")
        assert response.status_code == 204

    def test_delete_then_get_returns_404(self, client, created_product):
        pid = created_product["productId"]
        client.delete(f"/api/v1/products/{pid}")
        response = client.get(f"/api/v1/products/{pid}")
        assert response.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        response = client.delete("/api/v1/products/ghost")
        assert response.status_code == 404

    def test_double_delete_returns_404(self, client, created_product):
        pid = created_product["productId"]
        client.delete(f"/api/v1/products/{pid}")
        response = client.delete(f"/api/v1/products/{pid}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /products/category/{cat} — GSI query
# ---------------------------------------------------------------------------

class TestListByCategory:
    def _seed_electronics(self, client):
        """Seed a few electronics and one non-electronics product."""
        products = [
            {"name": "Budget Headphones", "category": "electronics", "price": 29.99, "stock": 100},
            {"name": "Mid Headphones", "category": "electronics", "price": 79.99, "stock": 50},
            {"name": "Premium Headphones", "category": "electronics", "price": 299.99, "stock": 10},
            {"name": "Office Chair", "category": "furniture", "price": 199.99, "stock": 20},
        ]
        for p in products:
            client.post("/api/v1/products", json=p)

    def test_category_filter_returns_only_matching(self, client):
        self._seed_electronics(client)
        response = client.get("/api/v1/products/category/electronics")
        assert response.status_code == 200
        data = response.json()
        assert all(p["category"] == "electronics" for p in data)
        assert len(data) == 3

    def test_category_filter_empty_category(self, client):
        self._seed_electronics(client)
        response = client.get("/api/v1/products/category/nonexistent")
        assert response.status_code == 200
        assert response.json() == []

    def test_max_price_filter(self, client):
        self._seed_electronics(client)
        response = client.get("/api/v1/products/category/electronics?max_price=80")
        assert response.status_code == 200
        data = response.json()
        assert all(p["price"] <= 80 for p in data)
        assert len(data) == 2  # $29.99 and $79.99

    def test_max_price_excludes_above_threshold(self, client):
        self._seed_electronics(client)
        response = client.get("/api/v1/products/category/electronics?max_price=30")
        data = response.json()
        assert all(p["price"] <= 30 for p in data)

    def test_results_sorted_by_price(self, client):
        self._seed_electronics(client)
        response = client.get("/api/v1/products/category/electronics")
        data = response.json()
        prices = [p["price"] for p in data]
        assert prices == sorted(prices)

    def test_furniture_category_isolated(self, client):
        self._seed_electronics(client)
        response = client.get("/api/v1/products/category/furniture")
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Office Chair"
