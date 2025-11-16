# StackSense Test Suite

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ -v --cov=stacksense --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_tracker.py -v
```

### Run specific test
```bash
pytest tests/test_tracker.py::test_track_call -v
```

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_settings.py` - Settings configuration tests
- `test_tracker.py` - MetricsTracker tests
- `test_analytics.py` - Analytics tests
- `test_database.py` - Database functionality tests
- `test_client.py` - StackSense client tests
- `test_utils.py` - Utility function tests

## Test Coverage

The test suite covers:
- ✅ Settings configuration
- ✅ Metrics tracking
- ✅ Cost calculation
- ✅ Analytics and aggregations
- ✅ Database operations
- ✅ Client initialization
- ✅ Utility functions

## Fixtures

- `temp_db` - Temporary SQLite database for testing
- `settings` - Test settings configuration
- `tracker` - MetricsTracker instance
- `analytics` - Analytics instance
- `stacksense_client` - StackSense client instance

## CI Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Multiple Python versions (3.8-3.12)
- Multiple OS (Ubuntu, macOS)

