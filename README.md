# Serverless Inventory API

[![Test and Deploy](https://github.com/YOUR_USERNAME/serverless-inventory-api/actions/workflows/deploy.yml/badge.svg)](https://github.com/YOUR_USERNAME/serverless-inventory-api/actions/workflows/deploy.yml)

Cloud-native REST API for product inventory management, built fully serverless on AWS Lambda + API Gateway with DynamoDB as the NoSQL store. Features GSI-based category filtering, cursor-based pagination, and a fully automated GitHub Actions CI/CD pipeline that lints, tests, and deploys to AWS on every push to `main`.

---

## Architecture

```
Client (curl / frontend)
        │
        ▼
┌─────────────────────┐
│   AWS API Gateway   │  (HTTP API — routes all paths to Lambda)
│   (HTTP API)        │
└────────┬────────────┘
         │  event (JSON)
         ▼
┌─────────────────────┐
│   AWS Lambda        │  Python 3.12 · FastAPI · Mangum
│   InventoryFunction │  256 MB · 30s timeout
└────────┬────────────┘
         │  boto3
         ▼
┌─────────────────────┐
│   AWS DynamoDB      │  PAY_PER_REQUEST billing
│   Products table    │  GSI: CategoryPriceIndex (category + price)
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  AWS CloudWatch     │  HighLatency alarm (p99 > 500ms)
│  Alarms             │  ErrorRate alarm (5xx > 5/5min)
└─────────────────────┘
```

---

## Endpoints

| Method   | Path                             | Description                                     |
|----------|----------------------------------|-------------------------------------------------|
| `GET`    | `/api/v1/health`                 | Health check — returns `{"status": "ok"}`       |
| `POST`   | `/api/v1/products`               | Create product → 201 + created item             |
| `GET`    | `/api/v1/products`               | List all products (paginated, `?limit=&cursor=`)|
| `GET`    | `/api/v1/products/{id}`          | Get single product → 200 or 404                 |
| `PUT`    | `/api/v1/products/{id}`          | Partial update → 200 or 404                     |
| `DELETE` | `/api/v1/products/{id}`          | Delete → 204 or 404                             |
| `GET`    | `/api/v1/products/category/{cat}`| Filter by category (GSI) — `?max_price=`        |

Interactive docs available at `/docs` (Swagger UI) when running locally.

---

## DynamoDB Schema

**Table:** `Products`

| Attribute     | Type   | Role                                   |
|---------------|--------|----------------------------------------|
| `productId`   | String | Partition key (PK)                     |
| `category`    | String | GSI partition key (CategoryPriceIndex) |
| `price`       | Number | GSI sort key (CategoryPriceIndex)      |
| `name`        | String | Product name                           |
| `description` | String | Optional description                   |
| `stock`       | Number | Units in stock                         |
| `createdAt`   | String | ISO 8601 timestamp                     |
| `updatedAt`   | String | ISO 8601 timestamp                     |

**GSI:** `CategoryPriceIndex` — enables efficient queries like *"all electronics under $50, sorted by price"* without a full table scan.

---

## Local Development

### Prerequisites
- Python 3.12+
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) (for `make local`)
- Docker (required by SAM local)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/serverless-inventory-api
cd serverless-inventory-api
python3 -m venv venv && source venv/bin/activate
make install
```

### Run tests

```bash
make test
# pytest tests/ --cov=src --cov-report=term-missing -v
```

Tests use `moto` to mock DynamoDB — **no AWS account or credentials required.**

### Lint

```bash
make lint
```

### Run locally with SAM

```bash
make local
# API available at http://localhost:8080/api/v1/
```

Requires Docker and AWS SAM CLI. Uses `sam local start-api`.

---

## Deployment

### Prerequisites

1. AWS account (free tier works)
2. IAM user with SAM deploy permissions
3. `aws configure` run with your credentials
4. AWS SAM CLI installed (`pip install aws-sam-cli`)

### Deploy

```bash
make deploy
# Runs: sam build && sam deploy --guided
```

On first run, `--guided` will prompt for stack name and region. After that, settings are saved to `samconfig.toml` (gitignored).

The deploy outputs the live **API Gateway URL**:
```
Outputs:
  ApiUrl: https://<api-id>.execute-api.us-east-1.amazonaws.com
```

---

## CI/CD Pipeline

GitHub Actions runs on every push and PR to `main`:

1. **Lint** — `flake8` enforces style (max line length 100)
2. **Test** — `pytest` with 85%+ coverage gate (`--cov-fail-under=85`)
3. **Deploy** — `sam build && sam deploy` (push to `main` only)

### Required GitHub Secrets

Add these in **Settings → Secrets → Actions**:

| Secret                  | Value                          |
|-------------------------|-------------------------------|
| `AWS_ACCESS_KEY_ID`     | Your IAM user's access key    |
| `AWS_SECRET_ACCESS_KEY` | Your IAM user's secret key    |

> **Never commit credentials.** The pipeline uses GitHub Secrets → IAM roles only.

---

## CloudWatch Monitoring

Two alarms are deployed automatically with `sam deploy`:

| Alarm                        | Trigger                                     | Action           |
|------------------------------|---------------------------------------------|------------------|
| `InventoryAPI-HighLatency`   | p99 latency > 500ms for 2× 5-min windows   | ALARM state      |
| `InventoryAPI-ErrorRate`     | 5xx count > 5 in any 5-min window          | ALARM state      |

Both alarms use `TreatMissingData: notBreaching` so cold/idle periods don't trigger false alerts.

---

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Runtime     | Python 3.12 · FastAPI · Mangum      |
| Compute     | AWS Lambda (serverless)             |
| API Layer   | AWS API Gateway (HTTP API)          |
| Database    | AWS DynamoDB (PAY_PER_REQUEST)      |
| Monitoring  | AWS CloudWatch                      |
| Deployment  | AWS SAM (CloudFormation)            |
| CI/CD       | GitHub Actions                      |
| Testing     | pytest · moto · httpx               |

---

## License

MIT
