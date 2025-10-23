# Data Transformation Template

## Features

- **Data Loading**: Support for CSV, JSON, Excel formats
- **Data Exploration**: Summary statistics and data profiling
- **Cleaning**: Duplicate removal, missing value handling, type conversion
- **Transformation**: Computed columns, date extraction, text normalization
- **Aggregation**: Group by statistics and summaries
- **Flexible Output**: Save to multiple formats

## Usage

```bash
python-script-runner --template data_transformation --output my_transform.py
```

## Customization

Replace placeholders:

- `{{INPUT_FILE}}`: Path to input data file
- `{{OUTPUT_FILE}}`: Path to output data file
- `{{TRANSFORMATIONS}}`: Custom transformation logic

## Example

```python
transformer = DataTransformer('input.csv')
transformer.load_data()
transformer.clean_data()
transformer.transform_data()
transformer.save_data('output.csv')
```

## Supported Formats

- **Input**: CSV, JSON, Excel
- **Output**: CSV, JSON, Excel

## Best Practices

- Always explore data first with `explore_data()`
- Handle missing values appropriately for your use case
- Validate transformations with statistics
- Log all transformations applied
- Test with sample data before full runs
