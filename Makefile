# AI Form Assistant - Development Makefile

.PHONY: help install dev test lint format type-check security-check quality pre-commit clean docker-build docker-up docker-down

# Default target
help:
	@echo "Available commands:"
	@echo "  install       - Install dependencies and setup development environment"
	@echo "  dev          - Start development server"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting (flake8)"
	@echo "  format       - Format code (black + isort)"
	@echo "  type-check   - Run type checking (mypy)"
	@echo "  security     - Run security checks (bandit)"
	@echo "  quality      - Run all quality checks (lint + type + security)"
	@echo "  pre-commit   - Setup and run pre-commit hooks"
	@echo "  clean        - Clean cache and temporary files"
	@echo "  docker-build - Build Docker containers"
	@echo "  docker-up    - Start Docker containers"
	@echo "  docker-down  - Stop Docker containers"

# Install dependencies
install:
	pip install -r requirements.txt
	pre-commit install

# Start development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest -v

# Run tests with coverage
test-coverage:
	pytest -v --cov=app --cov-report=html --cov-report=term

# Linting
lint:
	flake8 app/ tests/ --max-line-length=100

# Code formatting
format:
	black app/ tests/ --line-length=100
	isort app/ tests/ --profile=black --line-length=100

# Type checking
type-check:
	mypy app/ --ignore-missing-imports

# Security checks
security:
	bandit -r app/ --skip B101,B601

# Run all quality checks
quality: lint type-check security
	@echo "✅ All quality checks passed!"

# Setup and run pre-commit
pre-commit:
	pre-commit install
	pre-commit run --all-files

# Clean cache and temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database commands
db-indexes:
	python -c "import asyncio; from app.database import connect_to_mongo, db; from app.utils.db_indexes import create_all_indexes; asyncio.run(connect_to_mongo()); asyncio.run(create_all_indexes(db))"

# Development workflow commands
setup: install pre-commit
	@echo "🚀 Development environment setup complete!"

check: format quality test
	@echo "🎉 All checks passed! Ready to commit."

# Quick development cycle
quick-check: format lint
	@echo "⚡ Quick checks complete!"