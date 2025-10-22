# CI/CD Integration

## GitHub Actions

```yaml
name: Performance Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install psutil pyyaml requests
          pip install -r requirements.txt
      
      - name: Run with performance gates
        run: |
          python runner.py tests/suite.py \
            --add-gate cpu_max:85 \
            --add-gate memory_max_mb:2048 \
            --junit-output test-results.xml \
            --json-output metrics.json
      
      - name: Publish results
        if: always()
        uses: EnricoMi/publish-unit-test-result-action@v2
        with:
          files: test-results.xml
```

## Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                sh '''
                    pip install psutil pyyaml requests
                    python runner.py tests/suite.py \
                        --junit-output test-results.xml \
                        --add-gate cpu_max:90 \
                        --add-gate memory_max_mb:1024
                '''
            }
        }
        
        stage('Report') {
            steps {
                junit 'test-results.xml'
            }
        }
    }
}
```

## GitLab CI

```yaml
test_performance:
  stage: test
  image: python:3.11
  script:
    - pip install psutil pyyaml requests
    - python runner.py tests/suite.py
        --junit-output test-results.xml
        --add-gate cpu_max:85
  artifacts:
    reports:
      junit: test-results.xml
    expire_in: 30 days
```

## Performance Gates

Performance gates fail the build if metrics exceed thresholds:

```bash
python runner.py script.py \
    --add-gate cpu_max:90 \
    --add-gate memory_max_mb:1024 \
    --add-gate execution_time_seconds:120
```

Exit code is non-zero if any gate fails.

## Baseline Comparison

Track performance regression:

```bash
# First run
python runner.py script.py --save-baseline baseline.json

# Subsequent runs
python runner.py script.py --baseline baseline.json
```

Fails if current metrics exceed baseline by threshold.
