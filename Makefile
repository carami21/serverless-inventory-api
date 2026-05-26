.PHONY: install test lint build local deploy clean

install:
	pip install -r requirements.txt -r requirements-dev.txt

test:
	pytest tests/ --cov=src --cov-report=term-missing -v

lint:
	python -m flake8 src/ tests/ --max-line-length=100

build:
	sam build

local:
	sam local start-api --port 8080

deploy:
	sam build && sam deploy --guided

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf .aws-sam/ htmlcov/ .coverage
