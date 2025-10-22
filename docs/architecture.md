# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Python Script Runner                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐        ┌──────────────────────────┐   │
│  │ Script Executor  │◄───────┤ Input/Arguments         │   │
│  └────────┬─────────┘        └──────────────────────────┘   │
│           │                                                   │
│  ┌────────▼─────────────────────┐                           │
│  │ Process Monitor              │                           │
│  │ (CPU, Memory, I/O, Threads)  │                           │
│  └────────┬──────────────────────┘                          │
│           │                                                   │
│  ┌────────▼──────────────────────┐  ┌──────────────────┐   │
│  │ Alert Manager                │  │ Notification     │   │
│  │ (Conditions, Thresholds)     │─►│ Channels         │   │
│  └────────┬──────────────────────┘  │ (Email, Slack)  │   │
│           │                         └──────────────────┘   │
│  ┌────────▼──────────────────────┐  ┌──────────────────┐   │
│  │ CI/CD Integration            │  │ Performance      │   │
│  │ (Gates, Reports)             │─►│ Gates Checks     │   │
│  └────────┬──────────────────────┘  └──────────────────┘   │
│           │                                                   │
│  ┌────────▼────────────────────────────────────────────┐   │
│  │ History Manager & Analytics                        │   │
│  │ ┌──────────────┐ ┌──────────────┐                  │   │
│  │ │ SQLite DB    │ │ Trend        │                  │   │
│  │ │ (Metrics)    │ │ Analysis     │                  │   │
│  │ └──────────────┘ └──────────────┘                  │   │
│  └────────┬────────────────────────────────────────────┘   │
│           │                                                   │
│  ┌────────▼──────────────────────┐  ┌──────────────────┐   │
│  │ Advanced Features             │  │ Distributed      │   │
│  │ (Optimization, Forecasting)   │  │ Execution        │   │
│  └──────────────────────────────┘  │ (SSH, Docker)    │   │
│                                    └──────────────────┘   │
│                                                             │
└──────────────────────────────────────────────────────────┘
```

## Key Components

### ScriptRunner
Main execution engine coordinating all operations.

### ProcessMonitor
Background thread-based real-time monitoring of CPU, memory, I/O.

### AlertManager
Alert condition evaluation and notification delivery.

### HistoryManager
SQLite database abstraction for metrics persistence.

### TrendAnalyzer
Statistical analysis: linear regression, anomaly detection, regression detection.

### BaselineCalculator
Intelligent baseline selection from historical data.

### CICDIntegration
Performance gates, JUnit XML, TAP output generation.

### Advanced Features
- ML Anomaly Detection
- Metrics Correlation Analysis
- Performance Benchmarking
- Alert Intelligence
- Advanced Profiling
- Resource Forecasting
- Enterprise Integrations
- Distributed Execution

## Data Flow

1. **Execution**: Script runs in subprocess
2. **Monitoring**: Metrics collected at configurable intervals
3. **Evaluation**: Alerts checked against metrics
4. **Notification**: Triggered alerts sent immediately
5. **Reporting**: Results formatted for CI/CD systems
6. **Persistence**: Metrics saved to SQLite database
7. **Analysis**: Historical data analyzed for trends/anomalies

## Performance Characteristics

- **CPU Overhead**: < 2% on typical systems
- **Memory Overhead**: 5-15 MB base
- **Sampling Rate**: 10,000+ metrics/second
- **Database**: Scales to millions of records
- **Query Performance**: Sub-second for typical queries
