# StackSense Documentation

Welcome to the StackSense documentation! This directory contains all documentation, guides, and deployment files.

## 📚 Documentation Files

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in minutes
- **[USER_JOURNEY.md](USER_JOURNEY.md)** - Complete explanation of how StackSense works behind the scenes

### Database
- **[DATABASE_GUIDE.md](DATABASE_GUIDE.md)** - Database setup, configuration, and usage
- **[DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md)** - Database architecture, SQLite vs PostgreSQL, SQLAlchemy details

### Deployment
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide, CI/CD, Docker, Kubernetes

## 🐳 Deployment Files

The `deployment/` folder contains all files needed for containerization and deployment:

- **Dockerfile** - Multi-stage Docker build template
- **Dockerfile.example** - Example Dockerfile for applications
- **docker-compose.yml** - Docker Compose setup with PostgreSQL
- **.dockerignore** - Files to exclude from Docker builds
- **init.sql** - PostgreSQL initialization script
- **example_app.py** - Example application using StackSense
- **requirements.example.txt** - Example requirements file

## 📦 Installation Options

### Basic Installation
```bash
pip install stacksense
```

### With PostgreSQL Support
```bash
pip install stacksense[postgresql]  # or stacksense[postgres]
```

### With Dashboard Support
```bash
pip install stacksense[dashboard]
```

### Development
```bash
pip install stacksense[dev]
```

## 🔗 Quick Links

- [Main README](../README.md) - Project overview
- [GitHub Repository](https://github.com/Abdulkvng/stacksense)
- [Issue Tracker](https://github.com/Abdulkvng/stacksense/issues)

