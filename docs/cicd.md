# CI/CD Integration

> Integrate Python Script Runner with CI/CD pipelines

## GitHub Actions

```yaml
name: Test with Performance Gates

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python runner.py tests/suite.py \
            --add-gate cpu_max:90 \
            --add-gate memory_max_mb:1024 \
            --junit-output test-results.xml
      - name: Publish results
        uses: EnricoMi/publish-unit-test-result-action@v2
        with:
          files: test-results.xml
```

## GitLab CI

```yaml
test:
  stage: test
  script:
    - pip install -r requirements.txt
    - python runner.py tests/suite.py \
        --add-gate cpu_max:90 \
        --add-gate memory_max_mb:1024 \
        --junit-output test-results.xml
  artifacts:
    reports:
      junit: test-results.xml
```

## Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'pip install -r requirements.txt'
                sh '''
                    python runner.py tests/suite.py \
                        --add-gate cpu_max:90 \
                        --junit-output test-results.xml
                '''
            }
        }
    }
    post {
        always {
            junit 'test-results.xml'
        }
    }
}
```

