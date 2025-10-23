# File Processing Template

## Features

- **Batch Operations**: Process multiple files efficiently
- **Progress Tracking**: Real-time progress with file count and metrics
- **Error Recovery**: Continue processing even if individual files fail
- **File Filtering**: Glob patterns for selective file processing
- **Metrics Collection**: Throughput, duration, and success rates
- **Recursive Search**: Optional subdirectory traversal

## Usage

```bash
python-script-runner --template file_processing --output my_processor.py
```

## Customization

Replace these placeholders:

- `{{SOURCE_DIR}}`: Directory containing files to process
- `{{PATTERN}}`: Glob pattern (e.g., "*.txt", "*.csv", "*.log")

## Example

```bash
python my_processor.py
```

## Implementation

The template provides a base processor. Customize the `process_line_by_line` function with your logic:

```python
def process_line_by_line(file_path: Path) -> bool:
    """Your custom file processing logic."""
    with open(file_path, 'r') as f:
        for line in f:
            # Process each line
            pass
    return True  # Return True if successful
```

## Best Practices

- Use glob patterns for efficient file filtering
- Handle encoding errors gracefully
- Log progress for monitoring
- Collect metrics for optimization
- Skip problematic files and continue processing
