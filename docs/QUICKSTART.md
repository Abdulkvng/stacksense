# Quick Start Guide

Get StackSense up and running in minutes!

## Option 1: Local Installation (Development)

```bash
# Install StackSense
pip install stacksense

# Or install from source
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense
pip install -e .
```

**Usage:**
```python
from stacksense import StackSense
import openai

ss = StackSense(api_key="your_key")
client = ss.monitor(openai.OpenAI())
# Use client normally - all calls are tracked!
```

## Option 2: Docker Compose (Recommended for Testing)

```bash
# Start PostgreSQL and services
docker-compose up -d postgres

# Run example application
docker-compose --profile app up app

# Or run your own application
docker-compose --profile app up --build app
```

**Access Services:**
- PostgreSQL: `localhost:5432`
- pgAdmin (optional): `http://localhost:5050` (admin@stacksense.io / admin)

## Option 3: Full Docker Setup

```bash
# Build Docker image
docker build -f Dockerfile.example -t stacksense-app .

# Run with PostgreSQL
docker run --rm \
  -e STACKSENSE_ENABLE_DB=true \
  -e STACKSENSE_DB_URL=postgresql://user:pass@host:5432/stacksense \
  stacksense-app
```

## Publishing to PyPI

### First Time Setup:

1. **Create PyPI Account**
   - Go to https://pypi.org
   - Create account and verify email

2. **Generate API Token**
   - Go to https://pypi.org/manage/account/token/
   - Create token with "Upload packages" scope
   - Copy token

3. **Add to GitHub Secrets**
   - Go to your GitHub repo → Settings → Secrets
   - Add new secret: `PYPI_API_TOKEN` with your token

### Publishing:

**Automated (Recommended):**
```bash
# 1. Update version in pyproject.toml
# 2. Commit and push
git add pyproject.toml
git commit -m "Bump version to 0.1.0"
git push

# 3. Create GitHub Release
git tag v0.1.0
git push origin v0.1.0

# GitHub Actions will automatically publish!
```

**Manual:**
```bash
# Build package
make build
# or
python -m build

# Check package
twine check dist/*

# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Upload to production PyPI
twine upload dist/*
```

## Production Deployment

### 1. Set Environment Variables

```bash
export STACKSENSE_API_KEY=your_api_key
export STACKSENSE_PROJECT_ID=production-project
export STACKSENSE_ENABLE_DB=true
export STACKSENSE_DB_URL=postgresql://user:pass@db-host:5432/stacksense
export STACKSENSE_ENVIRONMENT=production
```

### 2. Deploy with Docker

```bash
# Build production image
docker build -t your-registry/stacksense-app:latest .

# Push to registry
docker push your-registry/stacksense-app:latest

# Deploy (example with docker-compose)
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Deploy to Cloud

**AWS ECS/Fargate:**
- Use provided Dockerfile
- Configure environment variables in task definition
- Use RDS for PostgreSQL

**Google Cloud Run:**
- Build and push to Container Registry
- Set environment variables in Cloud Run service
- Use Cloud SQL for PostgreSQL

**Kubernetes:**
- See `DEPLOYMENT.md` for Kubernetes manifests
- Use Secrets for sensitive data
- Use StatefulSet for PostgreSQL or managed service

## Common Commands

```bash
# Development
make dev-install          # Install with dev dependencies
make test                 # Run tests
make lint                 # Run linters
make format               # Format code

# Building
make build               # Build package
make publish             # Publish to PyPI

# Docker
make docker-build        # Build Docker image
make docker-up           # Start services
make docker-down         # Stop services
make docker-logs         # View logs

# Database
make db-init             # Initialize database tables
make db-reset            # Reset database (WARNING: deletes data)
```

## Next Steps

- Read [DATABASE_GUIDE.md](DATABASE_GUIDE.md) for database setup
- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [README.md](README.md) for full documentation

## Troubleshooting

### Database Connection Issues

```python
from stacksense.database import get_db_manager

db = get_db_manager()
if db.health_check():
    print("Database OK")
else:
    print("Database connection failed - check STACKSENSE_DB_URL")
```

### Docker Issues

```bash
# Check logs
docker-compose logs -f

# Restart services
docker-compose restart

# Clean and restart
docker-compose down -v
docker-compose up -d
```

### PyPI Publishing Issues

- Verify API token is correct
- Check package name isn't taken
- Ensure version is incremented
- Test on TestPyPI first

