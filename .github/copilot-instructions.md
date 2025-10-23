# Copilot Instructions for Python Script Runner

> Production-grade Python script execution engine with comprehensive monitoring, alerting, and analytics. Version 7.0.0+

## ⚠️ CRITICAL: Do NOT Generate Status/Report Files

**NEVER create markdown files for:**
- Status reports
- Progress trackers
- Task summaries
- Meeting notes
- Completion reports
- Execution logs
- Summary documents

**Instead:** Update the copilot-instructions.md directly with discoveries, patterns, or changes. Ask the user for feedback on iterations.

## Architecture Overview

This is a **monolithic Python module** (`runner.py`, 8251 lines) that implements a sophisticated script execution framework. The key insight: **all intelligence flows through a single execution pipeline**.

```
ScriptRunner (subprocess execution) → ProcessMonitor (real-time metrics collection)
  → HistoryManager (SQLite persistence) → Analytics (TrendAnalyzer, MLAnomalyDetector)
  → AlertManager (rule-based triggers) → Notifications (Email/Slack/Webhooks)
```

**Critical decision**: All components share a SQLite database as the single source of truth for metrics. This enables time-series analysis but requires careful connection pooling (see `HistoryManager.get_connection()`) to avoid database locks.

### Core Components (read these files in order)

1. **`runner.py`** - Single file, organized by feature class:
   - `ScriptRunner` (lines 6125+) - Main execution engine
   - `ProcessMonitor` - Real-time CPU/memory/I/O sampling during execution
   - `HistoryManager` (lines ~180) - SQLite with connection pooling (thread-safe queue)
   - `AlertManager` - Rule evaluation and multi-channel dispatch
   - `TrendAnalyzer` - Linear regression, anomaly detection (IQR, Z-score, MAD)
   - `CICDIntegration` - Performance gates and JUnit/TAP output
   - Other: `AdvancedProfiler`, `LogAnalyzer`, `MetricsCorrelationAnalyzer`

2. **`dashboard/backend/app.py`** (801 lines) - FastAPI REST API + WebSocket
   - Wraps runner components in web service
   - Uses same HistoryManager and TrendAnalyzer
   - Caching layer (CACHE_TTL_SECONDS = 2) to reduce DB queries

3. **`dashboard/frontend/index.html`** - Single HTML file with embedded CSS/JS
   - WebSocket listener for real-time updates
   - No build step, served directly by FastAPI

4. **Configuration**: `config.example.yaml` - YAML alerts, gates, notifications

## Design Patterns

### Pattern 1: Metrics Collection Strategy
**Why**: The project needs <2% CPU overhead while sampling 10k+ metrics/second.

- `ProcessMonitor` thread runs independently during script execution (non-blocking)
- Metrics collected every `monitor_interval` seconds (default 0.1s)
- CPU/memory snapshots stored in memory first, then batch-written to SQLite after execution
- **Important**: Connection pooling prevents database contention—always use `with manager.get_connection():` pattern

**When changing monitoring**: Edit `ProcessMonitor.monitor_loop()` method, test overhead with `test_script.py` running compute-heavy loads.

### Pattern 2: SQLite as Time-Series DB
**Why**: Simpler than external DB, SOC2/HIPAA compliant (local file), queryable with SQL.

- Schema: `executions` table (one row per script run) + `metrics` table (one row per metric/execution)
- Queries use `datetime` ISO format strings and `timedelta` for ranges
- Retention policies can delete old records (see `RetentionPolicy` class)
- **Critical bug risk**: SQLite locks when multiple writers exist—always use connection pooling context manager

**When querying**: Use indexed lookups on `(execution_id, metric_name)` pairs. Avoid full table scans.

### Pattern 3: Rule-Based Alert Triggering
**Why**: Flexible, declarative approach that avoids hardcoded thresholds.

- User defines alerts in YAML as: `condition: cpu_max > 85 AND memory_max_mb > 1024`
- `AlertManager.check_alerts()` evaluates all rules against current metrics dict
- Each alert has `severity` (INFO/WARNING/ERROR/CRITICAL) and `channels` (email/slack/webhook)
- **Design decision**: Alerts deduplicate within time windows to prevent spam (see `AlertIntelligence` class)

**When adding new alert types**: Add condition parser in `AlertManager.parse_condition()`, then register channel handler in `AlertManager.notify()`.

### Pattern 4: Multi-Tenant Persistence in Single DB
**Why**: SQLite file per project = simple scaling, no server needed, easy backups.

- Each `ScriptRunner` instance can point to different `history_db` file
- All analytics use `script_path` as grouping key in queries
- Dashboard initializes `HistoryManager(db_path=...)` with user-provided path

**When scaling**: This pattern stays single-file—no sharding logic needed for typical workloads.

## Developer Workflows

### Running Tests
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests with coverage
pytest . -v --cov=runner

# Run specific test file
pytest dashboard/backend/test_app.py -v

# Test with different Python version (uses PyPy3 dependencies)
pypy3 -m pytest test_script.py
```

### Building & Packaging
```bash
# Editable install for development
pip install -e .

# Build wheel
python setup.py bdist_wheel

# Upload to PyPI (see release.sh for full CI/CD)
pip install twine
twine upload dist/*
```

### Local Dashboard Testing
```bash
# Terminal 1: Start FastAPI backend on http://localhost:8000
cd dashboard/backend
python -m uvicorn app:app --reload --port 8000

# Terminal 2: Run script with runner
python -m runner ../test_script.py

# Browser: Open http://localhost:8000
# Dashboard shows real-time metrics via WebSocket
```

### Code Quality
```bash
# Format with black (line-length: 120)
black runner.py

# Lint with flake8
flake8 runner.py

# Type hints validation (target: Python 3.6)
mypy runner.py --python-version 3.6
```

## Project-Specific Conventions

### 1. Metrics Dict Structure
**Standard metric names** (used everywhere—don't invent new ones):
- Timing: `execution_time_seconds`, `start_time`, `end_time`, `user_time`, `system_time`
- CPU: `cpu_max`, `cpu_avg`, `cpu_min`, `context_switches`
- Memory: `memory_max_mb`, `memory_avg_mb`, `memory_min_mb`, `page_faults`
- System: `num_threads`, `num_fds`, `block_io_operations`
- Output: `stdout_lines`, `stderr_lines`, `exit_code`, `success`

When adding new metrics: register in `ScriptRunner.collect_system_metrics_end()` and update schema if using database.

### 2. Retry Configuration
**Modern pattern** (use this, not legacy `retry_count`):
```python
runner = ScriptRunner('script.py')
runner.retry_config = RetryConfig(
    strategy='exponential',  # or 'linear', 'fibonacci'
    max_attempts=3,
    base_delay=1.0
)
```

Legacy attributes (`retry_count`, `retry_delay`) kept for backward compatibility but ignored by modern retry logic.

### 3. Logging
All logging uses Python's standard `logging` module. Each component has its own logger:
```python
self.logger = logging.getLogger(__name__)
self.logger.debug("Detailed trace")
self.logger.info("Normal operation")
self.logger.error("Recoverable failure")  # Alert context if severity HIGH+
```

JSON structured logging available via `StructuredLogger` class for production deployments.

### 4. Error Categorization
`LogAnalyzer` detects error patterns (timeout, memory, file_error, permission_error, connection_error, database_error) and assigns severity. Used for root cause analysis—see `KNOWN_PATTERNS` dict for extensibility.

## Common Development Tasks

### Add a New Analytics Feature
1. Add class inheriting pattern from existing analyzers (e.g., `TrendAnalyzer`, `MLAnomalyDetector`)
2. Use `HistoryManager.get_connection()` for database access
3. Integrate into `ScriptRunner.__init__()` to expose via public API
4. Test with `dashboard/backend/test_app.py` pattern (mock HistoryManager fixture)

### Add a New Alert Channel
1. Implement handler in `AlertManager.notify()` switch statement
2. Add configuration class (e.g., `class SlackConfig`)
3. Update `config.example.yaml` with example
4. Test with mock requests (use `unittest.mock` to avoid real API calls)

### Optimize Metrics Collection
1. Edit `ProcessMonitor.monitor_loop()` or `psutil`-based sampling
2. Measure overhead with `StressTest` comparison: before/after CPU% on test workloads
3. Profile with `AdvancedProfiler.profile_cpu_and_memory()` to find hotspots
4. Remember 10k metrics/second throughput target = <0.1ms per sample

### Extend SQLite Schema
1. Add migration in `HistoryManager._init_database()` CREATE TABLE section
2. Add new table with explicit indexes on frequent lookup columns
3. Update `HistoryManager` query methods to populate new table
4. Add retention policy if storing large time-series data
5. Test backward compatibility with existing databases (handle missing columns gracefully)

## Integration Points

### External Dependencies
- **psutil**: CPU/memory/I/O monitoring (core, no fallback)
- **requests**: HTTP webhooks and Slack/email APIs (optional, wrap in try/except)
- **PyYAML**: Config file parsing (optional, used if config_file provided)
- **FastAPI/uvicorn**: Dashboard backend only (optional feature install)

### Compatibility Notes
- **Python 3.6+** support required (see `pyproject.toml`, `requirements-pypy3.txt`)
- **PyPy3** support via parallel requirements file (no C extensions)
- **Windows/macOS/Linux** all supported—use `sys.platform` for OS-specific logic
- **SQLite3**: Built-in to Python, no external DB server

## Tips for AI Productivity

1. **Start with ScriptRunner.run_script()** - Entry point for 80% of features
2. **Metrics flow through HistoryManager** - All persistence logic here
3. **Alerts are rule-evaluated** - No magic, just `condition: metric > threshold` strings
4. **Test with `test_script.py`** - Simple compute workload to validate overhead
5. **Dashboard shares business logic** - Changes to runner.py auto-reflect in API
6. **Connection pooling is non-negotiable** - Always use context manager for DB access
7. **Keep monitor_interval tunable** - Users often need to trade resolution for overhead

## Files Not to Modify Without Reason
- `.github/workflows/` - CI/CD automation, use `release.sh` for manual releases
- `python_script_runner.egg-info/` - Auto-generated during install, ignore
- `docs/` - Documentation, keep separate from code
- Version number: single source in `runner.py` line ~20 (`__version__`)
