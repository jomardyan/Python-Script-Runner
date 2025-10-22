#!/usr/bin/env python3
"""
Automatic MkDocs Documentation Generator
Scans the Python Script Runner codebase and generates comprehensive documentation
"""

import os
import re
import ast
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any


class DocGenerator:
    """Generate MkDocs documentation from codebase"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.docs_path = self.root_path / "docs"
        self.runner_path = self.root_path / "runner.py"
        self.pyproject_path = self.root_path / "pyproject.toml"
        self.readme_path = self.root_path / "README.md"
        
        # Create docs directory
        self.docs_path.mkdir(exist_ok=True)
        
        # Parse version from runner.py
        self.version = self._extract_version()
        
    def _extract_version(self) -> str:
        """Extract version from runner.py"""
        try:
            with open(self.runner_path, 'r') as f:
                content = f.read()
                match = re.search(r'__version__\s*=\s*"([\d.]+)"', content)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"Warning: Could not extract version: {e}")
        return "4.2.0"
    
    def _parse_classes(self) -> Dict[str, Dict]:
        """Parse classes from runner.py"""
        classes = {}
        try:
            with open(self.runner_path, 'r') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Get class docstring
                    docstring = ast.get_docstring(node) or ""
                    
                    # Get methods
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                            method_doc = ast.get_docstring(item) or ""
                            methods.append({
                                'name': item.name,
                                'doc': method_doc.split('\n')[0] if method_doc else ""
                            })
                    
                    classes[node.name] = {
                        'doc': docstring,
                        'methods': methods[:5]  # First 5 public methods
                    }
        except Exception as e:
            print(f"Warning: Could not parse classes: {e}")
        
        return classes
    
    def _get_features_from_code(self) -> List[Tuple[str, str]]:
        """Extract features from code comments"""
        features = []
        try:
            with open(self.runner_path, 'r') as f:
                content = f.read()
                # Find feature sections marked with FEATURE: comments
                pattern = r'# ={60,}\n# FEATURE: (.+?)\n# ={60,}'
                matches = re.findall(pattern, content)
                for match in matches:
                    features.append(match.strip())
        except Exception as e:
            print(f"Warning: Could not extract features: {e}")
        
        return features
    
    def _parse_metrics(self) -> List[Dict]:
        """Parse collected metrics from code"""
        metrics = []
        try:
            with open(self.runner_path, 'r') as f:
                content = f.read()
                # Find metrics documentation
                pattern = r"'(\w+)'\s*[:\-]\s*([^\n]+)"
                matches = re.findall(pattern, content)
                seen = set()
                for name, desc in matches:
                    if name not in seen and len(metrics) < 30:
                        metrics.append({'name': name, 'description': desc.strip()})
                        seen.add(name)
        except Exception as e:
            print(f"Warning: Could not parse metrics: {e}")
        
        return metrics
    
    def generate_api_docs(self) -> str:
        """Generate API documentation"""
        classes = self._parse_classes()
        
        doc = "# API Reference\n\n"
        doc += "> Complete Python API documentation for Python Script Runner\n\n"
        
        doc += "## Overview\n\n"
        doc += f"Python Script Runner provides a comprehensive Python API with {len(classes)} main classes.\n\n"
        
        doc += "## Core Classes\n\n"
        
        for class_name in sorted(classes.keys()):
            if class_name.startswith('_'):
                continue
            
            class_info = classes[class_name]
            doc += f"### {class_name}\n\n"
            
            if class_info['doc']:
                first_line = class_info['doc'].split('\n')[0]
                doc += f"{first_line}\n\n"
            
            if class_info['methods']:
                doc += "**Methods:**\n\n"
                for method in class_info['methods']:
                    doc += f"- `{method['name']}()` - {method['doc']}\n"
                doc += "\n"
        
        doc += "## Usage Examples\n\n"
        
        doc += "### Basic Execution\n\n"
        doc += "```python\n"
        doc += "from runner import ScriptRunner\n\n"
        doc += "runner = ScriptRunner('myscript.py')\n"
        doc += "result = runner.execute()\n"
        doc += "print(f\"Exit code: {result['exit_code']}\")\n"
        doc += "```\n\n"
        
        doc += "### With History Tracking\n\n"
        doc += "```python\n"
        doc += "from runner import ScriptRunner, HistoryManager\n\n"
        doc += "history = HistoryManager('metrics.db')\n"
        doc += "runner = ScriptRunner('script.py', history_manager=history)\n"
        doc += "result = runner.execute()\n"
        doc += "```\n\n"
        
        doc += "### With Alerts\n\n"
        doc += "```python\n"
        doc += "from runner import ScriptRunner, AlertManager\n\n"
        doc += "runner = ScriptRunner('script.py')\n"
        doc += "alerts = AlertManager()\n"
        doc += "alerts.add_alert('cpu_high', 'cpu_max > 80')\n"
        doc += "result = runner.execute()\n"
        doc += "```\n\n"
        
        doc += "### Workflow Orchestration\n\n"
        doc += "```python\n"
        doc += "from runner import ScriptWorkflow\n\n"
        doc += "workflow = ScriptWorkflow('my_pipeline', max_parallel=4)\n"
        doc += "workflow.add_script('task1', 'script1.py')\n"
        doc += "workflow.add_script('task2', 'script2.py', dependencies=['task1'])\n"
        doc += "result = workflow.execute()\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_metrics_docs(self) -> str:
        """Generate metrics documentation"""
        metrics = self._parse_metrics()
        
        doc = "# Metrics Reference\n\n"
        doc += "> Complete guide to all metrics collected by Python Script Runner\n\n"
        
        doc += "## Overview\n\n"
        doc += f"Python Script Runner automatically collects {len(metrics)} different metrics during script execution.\n"
        doc += "All metrics are stored in SQLite database and available for analysis and alerting.\n\n"
        
        # Categorize metrics
        categories = {
            'Timing': ['start_time', 'end_time', 'execution_time'],
            'CPU': ['cpu_max', 'cpu_avg', 'cpu_min', 'user_time', 'system_time'],
            'Memory': ['memory_max', 'memory_avg', 'memory_min', 'page_faults'],
            'System': ['num_threads', 'num_fds', 'context_switches', 'block_io'],
            'Output': ['stdout_lines', 'stderr_lines', 'exit_code', 'success']
        }
        
        for category, keywords in categories.items():
            matching = [m for m in metrics if any(k in m['name'].lower() for k in keywords)]
            if matching or keywords:
                doc += f"## {category} Metrics\n\n"
                doc += f"| Metric | Type | Description |\n"
                doc += f"|--------|------|-------------|\n"
                for keyword in keywords:
                    doc += f"| `{keyword}` | float/int | {keyword.replace('_', ' ').title()} |\n"
                doc += "\n"
        
        doc += "## Querying Metrics\n\n"
        
        doc += "### Via HistoryManager\n\n"
        doc += "```python\n"
        doc += "from runner import HistoryManager\n\n"
        doc += "manager = HistoryManager('metrics.db')\n"
        doc += "history = manager.get_execution_history('script.py', days=30)\n"
        doc += "metrics = manager.get_aggregated_metrics('script.py')\n"
        doc += "```\n\n"
        
        doc += "### Via TimeSeriesDB\n\n"
        doc += "```python\n"
        doc += "from runner import TimeSeriesDB, HistoryManager\n\n"
        doc += "history_manager = HistoryManager('metrics.db')\n"
        doc += "ts_db = TimeSeriesDB(history_manager)\n"
        doc += "results = ts_db.query(\n"
        doc += "    metric_name='cpu_max',\n"
        doc += "    script_path='script.py',\n"
        doc += "    days=30\n"
        doc += ")\n"
        doc += "```\n\n"
        
        doc += "## Metric Aggregation\n\n"
        doc += "```python\n"
        doc += "aggs = ts_db.aggregations(\n"
        doc += "    metric_name='execution_time_seconds',\n"
        doc += "    script_path='script.py'\n"
        doc += ")\n"
        doc += "# Returns: min, max, avg, median, p50, p75, p90, p95, p99, stddev\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_features_docs(self) -> str:
        """Generate advanced features documentation"""
        features = self._get_features_from_code()
        
        doc = "# Advanced Features\n\n"
        doc += "> Comprehensive guide to advanced Python Script Runner features\n\n"
        
        doc += f"## Available Features ({len(features)})\n\n"
        
        for feature in features:
            doc += f"- **{feature}**\n"
        doc += "\n"
        
        doc += "## Trend Analysis\n\n"
        doc += "Automatically analyze performance trends:\n\n"
        doc += "```python\n"
        doc += "from runner import TrendAnalyzer\n\n"
        doc += "analyzer = TrendAnalyzer()\n"
        doc += "trend = analyzer.calculate_linear_regression(values)\n"
        doc += "# Returns: slope, intercept, r_squared, trend direction\n"
        doc += "```\n\n"
        
        doc += "## Anomaly Detection\n\n"
        doc += "Detect anomalies using multiple methods:\n\n"
        doc += "```python\n"
        doc += "# IQR method\n"
        doc += "anomalies = analyzer.detect_anomalies(values, method='iqr')\n\n"
        doc += "# Z-score method\n"
        doc += "anomalies = analyzer.detect_anomalies(values, method='zscore')\n\n"
        doc += "# MAD method\n"
        doc += "anomalies = analyzer.detect_anomalies(values, method='mad')\n"
        doc += "```\n\n"
        
        doc += "## Baseline Calculation\n\n"
        doc += "Intelligent baseline calculation:\n\n"
        doc += "```python\n"
        doc += "from runner import BaselineCalculator\n\n"
        doc += "calc = BaselineCalculator()\n"
        doc += "baseline = calc.calculate_intelligent_baseline(values)\n"
        doc += "# Auto-selects best method based on data characteristics\n"
        doc += "```\n\n"
        
        doc += "## Workflow Orchestration\n\n"
        doc += "Execute multiple scripts with DAG support:\n\n"
        doc += "```python\n"
        doc += "from runner import ScriptWorkflow\n\n"
        doc += "workflow = ScriptWorkflow('pipeline')\n"
        doc += "workflow.add_script('etl', 'etl.py')\n"
        doc += "workflow.add_script('train', 'train.py', dependencies=['etl'])\n"
        doc += "workflow.add_script('eval', 'eval.py', dependencies=['train'])\n"
        doc += "result = workflow.execute()\n"
        doc += "```\n\n"
        
        doc += "## Performance Optimization\n\n"
        doc += "Get optimization recommendations:\n\n"
        doc += "```python\n"
        doc += "from runner import PerformanceOptimizer\n\n"
        doc += "optimizer = PerformanceOptimizer(history_manager)\n"
        doc += "report = optimizer.get_optimization_report('script.py')\n"
        doc += "print(report)\n"
        doc += "```\n\n"
        
        doc += "## Alert Intelligence\n\n"
        doc += "Smart alert management:\n\n"
        doc += "```python\n"
        doc += "from runner import AlertIntelligence\n\n"
        doc += "intel = AlertIntelligence()\n"
        doc += "# Deduplicate alerts\n"
        doc += "alerts = intel.deduplicate_alerts(raw_alerts)\n"
        doc += "# Calculate adaptive thresholds\n"
        doc += "threshold = intel.calculate_adaptive_threshold('cpu', values)\n"
        doc += "```\n\n"
        
        doc += "## Benchmarking\n\n"
        doc += "Performance regression detection:\n\n"
        doc += "```python\n"
        doc += "from runner import BenchmarkManager\n\n"
        doc += "bm = BenchmarkManager()\n"
        doc += "bm.create_benchmark('v1.0', script_path='script.py')\n"
        doc += "# Later...\n"
        doc += "comparison = bm.compare_benchmarks('v1.0', 'v2.0')\n"
        doc += "regressions = bm.detect_regressions('benchmark_name')\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_architecture_docs(self) -> str:
        """Generate architecture documentation"""
        doc = "# Architecture Guide\n\n"
        doc += "> Deep dive into Python Script Runner's design and components\n\n"
        
        doc += "## System Architecture\n\n"
        doc += "```\n"
        doc += "┌─────────────────────────────────────────────┐\n"
        doc += "│         Python Script Runner                │\n"
        doc += "├─────────────────────────────────────────────┤\n"
        doc += "│                                             │\n"
        doc += "│  ┌─────────────────────────────────────┐   │\n"
        doc += "│  │  Execution Engine                   │   │\n"
        doc += "│  │  - Subprocess management           │   │\n"
        doc += "│  │  - Timeout handling                │   │\n"
        doc += "│  │  - Exit code processing            │   │\n"
        doc += "│  └─────────────────────────────────────┘   │\n"
        doc += "│                    ↓                        │\n"
        doc += "│  ┌─────────────────────────────────────┐   │\n"
        doc += "│  │  Real-Time Monitoring               │   │\n"
        doc += "│  │  - CPU/Memory/I/O metrics          │   │\n"
        doc += "│  │  - Process profiling                │   │\n"
        doc += "│  │  - Resource tracking                │   │\n"
        doc += "│  └─────────────────────────────────────┘   │\n"
        doc += "│                    ↓                        │\n"
        doc += "│  ┌─────────────────────────────────────┐   │\n"
        doc += "│  │  Analytics Pipeline                 │   │\n"
        doc += "│  │  - Trend analysis                   │   │\n"
        doc += "│  │  - Anomaly detection                │   │\n"
        doc += "│  │  - ML correlation                   │   │\n"
        doc += "│  └─────────────────────────────────────┘   │\n"
        doc += "│                    ↓                        │\n"
        doc += "│  ┌─────────────────────────────────────┐   │\n"
        doc += "│  │  Persistent Storage (SQLite)        │   │\n"
        doc += "│  │  - Execution records                │   │\n"
        doc += "│  │  - Metrics database                 │   │\n"
        doc += "│  │  - Alert history                    │   │\n"
        doc += "│  └─────────────────────────────────────┘   │\n"
        doc += "│                    ↓                        │\n"
        doc += "│  ┌─────────────────────────────────────┐   │\n"
        doc += "│  │  Alert & Notification               │   │\n"
        doc += "│  │  - Email alerts                     │   │\n"
        doc += "│  │  - Slack integration                │   │\n"
        doc += "│  │  - Webhook support                  │   │\n"
        doc += "│  └─────────────────────────────────────┘   │\n"
        doc += "│                                             │\n"
        doc += "└─────────────────────────────────────────────┘\n"
        doc += "```\n\n"
        
        doc += "## Core Components\n\n"
        
        doc += "### 1. Execution Engine\n"
        doc += "- Manages subprocess execution\n"
        doc += "- Handles timeouts and cancellation\n"
        doc += "- Captures stdout/stderr\n"
        doc += "- Processes exit codes\n\n"
        
        doc += "### 2. Monitoring System\n"
        doc += "- Real-time CPU/memory tracking\n"
        doc += "- I/O operation monitoring\n"
        doc += "- System resource profiling\n"
        doc += "- <2% overhead guarantee\n\n"
        
        doc += "### 3. Analytics Engine\n"
        doc += "- Trend analysis with linear regression\n"
        doc += "- Anomaly detection (IQR, Z-score, MAD methods)\n"
        doc += "- Regression detection\n"
        doc += "- Metrics correlation analysis\n\n"
        
        doc += "### 4. Storage Layer\n"
        doc += "- SQLite database for persistence\n"
        doc += "- Efficient indexing for queries\n"
        doc += "- Time-series data support\n"
        doc += "- Retention policy management\n\n"
        
        doc += "### 5. Alert System\n"
        doc += "- Rule-based alert triggering\n"
        doc += "- Multi-channel notifications\n"
        doc += "- Alert deduplication\n"
        doc += "- Adaptive thresholds\n\n"
        
        doc += "## Data Flow\n\n"
        doc += "```\n"
        doc += "Script Execution → Metrics Collection → Storage → Analysis\n"
        doc += "                                           ↓\n"
        doc += "                    Alert Triggers ← Threshold Evaluation\n"
        doc += "                           ↓\n"
        doc += "                   Notification Delivery\n"
        doc += "```\n\n"
        
        doc += "## Performance Characteristics\n\n"
        doc += "| Component | Latency | Throughput |\n"
        doc += "|-----------|---------|------------|\n"
        doc += "| Monitoring | <1ms sample | 10k metrics/sec |\n"
        doc += "| Alert Check | <10ms | 1k alerts/sec |\n"
        doc += "| Database Query | <100ms | 10k records/sec |\n"
        doc += "| Analysis | <500ms | 100 analyses/sec |\n\n"
        
        return doc
    
    def generate_cli_reference(self) -> str:
        """Generate CLI reference documentation"""
        doc = "# CLI Reference\n\n"
        doc += "> Complete command-line interface documentation\n\n"
        
        doc += "## Usage\n\n"
        doc += "```bash\n"
        doc += "python runner.py [SCRIPT] [OPTIONS]\n"
        doc += "```\n\n"
        
        doc += "## Common Options\n\n"
        doc += "### Basic Options\n"
        doc += "| Option | Description |\n"
        doc += "|--------|-------------|\n"
        doc += "| `--help` | Show help message |\n"
        doc += "| `--version` | Show version |\n"
        doc += "| `--config FILE` | Config file path |\n"
        doc += "| `--json-output FILE` | Output metrics as JSON |\n"
        doc += "| `--junit-output FILE` | Output as JUnit XML |\n\n"
        
        doc += "### Monitoring Options\n"
        doc += "| Option | Description |\n"
        doc += "|--------|-------------|\n"
        doc += "| `--history-db DB` | SQLite database path |\n"
        doc += "| `--detect-anomalies` | Detect anomalies |\n"
        doc += "| `--analyze-trend` | Analyze trends |\n"
        doc += "| `--detect-regression` | Detect regressions |\n\n"
        
        doc += "### Alert Options\n"
        doc += "| Option | Description |\n"
        doc += "|--------|-------------|\n"
        doc += "| `--alert-config RULE` | Add alert rule |\n"
        doc += "| `--slack-webhook URL` | Slack webhook URL |\n"
        doc += "| `--email-to ADDR` | Email recipient |\n\n"
        
        doc += "### Performance Gate Options\n"
        doc += "| Option | Description |\n"
        doc += "|--------|-------------|\n"
        doc += "| `--add-gate METRIC:VALUE` | Add performance gate |\n"
        doc += "| `--fail-on-gate-failure` | Exit with error on gate failure |\n\n"
        
        doc += "### Retry Options\n"
        doc += "| Option | Description |\n"
        doc += "|--------|-------------|\n"
        doc += "| `--retry-strategy STR` | Retry strategy (linear/exponential/fibonacci) |\n"
        doc += "| `--max-attempts N` | Maximum retry attempts |\n"
        doc += "| `--initial-delay SEC` | Initial delay in seconds |\n"
        doc += "| `--max-delay SEC` | Maximum delay in seconds |\n\n"
        
        doc += "## Examples\n\n"
        
        doc += "### Basic Execution\n"
        doc += "```bash\n"
        doc += "python runner.py myscript.py\n"
        doc += "```\n\n"
        
        doc += "### With Monitoring\n"
        doc += "```bash\n"
        doc += "python runner.py script.py \\\n"
        doc += "    --history-db metrics.db \\\n"
        doc += "    --detect-anomalies \\\n"
        doc += "    --analyze-trend\n"
        doc += "```\n\n"
        
        doc += "### CI/CD with Performance Gates\n"
        doc += "```bash\n"
        doc += "python runner.py tests/suite.py \\\n"
        doc += "    --add-gate cpu_max:90 \\\n"
        doc += "    --add-gate memory_max_mb:1024 \\\n"
        doc += "    --junit-output test-results.xml\n"
        doc += "```\n\n"
        
        doc += "### With Alerts\n"
        doc += "```bash\n"
        doc += "python runner.py script.py \\\n"
        doc += "    --config config.yaml \\\n"
        doc += "    --slack-webhook 'https://hooks.slack.com/...'\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_configuration_docs(self) -> str:
        """Generate configuration documentation"""
        doc = "# Configuration Guide\n\n"
        doc += "> Complete guide to configuring Python Script Runner\n\n"
        
        doc += "## Configuration File Format\n\n"
        doc += "Configuration files can be in YAML or JSON format.\n\n"
        
        doc += "### Basic Structure\n\n"
        doc += "```yaml\n"
        doc += "alerts:\n"
        doc += "  - name: alert_name\n"
        doc += "    condition: metric > threshold\n"
        doc += "    channels: [email, slack]\n"
        doc += "    severity: WARNING\n\n"
        doc += "performance_gates:\n"
        doc += "  - metric_name: cpu_max\n"
        doc += "    max_value: 90\n\n"
        doc += "notifications:\n"
        doc += "  email:\n"
        doc += "    smtp_server: smtp.gmail.com\n"
        doc += "    smtp_port: 587\n"
        doc += "    from: alerts@company.com\n\n"
        doc += "retry:\n"
        doc += "  strategy: exponential\n"
        doc += "  max_attempts: 3\n"
        doc += "```\n\n"
        
        doc += "## Alert Configuration\n\n"
        doc += "```yaml\n"
        doc += "alerts:\n"
        doc += "  - name: cpu_high\n"
        doc += "    condition: cpu_max > 85\n"
        doc += "    channels: [email, slack]\n"
        doc += "    severity: WARNING\n"
        doc += "    enabled: true\n"
        doc += "```\n\n"
        
        doc += "## Performance Gates\n\n"
        doc += "```yaml\n"
        doc += "performance_gates:\n"
        doc += "  - metric_name: cpu_max\n"
        doc += "    max_value: 90\n"
        doc += "  - metric_name: memory_max_mb\n"
        doc += "    max_value: 1024\n"
        doc += "```\n\n"
        
        doc += "## Notifications Configuration\n\n"
        
        doc += "### Email\n\n"
        doc += "```yaml\n"
        doc += "notifications:\n"
        doc += "  email:\n"
        doc += "    smtp_server: smtp.gmail.com\n"
        doc += "    smtp_port: 587\n"
        doc += "    from: alerts@company.com\n"
        doc += "    to: team@company.com\n"
        doc += "    use_tls: true\n"
        doc += "    username: your_email@gmail.com\n"
        doc += "    password: your_app_password\n"
        doc += "```\n\n"
        
        doc += "### Slack\n\n"
        doc += "```yaml\n"
        doc += "notifications:\n"
        doc += "  slack:\n"
        doc += "    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK\n"
        doc += "    channel: '#alerts'\n"
        doc += "    username: PSR Bot\n"
        doc += "```\n\n"
        
        doc += "## Retry Configuration\n\n"
        doc += "```yaml\n"
        doc += "retry:\n"
        doc += "  strategy: exponential  # linear, exponential, fibonacci\n"
        doc += "  max_attempts: 3\n"
        doc += "  initial_delay: 2       # seconds\n"
        doc += "  max_delay: 60          # seconds\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_troubleshooting_docs(self) -> str:
        """Generate troubleshooting documentation"""
        doc = "# Troubleshooting Guide\n\n"
        doc += "> Solutions for common issues and problems\n\n"
        
        doc += "## Installation Issues\n\n"
        
        doc += "### ImportError: No module named 'psutil'\n\n"
        doc += "**Problem**: psutil dependency is not installed\n\n"
        doc += "**Solution**:\n"
        doc += "```bash\n"
        doc += "pip install psutil\n"
        doc += "```\n\n"
        
        doc += "### ImportError: No module named 'yaml'\n\n"
        doc += "**Problem**: PyYAML is not installed\n\n"
        doc += "**Solution**:\n"
        doc += "```bash\n"
        doc += "pip install pyyaml\n"
        doc += "# Or use JSON config instead:\n"
        doc += "python runner.py script.py --json-config config.json\n"
        doc += "```\n\n"
        
        doc += "## Runtime Issues\n\n"
        
        doc += "### Database Lock Error\n\n"
        doc += "**Problem**: `sqlite3.OperationalError: database is locked`\n\n"
        doc += "**Causes**:\n"
        doc += "- Multiple processes accessing database simultaneously\n"
        doc += "- Corrupted WAL files\n\n"
        doc += "**Solutions**:\n"
        doc += "```bash\n"
        doc += "# Remove lock files\n"
        doc += "rm -f script_runner_history.db-wal\n"
        doc += "rm -f script_runner_history.db-shm\n\n"
        doc += "# Or use separate database per process\n"
        doc += "python runner.py script.py --history-db metrics_$$.db\n"
        doc += "```\n\n"
        
        doc += "### Memory Usage Growing\n\n"
        doc += "**Problem**: Script Runner using too much memory\n\n"
        doc += "**Solutions**:\n"
        doc += "- Disable real-time monitoring if not needed\n"
        doc += "- Archive old database records\n"
        doc += "- Use smaller retention period\n\n"
        
        doc += "### Alerts Not Triggering\n\n"
        doc += "**Problem**: Alert conditions met but no alerts sent\n\n"
        doc += "**Solutions**:\n"
        doc += "- Check alert configuration syntax\n"
        doc += "- Verify notification credentials (email, Slack)\n"
        doc += "- Check network connectivity\n"
        doc += "- Enable debug logging\n\n"
        
        doc += "## Monitoring Issues\n\n"
        
        doc += "### High CPU Usage\n\n"
        doc += "**Problem**: Script Runner using high CPU\n\n"
        doc += "**Solutions**:\n"
        doc += "- Reduce monitoring frequency\n"
        doc += "- Disable unnecessary features\n"
        doc += "- Use PyPy for faster execution\n\n"
        
        doc += "### Missing Metrics\n\n"
        doc += "**Problem**: Some metrics not collected\n\n"
        doc += "**Solutions**:\n"
        doc += "- Check script execution time (need minimum time for sampling)\n"
        doc += "- Verify monitoring is enabled\n"
        doc += "- Check for process termination\n\n"
        
        doc += "## Performance Issues\n\n"
        
        doc += "### Slow Query Performance\n\n"
        doc += "**Problem**: Database queries are slow\n\n"
        doc += "**Solutions**:\n"
        doc += "```bash\n"
        doc += "# Archive old data\n"
        doc += "python runner.py --archive-db metrics.db --days 90\n\n"
        doc += "# Vacuum database\n"
        doc += "sqlite3 metrics.db \"VACUUM;\"\n"
        doc += "```\n\n"
        
        doc += "## Debugging\n\n"
        
        doc += "### Enable Debug Logging\n\n"
        doc += "```python\n"
        doc += "import logging\n"
        doc += "logging.basicConfig(level=logging.DEBUG)\n"
        doc += "\n"
        doc += "from runner import ScriptRunner\n"
        doc += "runner = ScriptRunner('script.py')\n"
        doc += "result = runner.execute()\n"
        doc += "```\n\n"
        
        doc += "### Check Database\n\n"
        doc += "```bash\n"
        doc += "# List tables\n"
        doc += "sqlite3 metrics.db \".tables\"\n\n"
        doc += "# Check recent executions\n"
        doc += "sqlite3 metrics.db \"SELECT * FROM executions LIMIT 5;\"\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_usage_docs(self) -> str:
        """Generate usage documentation"""
        doc = "# Usage Guide\n\n"
        doc += "> Common usage scenarios and best practices\n\n"
        
        doc += "## Basic Usage\n\n"
        doc += "```bash\n"
        doc += "python runner.py myscript.py\n"
        doc += "```\n\n"
        
        doc += "## With Arguments\n\n"
        doc += "```bash\n"
        doc += "python runner.py train.py --epochs 100 --batch-size 32\n"
        doc += "```\n\n"
        
        doc += "## Continuous Monitoring\n\n"
        doc += "```bash\n"
        doc += "python runner.py script.py \\\n"
        doc += "    --history-db metrics.db \\\n"
        doc += "    --detect-anomalies \\\n"
        doc += "    --analyze-trend\n"
        doc += "```\n\n"
        
        doc += "## CI/CD Integration\n\n"
        doc += "```bash\n"
        doc += "python runner.py tests/suite.py \\\n"
        doc += "    --add-gate cpu_max:90 \\\n"
        doc += "    --add-gate memory_max_mb:1024 \\\n"
        doc += "    --junit-output results.xml\n"
        doc += "```\n\n"
        
        doc += "## Remote Execution\n\n"
        doc += "```bash\n"
        doc += "python runner.py script.py \\\n"
        doc += "    --ssh-host prod.example.com \\\n"
        doc += "    --ssh-user deploy \\\n"
        doc += "    --ssh-key ~/.ssh/id_rsa\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_cicd_docs(self) -> str:
        """Generate CI/CD integration documentation"""
        doc = "# CI/CD Integration\n\n"
        doc += "> Integrate Python Script Runner with CI/CD pipelines\n\n"
        
        doc += "## GitHub Actions\n\n"
        doc += "```yaml\n"
        doc += "name: Test with Performance Gates\n\n"
        doc += "on: [push, pull_request]\n\n"
        doc += "jobs:\n"
        doc += "  test:\n"
        doc += "    runs-on: ubuntu-latest\n"
        doc += "    steps:\n"
        doc += "      - uses: actions/checkout@v2\n"
        doc += "      - uses: actions/setup-python@v2\n"
        doc += "        with:\n"
        doc += "          python-version: '3.11'\n"
        doc += "      - run: pip install -r requirements.txt\n"
        doc += "      - run: python runner.py tests/suite.py \\\n"
        doc += "            --add-gate cpu_max:90 \\\n"
        doc += "            --add-gate memory_max_mb:1024 \\\n"
        doc += "            --junit-output test-results.xml\n"
        doc += "      - name: Publish results\n"
        doc += "        uses: EnricoMi/publish-unit-test-result-action@v2\n"
        doc += "        with:\n"
        doc += "          files: test-results.xml\n"
        doc += "```\n\n"
        
        doc += "## GitLab CI\n\n"
        doc += "```yaml\n"
        doc += "test:\n"
        doc += "  stage: test\n"
        doc += "  script:\n"
        doc += "    - pip install -r requirements.txt\n"
        doc += "    - python runner.py tests/suite.py \\\n"
        doc += "        --add-gate cpu_max:90 \\\n"
        doc += "        --add-gate memory_max_mb:1024 \\\n"
        doc += "        --junit-output test-results.xml\n"
        doc += "  artifacts:\n"
        doc += "    reports:\n"
        doc += "      junit: test-results.xml\n"
        doc += "```\n\n"
        
        doc += "## Jenkins\n\n"
        doc += "```groovy\n"
        doc += "pipeline {\n"
        doc += "    agent any\n"
        doc += "    stages {\n"
        doc += "        stage('Test') {\n"
        doc += "            steps {\n"
        doc += "                sh 'pip install -r requirements.txt'\n"
        doc += "                sh '''\n"
        doc += "                    python runner.py tests/suite.py \\\n"
        doc += "                        --add-gate cpu_max:90 \\\n"
        doc += "                        --junit-output test-results.xml\n"
        doc += "                '''\n"
        doc += "            }\n"
        doc += "        }\n"
        doc += "    }\n"
        doc += "    post {\n"
        doc += "        always {\n"
        doc += "            junit 'test-results.xml'\n"
        doc += "        }\n"
        doc += "    }\n"
        doc += "}\n"
        doc += "```\n\n"
        
        return doc
    
    def generate_index_docs(self) -> str:
        """Generate index documentation"""
        doc = "# Python Script Runner\n\n"
        doc += "> **Enterprise-grade Python script execution engine with real-time monitoring, alerting, analytics, and distributed execution.**\n\n"
        
        doc += "[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)\n"
        doc += "[![Python 3.6+](https://img.shields.io/badge/python-3.6%2B-blue?logo=python&logoColor=white)](https://www.python.org/)\n"
        doc += "[![Status: Production Ready](https://img.shields.io/badge/status-production--ready-brightgreen)](https://github.com/jomardyan/Python-Script-Runner/releases)\n\n"
        
        doc += "## Overview\n\n"
        doc += "Python Script Runner transforms script execution into a production-ready operation with:\n\n"
        doc += "- 🔍 **Real-Time Monitoring** - CPU, memory, I/O tracking with <2% overhead\n"
        doc += "- 📢 **Multi-Channel Alerts** - Email, Slack, webhooks with threshold-based logic\n"
        doc += "- 📊 **Historical Analytics** - SQLite backend with trend analysis & anomaly detection\n"
        doc += "- 🔄 **Retry Strategies** - Linear, exponential, Fibonacci backoff with smart filtering\n"
        doc += "- 📈 **Advanced Profiling** - CPU/memory/I/O analysis with bottleneck identification\n"
        doc += "- 🏢 **Enterprise Ready** - Datadog, Prometheus, New Relic integrations\n"
        doc += "- 🌐 **Distributed Execution** - SSH, Docker, Kubernetes support\n"
        doc += "- 📊 **Web Dashboard** - Real-time metrics visualization & RESTful API\n"
        doc += "- 🤖 **ML-Powered** - Anomaly detection, forecasting, correlation analysis\n\n"
        
        doc += "## Quick Start\n\n"
        doc += "```bash\n"
        doc += "# Installation\n"
        doc += "git clone https://github.com/jomardyan/Python-Script-Runner.git\n"
        doc += "cd Python-Script-Runner\n"
        doc += "pip install -r requirements.txt\n\n"
        doc += "# Run\n"
        doc += "python runner.py myscript.py\n"
        doc += "```\n\n"
        
        doc += "## Key Features\n\n"
        doc += "| Feature | Description | Status |\n"
        doc += "|---------|-------------|--------|\n"
        doc += "| **Real-Time Monitoring** | CPU, memory, I/O, system resources | ✅ Production |\n"
        doc += "| **Alert System** | Email, Slack, webhooks, custom handlers | ✅ Production |\n"
        doc += "| **CI/CD Integration** | Performance gates, JUnit/TAP output | ✅ Production |\n"
        doc += "| **Historical Tracking** | SQLite database with metrics persistence | ✅ Production |\n"
        doc += "| **Trend Analysis** | Linear regression, anomaly detection | ✅ Production |\n"
        doc += "| **Multi-Script Workflows** | DAG-based orchestration with dependencies | ✅ Production |\n"
        doc += "| **Data Export** | CSV, JSON, Parquet formats | ✅ Production |\n"
        doc += "| **ML Anomaly Detection** | Z-score, IQR, trend-based methods | ✅ Production |\n"
        doc += "| **Metrics Correlation** | Pearson correlation, predictor analysis | ✅ Production |\n"
        doc += "| **Performance Benchmarking** | Regression detection, version comparison | ✅ Production |\n\n"
        
        doc += "## Documentation\n\n"
        doc += "- 📖 **[Installation](installation.md)** - Setup and requirements\n"
        doc += "- 🚀 **[Quick Start](quickstart.md)** - First steps guide\n"
        doc += "- 📚 **[Usage Guide](usage.md)** - Common use cases\n"
        doc += "- 🔧 **[CLI Reference](cli-reference.md)** - Command-line options\n"
        doc += "- ⚙️ **[Configuration](configuration.md)** - Config file guide\n"
        doc += "- 🔄 **[CI/CD Integration](cicd.md)** - Pipeline setup\n"
        doc += "- 📡 **[API Documentation](api.md)** - Python API reference\n"
        doc += "- 📊 **[Metrics Guide](metrics.md)** - Metrics details\n"
        doc += "- 🏗️ **[Architecture](architecture.md)** - System design\n"
        doc += "- 🔬 **[Advanced Features](advanced.md)** - Advanced topics\n"
        doc += "- 🐛 **[Troubleshooting](troubleshooting.md)** - Common issues\n\n"
        
        doc += "## Getting Help\n\n"
        doc += "- 📋 [Issues](https://github.com/jomardyan/Python-Script-Runner/issues)\n"
        doc += "- 💬 [Discussions](https://github.com/jomardyan/Python-Script-Runner/discussions)\n\n"
        
        doc += "## License\n\n"
        doc += "MIT License - see [LICENSE](../LICENSE) for details.\n\n"
        doc += f"---\n\n**Version**: {self.version} | **Status**: Production Ready | **Last Updated**: {datetime.now().strftime('%B %Y')}\n"
        
        return doc
    
    def generate_installation_docs(self) -> str:
        """Generate installation documentation"""
        doc = "# Installation Guide\n\n"
        doc += "## System Requirements\n\n"
        doc += "### Minimum\n"
        doc += "- **Python**: 3.6+ (3.8+ recommended)\n"
        doc += "- **OS**: Linux, macOS, Windows (with WSL2)\n"
        doc += "- **RAM**: 256 MB minimum (512 MB recommended)\n"
        doc += "- **Disk**: ~50 MB for installation\n\n"
        
        doc += "### Required Dependencies\n"
        doc += "- **psutil** (5.9.0+) - Process monitoring\n"
        doc += "- **PyYAML** (6.0+) - Config parsing\n"
        doc += "- **requests** (2.31.0+) - HTTP requests\n\n"
        
        doc += "### Optional Dependencies\n"
        doc += "- **fastapi** - Web dashboard\n"
        doc += "- **pyarrow** - Parquet export\n"
        doc += "- **scikit-learn** - ML features\n\n"
        
        doc += "## Installation Steps\n\n"
        doc += "### Method 1: From Repository\n\n"
        doc += "```bash\n"
        doc += "git clone https://github.com/jomardyan/Python-Script-Runner.git\n"
        doc += "cd Python-Script-Runner\n"
        doc += "pip install -r requirements.txt\n"
        doc += "python runner.py --version\n"
        doc += "```\n\n"
        
        doc += "### Method 2: Virtual Environment (Recommended)\n\n"
        doc += "```bash\n"
        doc += "python -m venv venv\n"
        doc += "source venv/bin/activate  # Windows: venv\\\\Scripts\\\\activate\n"
        doc += "pip install -r requirements.txt\n"
        doc += "```\n\n"
        
        doc += "### Method 3: PyPy3 (High Performance)\n\n"
        doc += "```bash\n"
        doc += "bash setup_pypy3_env.sh\n"
        doc += "source .venv-pypy3/bin/activate\n"
        doc += "pypy3 runner.py myscript.py\n"
        doc += "```\n\n"
        
        doc += "### Method 4: Docker\n\n"
        doc += "```bash\n"
        doc += "docker build -t psr .\n"
        doc += "docker run --rm psr myscript.py\n"
        doc += "```\n\n"
        
        doc += "## Verification\n\n"
        doc += "```bash\n"
        doc += "python runner.py --version\n"
        doc += "python runner.py --help\n"
        doc += "python runner.py test_script.py\n"
        doc += "```\n\n"
        
        doc += "## Troubleshooting\n\n"
        doc += "See [Troubleshooting Guide](troubleshooting.md) for common issues.\n"
        
        return doc
    
    def generate_quickstart_docs(self) -> str:
        """Generate quickstart documentation"""
        doc = "# Quick Start\n\n"
        doc += "Get up and running in 5 minutes!\n\n"
        
        doc += "## Installation\n\n"
        doc += "```bash\n"
        doc += "git clone https://github.com/jomardyan/Python-Script-Runner.git\n"
        doc += "cd Python-Script-Runner\n"
        doc += "pip install -r requirements.txt\n"
        doc += "```\n\n"
        
        doc += "## Your First Script\n\n"
        doc += "Create `test_app.py`:\n\n"
        doc += "```python\n"
        doc += "import time\n"
        doc += "print('Starting...')\n"
        doc += "for i in range(5):\n"
        doc += "    print(f'Step {i+1}')\n"
        doc += "    time.sleep(0.5)\n"
        doc += "print('Done!')\n"
        doc += "```\n\n"
        
        doc += "Run with monitoring:\n\n"
        doc += "```bash\n"
        doc += "python runner.py test_app.py\n"
        doc += "```\n\n"
        
        doc += "## Common Use Cases\n\n"
        
        doc += "### CI/CD with Performance Gates\n\n"
        doc += "```bash\n"
        doc += "python runner.py tests/suite.py \\\\\n"
        doc += "    --add-gate cpu_max:90 \\\\\n"
        doc += "    --add-gate memory_max_mb:1024 \\\\\n"
        doc += "    --junit-output results.xml\n"
        doc += "```\n\n"
        
        doc += "### Track Performance Over Time\n\n"
        doc += "```bash\n"
        doc += "python runner.py script.py \\\\\n"
        doc += "    --history-db metrics.db \\\\\n"
        doc += "    --detect-anomalies \\\\\n"
        doc += "    --analyze-trend\n"
        doc += "```\n\n"
        
        doc += "### Slack Alerts\n\n"
        doc += "```bash\n"
        doc += "python runner.py script.py \\\\\n"
        doc += "    --slack-webhook 'https://hooks.slack.com/services/YOUR/WEBHOOK'\n"
        doc += "```\n\n"
        
        doc += "## Next Steps\n\n"
        doc += "- 📖 [Installation](installation.md)\n"
        doc += "- 📚 [Usage Guide](usage.md)\n"
        doc += "- 🔧 [CLI Reference](cli-reference.md)\n"
        doc += "- ⚙️ [Configuration](configuration.md)\n"
        
        return doc
    
    def generate_all(self):
        """Generate all documentation files"""
        print("Generating MkDocs documentation...")
        
        docs_to_generate = {
            'index.md': self.generate_index_docs,
            'installation.md': self.generate_installation_docs,
            'quickstart.md': self.generate_quickstart_docs,
            'api.md': self.generate_api_docs,
            'metrics.md': self.generate_metrics_docs,
            'advanced.md': self.generate_features_docs,
            'architecture.md': self.generate_architecture_docs,
            'cli-reference.md': self.generate_cli_reference,
            'configuration.md': self.generate_configuration_docs,
            'troubleshooting.md': self.generate_troubleshooting_docs,
            'usage.md': self.generate_usage_docs,
            'cicd.md': self.generate_cicd_docs,
        }
        
        for filename, generator_func in docs_to_generate.items():
            filepath = self.docs_path / filename
            try:
                content = generator_func()
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"✅ Generated {filename}")
            except Exception as e:
                print(f"❌ Error generating {filename}: {e}")
        
        print("\n✅ Documentation generation complete!")
        print(f"📁 Docs location: {self.docs_path}")
        print("\n📖 To view documentation locally:")
        print("   pip install mkdocs mkdocs-material")
        print("   mkdocs serve")
        print("\n🌐 Then visit: http://localhost:8000")


def main():
    """Main entry point"""
    import sys
    
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    generator = DocGenerator(root_path)
    generator.generate_all()


if __name__ == '__main__':
    main()
