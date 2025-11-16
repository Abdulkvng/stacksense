# StackSense Deployment Guide

This guide covers deploying StackSense to production, including containerization, CI/CD, and best practices.

## Table of Contents

1. [Publishing to PyPI](#publishing-to-pypi)
2. [Docker Deployment](#docker-deployment)
3. [CI/CD Setup](#cicd-setup)
4. [Production Best Practices](#production-best-practices)
5. [Environment Configuration](#environment-configuration)

## Publishing to PyPI

### Prerequisites

1. Create a PyPI account at https://pypi.org
2. Generate an API token at https://pypi.org/manage/account/token/
3. Add token to GitHub Secrets as `PYPI_API_TOKEN`

### Manual Publishing

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check package
twine check dist/*

# Upload to PyPI (test first)
twine upload --repository testpypi dist/*

# Upload to production PyPI
twine upload dist/*
```

### Automated Publishing

The GitHub Actions workflow automatically publishes when you:
1. Create a GitHub Release
2. Or manually trigger the workflow

**Steps:**
1. Update version in `pyproject.toml`
2. Commit and push changes
3. Create a GitHub Release tag (e.g., `v0.1.0`)
4. GitHub Actions will automatically build and publish

## Docker Deployment

### Quick Start

```bash
# Start PostgreSQL and pgAdmin
docker-compose up -d postgres pgadmin

# Build and run your application
docker-compose up --build app
```

### Custom Application Dockerfile

1. Copy `Dockerfile.example` to your project
2. Customize for your application:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install StackSense with PostgreSQL support
RUN pip install stacksense[postgres]

# Copy application
COPY . .

# Set environment variables
ENV STACKSENSE_ENABLE_DB=true
ENV STACKSENSE_DB_URL=postgresql://user:pass@postgres:5432/stacksense

CMD ["python", "app.py"]
```

### Docker Compose for Production

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: stacksense
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - app-network

  app:
    build: .
    environment:
      - STACKSENSE_DB_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/stacksense
    depends_on:
      - postgres
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

## CI/CD Setup

### GitHub Actions

The repository includes two workflows:

1. **CI** (`.github/workflows/ci.yml`):
   - Runs on push/PR
   - Tests across Python 3.8-3.12
   - Runs linters and type checkers
   - Builds and tests Docker image

2. **Publish** (`.github/workflows/publish.yml`):
   - Runs on release creation
   - Builds package
   - Publishes to PyPI

### Setting Up Secrets

1. Go to GitHub Repository → Settings → Secrets
2. Add `PYPI_API_TOKEN` with your PyPI API token

### GitLab CI/CD

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - publish

test:
  stage: test
  image: python:3.11
  script:
    - pip install -e ".[dev]"
    - pytest tests/
    - flake8 stacksense/
    - black --check stacksense/

build:
  stage: build
  image: python:3.11
  script:
    - pip install build twine
    - python -m build
    - twine check dist/*
  artifacts:
    paths:
      - dist/

publish:
  stage: publish
  image: python:3.11
  script:
    - pip install twine
    - twine upload dist/*
  only:
    - tags
  variables:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: $PYPI_API_TOKEN
```

## Production Best Practices

### 1. Database Configuration

**Use PostgreSQL in Production:**
```bash
# Install PostgreSQL support
pip install stacksense[postgres]

# Set connection string
export STACKSENSE_DB_URL="postgresql://user:password@host:5432/stacksense"
```

**Connection Pooling:**
- Already configured in `DatabaseManager`
- Pool size: 10 connections
- Max overflow: 20 connections
- Connection health checks enabled

### 2. Environment Variables

```bash
# Required
STACKSENSE_API_KEY=your_api_key
STACKSENSE_PROJECT_ID=production-project

# Database
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=postgresql://user:pass@host:5432/stacksense

# Optional
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
STACKSENSE_DB_ECHO=false
```

### 3. Security

- **Never commit secrets**: Use environment variables or secrets management
- **Database credentials**: Store in secure vault (AWS Secrets Manager, HashiCorp Vault)
- **API keys**: Rotate regularly
- **Network security**: Use VPC/private networks for database

### 4. Monitoring

```python
# Health check endpoint
from stacksense.database import get_db_manager

@app.route('/health')
def health():
    db = get_db_manager()
    if db.health_check():
        return {'status': 'healthy'}, 200
    return {'status': 'unhealthy'}, 503
```

### 5. Backup Strategy

**Database Backups:**
```bash
# PostgreSQL backup
pg_dump -h localhost -U stacksense stacksense > backup.sql

# Restore
psql -h localhost -U stacksense stacksense < backup.sql
```

**Automated Backups:**
- Use managed database services (AWS RDS, Google Cloud SQL)
- Set up automated daily backups
- Test restore procedures regularly

### 6. Scaling

**Horizontal Scaling:**
- Multiple application instances can share the same database
- Database handles concurrent connections via connection pooling
- Consider read replicas for analytics queries

**Vertical Scaling:**
- Increase database resources as data grows
- Monitor query performance
- Add indexes for common queries

## Environment Configuration

### Development

```bash
# .env.development
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=sqlite:///./stacksense.db
STACKSENSE_ENVIRONMENT=development
STACKSENSE_DEBUG=true
```

### Staging

```bash
# .env.staging
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=postgresql://user:pass@staging-db:5432/stacksense
STACKSENSE_ENVIRONMENT=staging
STACKSENSE_DEBUG=false
```

### Production

```bash
# .env.production
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=postgresql://user:pass@prod-db:5432/stacksense
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
STACKSENSE_DB_ECHO=false
```

## Kubernetes Deployment

### Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stacksense-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: stacksense-app
  template:
    metadata:
      labels:
        app: stacksense-app
    spec:
      containers:
      - name: app
        image: your-registry/stacksense-app:latest
        env:
        - name: STACKSENSE_DB_URL
          valueFrom:
            secretKeyRef:
              name: stacksense-secrets
              key: db-url
        - name: STACKSENSE_API_KEY
          valueFrom:
            secretKeyRef:
              name: stacksense-secrets
              key: api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Secrets

```bash
# Create Kubernetes secret
kubectl create secret generic stacksense-secrets \
  --from-literal=db-url='postgresql://user:pass@db:5432/stacksense' \
  --from-literal=api-key='your-api-key'
```

## Troubleshooting

### Database Connection Issues

```python
# Test database connection
from stacksense.database import get_db_manager

db = get_db_manager()
if db.health_check():
    print("Database connected")
else:
    print("Database connection failed")
```

### Performance Issues

1. **Check connection pool**: Monitor active connections
2. **Query optimization**: Use indexes, analyze slow queries
3. **Resource limits**: Increase database resources if needed

### Deployment Issues

1. **Check logs**: `docker logs stacksense-app`
2. **Verify environment variables**: Ensure all required vars are set
3. **Database migrations**: Ensure tables are created
4. **Network connectivity**: Verify database is reachable

## Next Steps

1. Set up monitoring and alerting
2. Configure automated backups
3. Set up staging environment
4. Create deployment runbooks
5. Document rollback procedures

