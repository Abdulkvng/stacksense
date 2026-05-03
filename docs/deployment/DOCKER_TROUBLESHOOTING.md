# Docker Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: "requirements.txt not found"

**Error:**
```
COPY failed: file not found in build context
```

**Solution:**
The Dockerfile.example now copies `requirements.example.txt` automatically. If you have your own `requirements.txt`, place it in the project root.

### Issue 2: "Cannot find stacksense package"

**Error:**
```
ERROR: Could not find a version that satisfies the requirement stacksense[postgres]
```

**Solution:**
The Dockerfile now installs from source. Make sure:
1. `pyproject.toml` exists in the build context
2. `stacksense/` directory is copied before installation
3. Build context includes the project root

### Issue 3: "docker-compose build fails"

**Error:**
```
ERROR: Cannot locate specified Dockerfile
```

**Solution:**
Run docker-compose from the `docs/deployment/` directory:
```bash
cd docs/deployment
docker-compose up --build
```

Or use the full path in docker-compose.yml (already fixed).

### Issue 4: "Module not found errors"

**Error:**
```
ModuleNotFoundError: No module named 'stacksense'
```

**Solution:**
Ensure the Dockerfile installs StackSense:
```dockerfile
RUN pip install --no-cache-dir -e ".[postgres]"
```

### Issue 5: "Database connection failed"

**Error:**
```
Failed to connect to database
```

**Solution:**
1. Check PostgreSQL is running: `docker-compose ps`
2. Verify environment variables in docker-compose.yml
3. Wait for health check: `depends_on: postgres: condition: service_healthy`

### Issue 6: "Permission denied"

**Error:**
```
Permission denied: /app/example_app.py
```

**Solution:**
Ensure files are copied correctly:
```dockerfile
COPY docs/deployment/example_app.py ./example_app.py
```

## Build Commands

### Build from project root:
```bash
docker build -f docs/deployment/Dockerfile.example -t stacksense-app .
```

### Build with docker-compose:
```bash
cd docs/deployment
docker-compose --profile app up --build
```

### Build dashboard:
```bash
docker build -f docs/deployment/Dockerfile.dashboard -t stacksense-dashboard .
```

## Testing Docker Build

```bash
# Test build without running
docker build -f docs/deployment/Dockerfile.example -t test-build .

# Check if image was created
docker images | grep test-build

# Test run
docker run --rm test-build python -c "import stacksense; print('OK')"
```

## Debugging Tips

1. **Check build context:**
   ```bash
   docker build --no-cache -f docs/deployment/Dockerfile.example .
   ```

2. **Inspect image:**
   ```bash
   docker run --rm -it test-build /bin/bash
   ```

3. **Check logs:**
   ```bash
   docker-compose logs app
   ```

4. **Verify file structure:**
   ```bash
   docker run --rm test-build ls -la /app
   ```

## Fixed Issues

✅ Fixed: requirements.txt path
✅ Fixed: docker-compose context paths
✅ Fixed: Install from source instead of PyPI
✅ Fixed: Example app path in CMD
✅ Fixed: Added .dockerignore
✅ Fixed: Added dashboard Dockerfile

