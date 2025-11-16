# Package Verification Guide

## Verifying Package Contents

### 1. Check Database Module Files

Verify all database files exist:
```bash
ls -la stacksense/database/
```

Should show:
- `__init__.py`
- `connection.py`
- `models.py`

### 2. Verify Package Includes Database

After building the package, check included files:
```bash
python -m build
tar -tzf dist/stacksense-*.tar.gz | grep database
```

Should show:
- `stacksense/database/__init__.py`
- `stacksense/database/connection.py`
- `stacksense/database/models.py`

### 3. Test Import

Test that database module can be imported:
```bash
python -c "from stacksense.database import DatabaseManager, Event, Metric; print('✅ Database module imports successfully')"
```

### 4. Verify Package Installation

```bash
pip install -e .
python -c "import stacksense.database; print(stacksense.database.__file__)"
```

## Common Issues

### Issue: Database module not found after installation

**Solution:**
1. Ensure `MANIFEST.in` includes database files
2. Rebuild package: `python -m build --no-cache`
3. Reinstall: `pip install -e . --force-reinstall`

### Issue: ImportError: cannot import name 'DatabaseManager'

**Solution:**
1. Check `stacksense/database/__init__.py` exports DatabaseManager
2. Verify `stacksense/database/connection.py` exists
3. Check for circular imports

### Issue: Missing files in SOURCES.txt

**Solution:**
1. Add `MANIFEST.in` file
2. Use `include-package-data = true` in pyproject.toml
3. Rebuild package

## Verification Checklist

- [ ] `stacksense/database/__init__.py` exists
- [ ] `stacksense/database/connection.py` exists
- [ ] `stacksense/database/models.py` exists
- [ ] `MANIFEST.in` includes database files
- [ ] `pyproject.toml` has `include-package-data = true`
- [ ] Package builds without errors
- [ ] Database module imports successfully
- [ ] All tests pass

