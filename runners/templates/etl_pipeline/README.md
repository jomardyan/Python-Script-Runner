# ETL Pipeline Template

## Overview

This template provides a production-grade ETL (Extract, Transform, Load) pipeline pattern with:

- **Separation of Concerns**: Extract, Transform, and Load logic isolated
- **Error Handling**: Comprehensive exception handling with logging
- **Metrics Collection**: Detailed execution metrics for monitoring
- **Configuration Support**: YAML-based configuration
- **Logging**: Both file and console output with structured format

## Usage

### Basic Setup

```bash
python-script-runner --template etl_pipeline --output my_etl.py
```

### Customization

Replace these placeholders in the generated script:

- `{{SOURCE}}`: Data source type (csv, database, api, etc.)
- `{{TRANSFORM}}`: Transformation rules or functions
- `{{TARGET}}`: Target system (csv, database, warehouse, etc.)

### Running

```bash
python my_etl.py
```

## Extending the Template

1. **Modify Extract**: Implement your data source connection logic
2. **Modify Transform**: Add your business logic and transformations
3. **Modify Load**: Implement target system writes

## Best Practices

- Keep extracts and loads isolated for independent scaling
- Use configuration files for environment-specific settings
- Log all transformations for debugging
- Collect and report metrics for monitoring
- Handle partial failures gracefully

## Dependencies

- `pandas`: For CSV and data operations
- `sqlalchemy`: For database connections (optional)
- `pyyaml`: For configuration files (optional)

See `template.json` for required dependencies.
