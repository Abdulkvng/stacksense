# Deployment Files

This directory contains all files needed for containerizing and deploying StackSense applications.

## Files

- **Dockerfile** - Multi-stage Docker build template for production
- **Dockerfile.example** - Example Dockerfile showing how to use StackSense in your application
- **docker-compose.yml** - Complete Docker Compose setup with PostgreSQL, pgAdmin, and example app
- **init.sql** - PostgreSQL initialization script (runs automatically in Docker)
- **example_app.py** - Example Python application demonstrating StackSense usage
- **requirements.example.txt** - Example requirements.txt for applications using StackSense

## Quick Start

### Using Docker Compose

```bash
# Start PostgreSQL database
docker-compose up -d postgres

# Run example application
docker-compose --profile app up app

# Access pgAdmin (optional)
docker-compose --profile tools up pgadmin
# Visit http://localhost:5050
```

### Using Dockerfile

```bash
# Build image
docker build -f Dockerfile.example -t my-app .

# Run with PostgreSQL
docker run -e STACKSENSE_DB_URL=postgresql://... my-app
```

## PostgreSQL Support

To use PostgreSQL, install with:

```bash
pip install stacksense[postgresql]
# or
pip install stacksense[postgres]
```

Both commands install the same PostgreSQL driver (`psycopg2-binary`).

## See Also

- [../DEPLOYMENT.md](../DEPLOYMENT.md) - Complete deployment guide
- [../QUICKSTART.md](../QUICKSTART.md) - Quick start guide
- [../../README.md](../../README.md) - Main project README

