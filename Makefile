.PHONY: help check-python release-tools install dev-install enterprise-install test lint format build check-dist publish-test publish dashboard clean docker-build docker-up docker-down docker-logs

PYTHON ?= $(shell ./scripts/resolve_python.sh)
PIP := $(PYTHON) -m pip
BUILD := $(PYTHON) -m build
TWINE := $(PYTHON) -m twine
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy

check-python: ## Verify that a supported Python interpreter is available
	@$(PYTHON) --version >/dev/null

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: check-python ## Install StackSense
	$(PIP) install -e .

enterprise-install: check-python ## Install the private enterprise add-on package
	$(PIP) install -e ./enterprise

release-tools: check-python ## Install build and publishing tools
	$(PIP) install build twine

dev-install: check-python ## Install StackSense with dev dependencies
	$(PIP) install -e ".[dev]"

test: check-python ## Run tests
	$(PYTEST) tests/ -v

lint: check-python ## Run linters
	$(FLAKE8) stacksense/ --count --select=E9,F63,F7,F82 --show-source --statistics
	$(BLACK) --check stacksense/
	$(MYPY) stacksense/ || true

format: check-python ## Format code
	$(BLACK) stacksense/
	$(ISORT) stacksense/

build: check-python ## Build package
	$(BUILD) --no-isolation

check-dist: check-python ## Validate built package metadata
	$(TWINE) check dist/*

publish-test: check-python ## Publish to TestPyPI
	$(TWINE) upload --repository testpypi dist/*

publish: check-python ## Publish to PyPI
	$(TWINE) upload dist/*

dashboard: check-python ## Run the StackSense dashboard
	$(PYTHON) -m stacksense.dashboard

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

db-init: check-python ## Initialize database tables
	$(PYTHON) -c "from stacksense.database import get_db_manager; get_db_manager().create_tables()"

db-reset: check-python ## Reset database (WARNING: deletes all data)
	$(PYTHON) -c "from stacksense.database import get_db_manager; db = get_db_manager(); db.drop_tables(); db.create_tables()"
