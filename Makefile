.PHONY: help install dev-install test lint format build publish clean docker-build docker-up docker-down docker-logs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install StackSense
	pip install -e .

dev-install: ## Install StackSense with dev dependencies
	pip install -e ".[dev]"

test: ## Run tests
	pytest tests/ -v

lint: ## Run linters
	flake8 stacksense/ --count --select=E9,F63,F7,F82 --show-source --statistics
	black --check stacksense/
	mypy stacksense/ || true

format: ## Format code
	black stacksense/
	isort stacksense/

build: ## Build package
	python -m build

publish-test: ## Publish to TestPyPI
	twine upload --repository testpypi dist/*

publish: ## Publish to PyPI
	twine upload dist/*

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

docker-build: ## Build Docker image
	docker build -t stacksense:latest -f Dockerfile.example .

docker-up: ## Start Docker Compose services
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-clean: ## Clean Docker resources
	docker-compose down -v
	docker system prune -f

db-init: ## Initialize database tables
	python -c "from stacksense.database import get_db_manager; get_db_manager().create_tables()"

db-reset: ## Reset database (WARNING: deletes all data)
	python -c "from stacksense.database import get_db_manager; db = get_db_manager(); db.drop_tables(); db.create_tables()"

