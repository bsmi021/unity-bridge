# Unity Bridge MCP v2.0 Test Suite

Comprehensive test suite following Test-Driven Development (TDD) principles for the Unity Bridge MCP Server v2.0.

## Overview

This test suite validates:
- **Retry logic** with exponential backoff
- **Response caching** with LRU eviction
- **Health monitoring** via heartbeat files
- **Integration testing** with live Unity Bridge

## Test Structure

```
tests/
├── __init__.py                  # Package initialization
├── conftest.py                  # Pytest configuration and fixtures
├── requirements.txt             # Test dependencies
├── README.md                    # This file
├── test_retry_handler.py        # Retry logic unit tests
├── test_response_cache.py       # Caching unit tests
├── test_health_monitor.py       # Health monitoring unit tests
└── test_integration.py          # Integration tests (requires Unity)
```

## Setup

### Install Dependencies

```bash
pip install -r tests/requirements.txt
```

### Prerequisites

- Python 3.10 or higher
- pytest and pytest-asyncio
- For integration tests: Unity Editor with Unity Bridge installed and running

## Running Tests

### Run All Tests (except integration)

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_retry_handler.py
pytest tests/test_response_cache.py
pytest tests/test_health_monitor.py
```

### Run Integration Tests (requires Unity)

```bash
pytest tests/test_integration.py
```

Or run all tests including integration:

```bash
pytest --run-integration
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
```

View coverage report at `htmlcov/index.html`

### Run Specific Test Class or Method

```bash
# Run specific class
pytest tests/test_retry_handler.py::TestRetryAsync

# Run specific test
pytest tests/test_retry_handler.py::TestRetryAsync::test_success_first_attempt
```

### Run Tests Matching Pattern

```bash
# Run all tests with "retry" in the name
pytest -k retry

# Run all tests with "cache" in the name
pytest -k cache
```

## Test Categories

### Unit Tests

**test_retry_handler.py** (45+ tests)
- Error classification (`is_retryable_error`)
- RetryConfig configuration
- Async retry function
- Exponential backoff timing
- Decorator usage
- Exception handling

**test_response_cache.py** (40+ tests)
- Cache entry validation
- Get/set operations
- Key generation
- LRU eviction
- TTL expiration
- Scene change invalidation
- Concurrent access

**test_health_monitor.py** (35+ tests)
- HealthStatus dataclass
- Heartbeat file parsing
- Stale heartbeat detection
- Invalid JSON handling
- I/O error handling
- Wait for healthy

### Integration Tests

**test_integration.py** (30+ tests)
- Health monitoring with live Unity
- DirectBridge communication
- Phase 1 commands (clear-console, get-selection, refresh-assets)
- Command latency benchmarks
- Error handling
- Concurrent command execution

**Requirements:** Unity Editor must be running with Unity Bridge installed.

**Skip Behavior:** Integration tests automatically skip if `heartbeat.json` not found.

## TDD Workflow

This test suite follows the **Red-Green-Refactor** cycle:

### 🔴 RED Phase (Current State)

Tests are written BEFORE implementation. All tests will initially **FAIL** with import errors because modules don't exist yet.

```bash
$ pytest
# Expected: All tests skipped or failed (modules not implemented)
```

### 🟢 GREEN Phase (Next Step)

Implement the modules to make tests pass:

1. Implement `retry_handler.py`
2. Implement `response_cache.py`
3. Implement `health_monitor.py`
4. Implement `direct_bridge.py`

After each implementation:

```bash
$ pytest tests/test_retry_handler.py
# Expected: All tests PASS
```

### 🔄 REFACTOR Phase

Once tests pass, refactor code for:
- Better performance
- Cleaner structure
- Reduced complexity
- DRY principles

Tests should continue passing throughout refactoring.

## Test Markers

### Built-in Markers

- `@pytest.mark.asyncio` - Async tests (auto-applied)
- `@pytest.mark.integration` - Integration tests requiring Unity
- `@pytest.mark.slow` - Slow-running tests

### Using Markers

```bash
# Run only integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"

# Run only slow tests
pytest -m slow
```

## Writing New Tests

### Template for Unit Test

```python
import pytest

class TestMyFeature:
    """Test my feature description."""

    def test_basic_functionality(self):
        """Test should do X."""
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = my_function(input_data)

        # Assert
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Async test should do Y."""
        # Arrange
        config = MyConfig()

        # Act
        result = await my_async_function(config)

        # Assert
        assert result is not None
```

### Template for Integration Test

```python
import pytest

pytestmark = pytest.mark.skipif(
    not is_unity_running(),
    reason="Unity not running"
)

@pytest.mark.asyncio
class TestMyIntegration:
    """Integration test for my feature."""

    async def test_with_unity(self, bridge):
        """Test should work with real Unity."""
        result = await bridge.send_command("my-command", {})
        assert result["success"] is True
```

## Fixtures

### Available Fixtures

- `cache` - Fresh ResponseCache instance (max_entries=10)
- `large_cache` - ResponseCache with 100 entries
- `bridge` - DirectBridge instance
- `health_monitor` - HealthMonitor instance
- `project_root` - Path to Unity project root
- `tmp_project_root` - Temporary project directory
- `heartbeat_path` - Path to heartbeat.json

### Using Fixtures

```python
def test_with_cache(cache):
    """Test using cache fixture."""
    await cache.set("cmd", {}, {"success": True})
    result = await cache.get("cmd", {})
    assert result is not None
```

## Coverage Goals

- **Unit tests:** 90%+ code coverage
- **Integration tests:** Cover all Phase 1 commands
- **Edge cases:** Test boundary conditions, error paths
- **Performance:** Validate latency targets (p95 < 300ms)

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: pip install -r tests/requirements.txt

    - name: Run unit tests
      run: pytest -m "not integration"

    - name: Upload coverage
      run: pytest --cov=. --cov-report=xml
```

## Troubleshooting

### Tests Skipped

**Problem:** All tests showing "skipped"

**Solution:** Modules not yet implemented (expected in RED phase). Implement the module and re-run.

### Integration Tests Failing

**Problem:** Integration tests fail with "Unity not running"

**Solution:**
1. Start Unity Editor
2. Ensure Unity Bridge C# scripts installed
3. Verify `heartbeat.json` exists at `.claude/unity/heartbeat.json`
4. Check Unity console for bridge initialization message

### Import Errors

**Problem:** `ModuleNotFoundError` for test modules

**Solution:**
1. Ensure you're running from project root: `cd C:\projects\my-marketplace\unity-plugin\unity`
2. Check Python path includes parent directory
3. Verify `conftest.py` is present in tests directory

### Async Tests Not Running

**Problem:** Async tests showing warnings or not running

**Solution:**
1. Ensure `pytest-asyncio` installed: `pip install pytest-asyncio`
2. Check `pytest.ini` has `asyncio_mode = auto`
3. Verify `@pytest.mark.asyncio` decorator present

## Performance Benchmarks

Integration tests validate performance targets:

- **Query hierarchy:** p95 latency < 300ms
- **Get selection:** < 100ms
- **Clear console:** < 100ms
- **Overall throughput:** > 5 commands/sec (batch mode)

Run benchmarks:

```bash
pytest tests/test_integration.py::TestCommandLatency -v
```

## Contributing

When adding new features:

1. ✅ Write tests FIRST (RED phase)
2. ✅ Implement feature to pass tests (GREEN phase)
3. ✅ Refactor for quality (REFACTOR phase)
4. ✅ Ensure 90%+ coverage maintained
5. ✅ Update this README if adding new test categories

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Unity Bridge MCP Tech Spec](../TECH_SPEC_Unity_Bridge_MCP_v2.md)

## License

Part of Unity Bridge MCP Server project.
