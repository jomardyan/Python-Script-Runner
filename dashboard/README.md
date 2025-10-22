# Web Dashboard for Python Script Runner

Complete web-based dashboard for monitoring and analyzing script execution metrics.

## Features

### Real-Time Monitoring
- **WebSocket Connection**: Live metric updates every 2 seconds
- **Status Indicators**: Visual feedback of system health
- **Auto-Refresh**: Dashboard updates every 30 seconds

### Metrics Visualization
- **Trend Charts**: Time-series visualization of execution metrics
- **Distribution Analysis**: Performance distribution across runs
- **Aggregated Statistics**: Min, max, average, percentiles

### Executive Dashboard
- **Overview Cards**: Total executions, metrics, database size
- **Recent Executions Table**: Latest 20 runs with status
- **Quick Filters**: Filter by script and metric type

### Data Analysis
- **Trend Analysis**: Detect performance trends and regressions
- **Baseline Calculation**: Automatic baseline computation
- **Anomaly Detection**: Identify outliers and performance issues

### Export Capabilities
- **CSV Export**: Download metrics for external analysis
- **Detailed Views**: Drill down into individual executions

## Quick Start

### 1. Install Dependencies

```bash
pip install -r dashboard/backend/requirements.txt
```

### 2. Start the Dashboard Server

```bash
python dashboard/backend/app.py --port 8000
```

Or with custom database:

```bash
python dashboard/backend/app.py --db /path/to/database.db --port 8000
```

### 3. Access the Dashboard

Open your browser to `http://localhost:8000`

## API Reference

### REST Endpoints

#### Scripts Management
- `GET /api/scripts` - List all monitored scripts
- `GET /api/executions` - Get recent executions
- `GET /api/execution/{id}` - Get execution details

#### Metrics Data
- `GET /api/metrics/latest` - Get latest metrics
- `GET /api/metrics/history?script_path=X&metric_name=Y&days=7` - Get metric time-series
- `GET /api/metrics/aggregated?script_path=X&days=7` - Get aggregated stats

#### Analysis
- `GET /api/analysis/trend?script_path=X&metric_name=Y` - Trend analysis
- `GET /api/analysis/baseline?script_path=X&method=intelligent` - Baseline calculation

#### System
- `GET /api/health` - Health check
- `GET /api/stats/database` - Database statistics

### WebSocket

#### Real-Time Metrics Stream
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Metrics updated:', data);
};
```

## Architecture

### Backend
- **Framework**: FastAPI
- **Database**: SQLite (via HistoryManager)
- **Analytics**: TrendAnalyzer, BaselineCalculator
- **Real-time**: WebSocket support

### Frontend
- **Framework**: Vanilla JavaScript (no npm required)
- **Charts**: Chart.js library
- **Styling**: Custom CSS with responsive design
- **Features**: Real-time updates, interactive charts, data export

## Configuration

### Environment Variables

```bash
export DASHBOARD_HOST=0.0.0.0
export DASHBOARD_PORT=8000
export DASHBOARD_DB=/path/to/database.db
```

### CORS Configuration

The dashboard allows CORS requests from any origin by default. To restrict:

Edit `dashboard/backend/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Integration with Script Runner

The dashboard automatically connects to the historical data created by the main Script Runner.

### Prerequisites
1. Run scripts with history enabled: `python runner.py script.py`
2. This creates `script_runner_history.db`
3. Start dashboard pointing to the same database

### Example
```bash
# Terminal 1: Run scripts (creates history)
python runner.py my_script.py --retry 3

# Terminal 2: Start dashboard
python dashboard/backend/app.py --db script_runner_history.db

# Terminal 3: Open browser to http://localhost:8000
```

## Performance Considerations

- **Database**: SQLite supports ~1M metrics efficiently
- **WebSocket**: Broadcasts to all clients every 2 seconds
- **API**: Queries optimized with indexes on common filters
- **Frontend**: Lightweight (~100KB), no heavy dependencies

## Troubleshooting

### Dashboard won't connect
- Check database path is accessible
- Verify runner.py has created history data
- Check for database locks

### Slow performance
- Reduce history-days range in queries
- Consider archiving old data
- Use --history-limit flag

### WebSocket issues
- Check CORS configuration
- Verify no firewall blocking WebSocket
- Check browser console for errors

## Future Enhancements

- Real-time alerts and notifications
- Custom dashboard layouts
- Advanced filtering and search
- User authentication
- Email report scheduling
- Prometheus metrics export

## Development

### Running in Development Mode

```bash
uvicorn dashboard.backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Testing API Endpoints

```bash
curl http://localhost:8000/api/scripts
curl http://localhost:8000/api/stats/database
curl http://localhost:8000/api/metrics/latest?limit=10
```

### Frontend Customization

The frontend is a single HTML file in `dashboard/frontend/index.html`. Customize:
- Color scheme (CSS variables in `<style>`)
- Chart types (Chart.js configuration)
- Layout and responsive breakpoints
- Real-time update interval

## License

Same as Python Script Runner main project.
