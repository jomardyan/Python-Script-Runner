# REST API Integration Template

## Features

- **Resilient HTTP Client**: Automatic retries with exponential backoff
- **Multiple Auth Methods**: API key, Bearer token, Basic auth
- **Rate Limiting**: Built-in handling for 429 Too Many Requests
- **Metrics Tracking**: Request counts, success rates, latencies
- **Error Handling**: Comprehensive exception handling with logging
- **Type Hints**: Full type annotations for IDE support

## Usage

```bash
python-script-runner --template api_integration --output my_api.py
```

## Customization

Replace these placeholders:

- `{{BASE_URL}}`: Your API base URL (e.g., https://api.example.com/v1)
- `{{API_KEY}}`: Your API key or authentication token
- `{{ENDPOINT}}`: The API endpoint to call

## Example

```python
config = APIConfig(
    base_url="https://api.github.com",
    auth_type="bearer",
    api_key="your_token_here"
)

client = APIClient(config)
result = client.get("users/octocat")
```

## Best Practices

- Store API keys in environment variables, not in code
- Implement request timeouts to prevent hanging
- Use exponential backoff for retries
- Log all API interactions for debugging
- Monitor request metrics for performance
