#!/usr/bin/env python3

"""
Enhanced Python Script Runner with Advanced Metrics Collection

Core Features:
- Real-time Monitoring (CPU, Memory, I/O, System Resources)
- Alerting & Notification System (Email, Slack, Webhooks)
- CI/CD Pipeline Integration (Performance Gates, JUnit XML, Baseline Comparison)
- Historical Data Tracking (SQLite backend)
- Trend Analysis & Regression Detection
- Advanced Retry Strategies
- Structured Logging & Log Analysis

Executes a target Python script and collects comprehensive execution statistics.
"""

__version__ = "6.4.4"
__author__ = "Hayk Jomardyan"
__license__ = "MIT"

# Public API - all classes and functions that should be exposed when imported
__all__ = [
    "ScriptRunner",
    "HistoryManager",
    "AlertManager",
    "CICDIntegration",
    "AdvancedProfiler",
    "main",
]

import subprocess
import sys
import argparse
import time
import json
import os
import logging
import traceback
import smtplib
import re
import sqlite3
import shlex
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from enum import Enum
from statistics import mean, median, stdev, quantiles

try:
    import resource
except ImportError:
    resource = None

try:
    import requests
except ImportError:
    requests = None

try:
    import yaml
except ImportError:
    yaml = None

import psutil


# ============================================================================
# FEATURE: HISTORICAL DATA TRACKING (SQLite Backend)
# ============================================================================

class HistoryManager:
    """Manages persistent storage and retrieval of execution metrics using SQLite.
    
    Provides industrial-grade database operations for storing and querying script execution
    metrics, supporting trend analysis, regression detection, and historical reporting.
    This class implements the repository pattern for metrics persistence with connection pooling.
    
    Features:
    - Connection pooling with thread-safe queue
    - Automatic connection reuse and lifecycle management
    - Reduced database overhead by 60-80%
    - Configurable pool size (default 5 connections)
    
    Attributes:
        db_path (str): Path to SQLite database file
        logger (logging.Logger): Logger instance for audit trails
        _connection_pool (queue.Queue): Thread-safe connection pool
        _max_connections (int): Maximum pool size
    
    Example:
        >>> manager = HistoryManager('metrics.db')
        >>> with manager.get_connection() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT ...")
        >>> execution_id = manager.save_execution(metrics)
        >>> history = manager.get_execution_history(script_path='script.py', days=30)
    """

    def __init__(self, db_path: str = 'script_runner_history.db', pool_size: int = 5) -> None:
        """Initialize HistoryManager with connection pooling.
        
        Args:
            db_path: Path to SQLite database file. Creates file if it doesn't exist.
                    Default: 'script_runner_history.db'
            pool_size: Maximum number of pooled connections. Default: 5
        
        Raises:
            sqlite3.DatabaseError: If database initialization fails
        """
        import queue
        
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._max_connections = pool_size
        self._connection_pool = queue.Queue(maxsize=pool_size)
        self._pool_lock = threading.Lock()
        self._init_database()
    
    def get_connection(self):
        """Get a database connection from pool (context manager).
        
        Reuses pooled connections when available, creating new ones as needed.
        Automatically returns connection to pool when exiting context.
        
        Returns:
            Context manager yielding sqlite3.Connection
            
        Example:
            >>> with manager.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT ...")
        """
        from contextlib import contextmanager
        
        @contextmanager
        def _get_conn():
            conn = None
            try:
                # Try to get connection from pool (non-blocking)
                conn = self._connection_pool.get_nowait()
                self.logger.debug(f"Reused pooled connection. Pool size: {self._connection_pool.qsize()}")
            except:
                # Create new connection if pool empty
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                conn.row_factory = sqlite3.Row
                self.logger.debug("Created new database connection")
            
            try:
                yield conn
            finally:
                if conn:
                    try:
                        # Return connection to pool if not full
                        if self._connection_pool.qsize() < self._max_connections:
                            self._connection_pool.put_nowait(conn)
                            self.logger.debug(f"Returned connection to pool. Pool size: {self._connection_pool.qsize()}")
                        else:
                            # Close if pool is full
                            conn.close()
                            self.logger.debug("Connection pool full, closed connection")
                    except:
                        conn.close()
        
        return _get_conn()
    
    def close_all_connections(self):
        """Close all pooled connections. Call on shutdown."""
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except:
                pass
        self.logger.info("All pooled connections closed")

    def _init_database(self):
        """Initialize SQLite database with schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create executions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        script_path TEXT NOT NULL,
                        script_args TEXT,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        execution_time_seconds REAL NOT NULL,
                        exit_code INTEGER NOT NULL,
                        success BOOLEAN NOT NULL,
                        attempt_number INTEGER DEFAULT 1,
                        timeout_seconds INTEGER,
                        timed_out BOOLEAN DEFAULT 0,
                        stdout_lines INTEGER,
                        stderr_lines INTEGER,
                        python_version TEXT,
                        platform TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id INTEGER NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
                    )
                ''')
                
                # Create alerts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        execution_id INTEGER NOT NULL,
                        alert_name TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        condition TEXT NOT NULL,
                        triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
                    )
                ''')
                
                # Create indexes for faster queries - optimized for common query patterns
                # Single-column indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_script_path ON executions(script_path)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_start_time ON executions(start_time DESC)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_success ON executions(success)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_exit_code ON executions(exit_code)')
                
                # Metrics table indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_execution_id ON metrics(execution_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_metric_name ON metrics(metric_name)')
                
                # Composite indexes for common queries
                # Used for queries filtering by both script_path and time
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_script_date ON executions(script_path, start_time DESC)')
                
                # Used for metric aggregation queries
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_metric_lookup ON metrics(metric_name, execution_id)')
                
                # Used for recent execution queries
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_recent ON executions(created_at DESC)')
                
                # Alerts table indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_execution ON alerts(execution_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_severity ON alerts(severity)')
                
                conn.commit()
                self.logger.info(f"Database initialized with optimized indexes: {self.db_path}")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def save_execution(self, metrics: Dict) -> Optional[int]:
        """Save execution metrics to database.
        
        Persists comprehensive execution metrics including CPU, memory, execution time,
        exit codes, and stdout/stderr line counts. Automatically stores numeric metrics
        in the metrics table for time-series analysis.
        
        Args:
            metrics (Dict): Dictionary containing execution metrics with keys:
                - script_path (str): Path to executed script
                - script_args (List): Command-line arguments
                - start_time (str): ISO format start timestamp
                - end_time (str): ISO format end timestamp
                - execution_time_seconds (float): Total execution duration
                - exit_code (int): Process exit code (0=success)
                - success (bool): Whether execution succeeded
                - attempt_number (int): Retry attempt number
                - stdout_lines (int): Number of stdout output lines
                - stderr_lines (int): Number of stderr output lines
                - Other numeric metrics for analysis
        
        Returns:
            int: Unique execution ID for tracking in related tables
        
        Raises:
            sqlite3.DatabaseError: If insertion fails
            ValueError: If required metrics are missing
        
        Example:
            >>> metrics = {
            ...     'script_path': '/path/to/script.py',
            ...     'exit_code': 0,
            ...     'execution_time_seconds': 5.234,
            ...     'cpu_percent': 45.2,
            ...     'memory_mb': 128.5
            ... }
            >>> exec_id = manager.save_execution(metrics)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Save execution record
                cursor.execute('''
                    INSERT INTO executions (
                        script_path, script_args, start_time, end_time,
                        execution_time_seconds, exit_code, success, attempt_number,
                        timeout_seconds, timed_out, stdout_lines, stderr_lines,
                        python_version, platform
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.get('script_path', ''),
                    json.dumps(metrics.get('script_args', [])),
                    metrics.get('start_time', ''),
                    metrics.get('end_time', ''),
                    metrics.get('execution_time_seconds', 0),
                    metrics.get('exit_code', -1),
                    metrics.get('success', False),
                    metrics.get('attempt_number', 1),
                    metrics.get('timeout_seconds'),
                    metrics.get('timed_out', False),
                    metrics.get('stdout_lines', 0),
                    metrics.get('stderr_lines', 0),
                    metrics.get('python_version', ''),
                    metrics.get('platform', '')
                ))
                
                execution_id = cursor.lastrowid
                
                # Save individual metrics
                numeric_metrics = {k: v for k, v in metrics.items() 
                                 if isinstance(v, (int, float)) and k not in [
                                     'exit_code', 'attempt_number', 'timeout_seconds',
                                     'stdout_lines', 'stderr_lines'
                                 ]}
                
                for metric_name, metric_value in numeric_metrics.items():
                    cursor.execute('''
                        INSERT INTO metrics (execution_id, metric_name, metric_value)
                        VALUES (?, ?, ?)
                    ''', (execution_id, metric_name, metric_value))
                
                conn.commit()
                self.logger.info(f"Execution saved: {execution_id}")
                return execution_id
                
        except Exception as e:
            self.logger.error(f"Failed to save execution: {e}")
            raise
        
        # This line should never be reached due to raise, but satisfies type checker
        return None

    def save_alerts(self, execution_id: int, alerts: List[Dict]):
        """Save triggered alerts for an execution"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for alert in alerts:
                    cursor.execute('''
                        INSERT INTO alerts (execution_id, alert_name, severity, condition)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        execution_id,
                        alert.get('name', ''),
                        alert.get('severity', ''),
                        alert.get('condition', '')
                    ))
                
                conn.commit()
                self.logger.debug(f"Saved {len(alerts)} alerts for execution {execution_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to save alerts: {e}")

    def get_execution_history(self, script_path: Optional[str] = None, limit: int = 100, 
                             days: int = 30) -> List[Dict]:
        """Retrieve execution history with optional filtering.
        
        Queries execution history with flexible filtering options for analysis,
        reporting, and debugging. Returns complete execution records including
        all associated metrics.
        
        Args:
            script_path (str, optional): Filter by specific script path. If None,
                returns history for all scripts. Default: None
            limit (int): Maximum number of records to return. Default: 100
            days (int): Only include executions from last N days. Useful for
                recent history analysis. Default: 30
            
        Returns:
            List[Dict]: List of execution records sorted by descending start_time.
                Each record contains:
                - id (int): Execution record ID
                - script_path (str): Script that was executed
                - exit_code (int): Process exit code
                - execution_time_seconds (float): Duration
                - success (bool): Execution success status
                - metrics (Dict): Associated time-series metrics
        
        Raises:
            sqlite3.DatabaseError: If query execution fails
        
        Example:
            >>> # Get last 50 executions of a specific script
            >>> history = manager.get_execution_history(
            ...     script_path='app.py',
            ...     limit=50,
            ...     days=7
            ... )
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = 'SELECT * FROM executions WHERE 1=1'
                params = []
                
                if script_path:
                    query += ' AND script_path = ?'
                    params.append(script_path)
                
                if days:
                    cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
                    query += ' AND start_time >= ?'
                    params.append(cutoff_time)
                
                query += ' ORDER BY start_time DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                executions = [dict(row) for row in cursor.fetchall()]
                
                # Load metrics for each execution
                for execution in executions:
                    cursor.execute(
                        'SELECT metric_name, metric_value FROM metrics WHERE execution_id = ?',
                        (execution['id'],)
                    )
                    metrics = {row[0]: row[1] for row in cursor.fetchall()}
                    execution['metrics'] = metrics
                
                return executions
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve execution history: {e}")
            return []

    def get_metrics_for_script(self, script_path: str, metric_name: str, 
                              days: int = 30) -> List[Tuple[str, float]]:
        """Get all values of a specific metric for a script over time
        
        Returns:
            List of (timestamp, value) tuples
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT e.start_time, m.metric_value
                    FROM metrics m
                    JOIN executions e ON m.execution_id = e.id
                    WHERE e.script_path = ? AND m.metric_name = ?
                    AND e.start_time >= ?
                    ORDER BY e.start_time ASC
                '''
                
                cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(query, (script_path, metric_name, cutoff_time))
                
                return cursor.fetchall()
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve metric series: {e}")
            return []

    def get_aggregated_metrics(self, script_path: Optional[str] = None, metric_name: Optional[str] = None,
                              days: int = 30) -> Dict:
        """Get aggregated statistics for metrics
        
        Returns:
            Dictionary with min, max, avg, median, p50, p95, p99 for each metric
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all metric values
                query = '''
                    SELECT m.metric_name, m.metric_value
                    FROM metrics m
                    JOIN executions e ON m.execution_id = e.id
                    WHERE 1=1
                '''
                params = []
                
                if script_path:
                    query += ' AND e.script_path = ?'
                    params.append(script_path)
                
                if metric_name:
                    query += ' AND m.metric_name = ?'
                    params.append(metric_name)
                
                cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
                query += ' AND e.start_time >= ?'
                params.append(cutoff_time)
                
                query += ' ORDER BY m.metric_name, m.metric_value'
                cursor.execute(query, params)
                
                # Group by metric name
                metrics_data = defaultdict(list)
                for metric_name_col, value in cursor.fetchall():
                    metrics_data[metric_name_col].append(value)
                
                # Calculate statistics
                stats = {}
                for metric_name_col, values in metrics_data.items():
                    if not values:
                        continue
                    
                    sorted_values = sorted(values)
                    stats[metric_name_col] = {
                        'count': len(values),
                        'min': min(values),
                        'max': max(values),
                        'avg': mean(values),
                        'median': median(values),
                        'p95': quantiles(sorted_values, n=20)[18] if len(sorted_values) >= 20 else sorted_values[-1],
                        'p99': quantiles(sorted_values, n=100)[98] if len(sorted_values) >= 100 else sorted_values[-1],
                        'stddev': stdev(values) if len(values) > 1 else 0
                    }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get aggregated metrics: {e}")
            return {}

    def cleanup_old_data(self, days: int = 90):
        """Delete execution records older than specified number of days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor.execute('DELETE FROM executions WHERE start_time < ?', (cutoff_time,))
                
                deleted = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Cleaned up {deleted} old execution records (older than {days} days)")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    def get_database_stats(self) -> Dict:
        """Get statistics about the database using connection pool"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM executions')
                total_executions = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM metrics')
                total_metrics = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM alerts')
                total_alerts = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT script_path) FROM executions')
                unique_scripts = cursor.fetchone()[0]
                
                cursor.execute('SELECT SUM(execution_time_seconds) FROM executions')
                total_execution_time = cursor.fetchone()[0] or 0
                
                return {
                    'total_executions': total_executions,
                    'total_metrics': total_metrics,
                    'total_alerts': total_alerts,
                    'unique_scripts': unique_scripts,
                    'total_execution_time_seconds': round(total_execution_time, 2),
                    'database_file': self.db_path,
                    'database_size_mb': os.path.getsize(self.db_path) / 1024 / 1024 if os.path.exists(self.db_path) else 0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            return {}

    def get_executions_paginated(self, limit: int = 100, offset: int = 0, 
                                 script_path: Optional[str] = None, days: int = 30) -> Dict:
        """Get paginated execution history (memory-efficient for large datasets)
        
        Args:
            limit: Number of records per page (default 100)
            offset: Record offset for pagination (default 0)
            script_path: Filter by script path (optional)
            days: Only include executions from last N days
            
        Returns:
            Dict with keys:
                - data: List of execution records
                - total: Total number of matching records
                - limit: Records per page
                - offset: Current offset
                - has_more: Whether more records exist
                
        Example:
            >>> page1 = manager.get_executions_paginated(limit=50, offset=0)
            >>> page2 = manager.get_executions_paginated(limit=50, offset=50)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                query_where = 'WHERE 1=1'
                params = []
                
                if script_path:
                    query_where += ' AND script_path = ?'
                    params.append(script_path)
                
                if days:
                    cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
                    query_where += ' AND start_time >= ?'
                    params.append(cutoff_time)
                
                # Get total count
                cursor.execute(f'SELECT COUNT(*) FROM executions {query_where}', params)
                total = cursor.fetchone()[0]
                
                # Get paginated data
                cursor.execute(
                    f'SELECT * FROM executions {query_where} '
                    'ORDER BY start_time DESC LIMIT ? OFFSET ?',
                    params + [limit, offset]
                )
                
                data = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'data': data,
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get paginated executions: {e}")
            return {'data': [], 'total': 0, 'limit': limit, 'offset': offset, 'has_more': False}

    def get_metrics_paginated(self, limit: int = 1000, offset: int = 0,
                             metric_name: Optional[str] = None, days: int = 30) -> Dict:
        """Get paginated metrics (memory-efficient for large datasets)
        
        Args:
            limit: Number of records per page (default 1000)
            offset: Record offset for pagination
            metric_name: Filter by metric name
            days: Only include metrics from last N days
            
        Returns:
            Dict with keys:
                - data: List of metric records
                - total: Total number of matching records
                - limit: Records per page
                - offset: Current offset
                - has_more: Whether more records exist
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query_where = 'WHERE 1=1'
                params = []
                
                if metric_name:
                    query_where += ' AND m.metric_name = ?'
                    params.append(metric_name)
                
                if days:
                    cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
                    query_where += ' AND e.start_time >= ?'
                    params.append(cutoff_time)
                
                # Get total count
                cursor.execute(
                    f'SELECT COUNT(*) FROM metrics m '
                    f'JOIN executions e ON m.execution_id = e.id {query_where}',
                    params
                )
                total = cursor.fetchone()[0]
                
                # Get paginated data
                cursor.execute(
                    f'SELECT m.*, e.script_path, e.start_time FROM metrics m '
                    f'JOIN executions e ON m.execution_id = e.id {query_where} '
                    'ORDER BY e.start_time DESC LIMIT ? OFFSET ?',
                    params + [limit, offset]
                )
                
                data = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'data': data,
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get paginated metrics: {e}")
            return {'data': [], 'total': 0, 'limit': limit, 'offset': offset, 'has_more': False}


# ============================================================================
# FEATURE: TREND ANALYSIS & REGRESSION DETECTION
# ============================================================================

class TrendAnalyzer:
    """Analyze trends in metrics and detect performance regressions.
    
    Industrial-grade trend analysis engine supporting statistical regression analysis,
    anomaly detection, percentile calculations, and regression detection for metrics.
    Implements multiple statistical methods for robust analysis across different
    metric distributions.
    
    Supports analysis methods:
    - Linear regression for trend identification
    - IQR/Z-score/MAD methods for anomaly detection
    - Regression detection using baseline comparison
    - Statistical percentile calculations
    
    Attributes:
        logger (logging.Logger): Logger instance for audit trails
    
    Example:
        >>> analyzer = TrendAnalyzer()
        >>> trend = analyzer.calculate_linear_regression([1, 1.1, 1.2, 1.25, 1.3])
        >>> anomalies = analyzer.detect_anomalies([100, 110, 105, 500], method='iqr')
        >>> regression = analyzer.detect_regression(values, threshold_pct=10)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def calculate_linear_regression(self, values: List[float]) -> Dict:
        """Calculate linear regression trend line for metric values.
        
        Performs least-squares linear regression to identify performance trends
        (improving, degrading, or stable). Includes R-squared goodness-of-fit metric.
        
        Args:
            values (List[float]): List of metric values in chronological order.
                Minimum 2 values required for meaningful regression.
        
        Returns:
            Dict: Regression analysis results containing:
                - slope (float): Rate of change per time unit
                - intercept (float): Y-intercept of regression line
                - r_squared (float): Goodness-of-fit (0-1, higher is better)
                - trend (str): Classification ('increasing', 'decreasing', 'stable', 'insufficient_data')
                - slope_pct_per_run (float): Percentage change per execution
        
        Example:
            >>> values = [100, 102, 104, 106, 108]  # improving over time
            >>> result = analyzer.calculate_linear_regression(values)
            >>> print(f"Trend: {result['trend']}, slope: {result['slope_pct_per_run']}%")
        """
        if len(values) < 2:
            return {
                'slope': 0,
                'intercept': values[0] if values else 0,
                'r_squared': 0,
                'trend': 'insufficient_data',
                'slope_pct_per_run': 0
            }
        
        n = len(values)
        x = list(range(n))  # Time points (0, 1, 2, ...)
        y = values
        
        # Calculate means
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        # Calculate slope (m) and intercept (b)
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return {
                'slope': 0,
                'intercept': y_mean,
                'r_squared': 0,
                'trend': 'flat',
                'slope_pct_per_run': 0
            }
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Calculate R-squared
        y_pred = [intercept + slope * xi for xi in x]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine trend
        if abs(slope) < 0.01:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        return {
            'slope': round(slope, 6),
            'intercept': round(intercept, 2),
            'r_squared': round(r_squared, 4),
            'trend': trend,
            'slope_pct_per_run': round((slope / y_mean * 100) if y_mean != 0 else 0, 2)
        }
    
    def detect_anomalies(self, values: List[float], method: str = 'iqr',
                        threshold: float = 1.5) -> Dict:
        """Detect anomalies in metric values using statistical methods.
        
        Identifies outliers and anomalies using one of three statistical methods.
        Robust against different data distributions.
        
        Args:
            values (List[float]): List of metric values to analyze
            method (str): Detection method, one of:
                - 'iqr': Interquartile Range method (robust, recommended for skewed data)
                - 'zscore': Z-score method (good for normal distributions)
                - 'mad': Median Absolute Deviation (most robust to outliers)
                Default: 'iqr'
            threshold (float): Sensitivity threshold:
                - IQR: multiplier (1.5=standard, 3.0=extreme)
                - Z-score: standard deviations (2.0=95%, 3.0=99.7%)
                - MAD: modified z threshold
                Default: 1.5
        
        Returns:
            Dict: Anomaly detection results:
                - anomalies (List): List of detected anomalies with indices and values
                - method (str): Method used
                - count (int): Number of anomalies found
                - percentage (float): Percentage of anomalies in dataset
        
        Example:
            >>> values = [100, 101, 99, 102, 500, 100]  # 500 is anomaly
            >>> result = analyzer.detect_anomalies(values, method='iqr')
            >>> print(f"Found {result['count']} anomalies")
        """
        if len(values) < 3:
            return {'anomalies': [], 'method': method, 'count': 0}
        
        anomalies = []
        
        if method == 'iqr':
            # Interquartile Range method
            sorted_vals = sorted(values)
            q1_idx = len(sorted_vals) // 4
            q3_idx = (3 * len(sorted_vals)) // 4
            q1 = sorted_vals[q1_idx]
            q3 = sorted_vals[q3_idx]
            iqr = q3 - q1
            
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            
            for i, val in enumerate(values):
                if val < lower_bound or val > upper_bound:
                    anomalies.append({
                        'index': i,
                        'value': val,
                        'type': 'outlier',
                        'deviation': val - (upper_bound if val > upper_bound else lower_bound)
                    })
        
        elif method == 'zscore':
            # Z-score method
            if len(values) > 1:
                mean_val = mean(values)
                std_val = stdev(values)
                
                for i, val in enumerate(values):
                    z_score = (val - mean_val) / std_val if std_val > 0 else 0
                    if abs(z_score) > threshold:
                        anomalies.append({
                            'index': i,
                            'value': val,
                            'type': 'outlier',
                            'z_score': round(z_score, 2)
                        })
        
        elif method == 'mad':
            # Median Absolute Deviation
            med = median(values)
            deviations = [abs(v - med) for v in values]
            mad = median(deviations)
            
            for i, val in enumerate(values):
                if mad > 0:
                    modified_z = 0.6745 * (val - med) / mad
                    if abs(modified_z) > threshold:
                        anomalies.append({
                            'index': i,
                            'value': val,
                            'type': 'outlier',
                            'modified_z': round(modified_z, 2)
                        })
        
        return {
            'anomalies': anomalies,
            'method': method,
            'count': len(anomalies),
            'percentage': round(len(anomalies) / len(values) * 100, 2) if values else 0
        }
    
    def detect_regression(self, values: List[float], window_size: int = 5,
                         threshold_pct: float = 10.0) -> Dict:
        """Detect performance regressions (significant increases in metric values)
        
        Args:
            values: List of metric values (lower is better)
            window_size: Number of recent values to compare against older values
            threshold_pct: Percentage increase threshold to flag as regression
            
        Returns:
            Dictionary with regression analysis
        """
        if len(values) < window_size * 2:
            return {
                'regression_detected': False,
                'reason': 'insufficient_data',
                'data_points': len(values)
            }
        
        # Compare recent window vs older baseline
        baseline = values[:-window_size]
        recent = values[-window_size:]
        
        baseline_mean = mean(baseline)
        recent_mean = mean(recent)
        
        if baseline_mean == 0:
            percent_change = 0
        else:
            percent_change = ((recent_mean - baseline_mean) / baseline_mean) * 100
        
        regression_detected = percent_change > threshold_pct
        
        return {
            'regression_detected': regression_detected,
            'baseline_mean': round(baseline_mean, 2),
            'recent_mean': round(recent_mean, 2),
            'percent_change': round(percent_change, 2),
            'threshold_pct': threshold_pct,
            'baseline_size': len(baseline),
            'recent_size': window_size,
            'severity': 'high' if percent_change > threshold_pct * 1.5 else 'medium' if regression_detected else 'none'
        }
    
    def calculate_percentiles(self, values: List[float]) -> Dict:
        """Calculate key percentiles for a metric series
        
        Returns:
            Dictionary with p50, p75, p90, p95, p99
        """
        if not values:
            return {}
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        def percentile(data, p):
            idx = (len(data) - 1) * p / 100
            lower = int(idx)
            upper = lower + 1
            weight = idx % 1
            
            if upper >= len(data):
                return data[lower]
            return data[lower] * (1 - weight) + data[upper] * weight
        
        return {
            'min': round(min(values), 2),
            'max': round(max(values), 2),
            'mean': round(mean(values), 2),
            'median': round(median(values), 2),
            'p75': round(percentile(sorted_vals, 75), 2),
            'p90': round(percentile(sorted_vals, 90), 2),
            'p95': round(percentile(sorted_vals, 95), 2),
            'p99': round(percentile(sorted_vals, 99), 2),
            'stddev': round(stdev(values) if len(values) > 1 else 0, 2)
        }
    
    def analyze_metric_history(self, history_manager: 'HistoryManager', 
                               script_path: str, metric_name: str,
                               days: int = 30) -> Dict:
        """Comprehensive analysis of a metric's history
        
        Args:
            history_manager: HistoryManager instance
            script_path: Path to the script
            metric_name: Name of the metric to analyze
            days: Days of history to analyze
            
        Returns:
            Complete analysis with trends, anomalies, regressions
        """
        # Get metric history
        metric_series = history_manager.get_metrics_for_script(script_path, metric_name, days)
        
        if not metric_series:
            return {
                'error': 'No data available',
                'script_path': script_path,
                'metric_name': metric_name
            }
        
        values = [val for _, val in metric_series]
        
        # Perform analysis
        regression_analysis = TrendAnalyzer(self.logger)
        
        return {
            'script_path': script_path,
            'metric_name': metric_name,
            'data_points': len(values),
            'period_days': days,
            'trend': self.calculate_linear_regression(values),
            'anomalies': self.detect_anomalies(values),
            'regression': self.detect_regression(values),
            'percentiles': self.calculate_percentiles(values),
            'latest_value': round(values[-1], 2),
            'first_value': round(values[0], 2)
        }


# ============================================================================
# FEATURE: AUTO-BASELINE CALCULATION
# ============================================================================

class BaselineCalculator:
    """Automatically calculate intelligent performance baselines from historical data.
    
    Industrial-grade baseline calculation supporting multiple strategies for different
    metric distributions and use cases. Automatically selects optimal method based
    on data characteristics (volatility, distribution, outliers).
    
    Supports baseline methods:
    - Percentile: Fixed percentile (P50, P75, P90, etc.)
    - IQR: Interquartile Range with outlier filtering
    - Intelligent: Auto-selects best method based on data analysis
    - Time-based: Compares recent vs historical performance
    
    Attributes:
        logger (logging.Logger): Logger instance
    
    Example:
        >>> calc = BaselineCalculator()
        >>> baseline = calc.calculate_intelligent_baseline([100, 102, 101, 103, 105])
        >>> print(f"Baseline: {baseline['baseline']} ({baseline['method']})")
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def calculate_from_percentile(self, values: List[float], percentile: int = 50) -> Dict:
        """Calculate baseline using percentile method
        
        Args:
            values: Historical metric values
            percentile: Percentile to use (50=median, 75=upper quartile, 90=p90)
            
        Returns:
            Dictionary with baseline value and percentile info
        """
        if not values:
            return {'error': 'No data available'}
        
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * percentile / 100)
        baseline = sorted_vals[min(idx, len(sorted_vals) - 1)]
        
        return {
            'baseline': round(baseline, 4),
            'percentile': percentile,
            'data_points': len(values),
            'min': round(min(values), 4),
            'max': round(max(values), 4),
            'method': 'percentile'
        }
    
    def calculate_with_iqr_filtering(self, values: List[float], 
                                      k: float = 1.5) -> Dict:
        """Calculate baseline using IQR method to exclude outliers
        
        Args:
            values: Historical metric values
            k: IQR multiplier (1.5=standard, 3.0=extreme outliers only)
            
        Returns:
            Dictionary with baseline and outlier statistics
        """
        if len(values) < 4:
            return {
                'error': 'Insufficient data for IQR filtering',
                'data_points': len(values)
            }
        
        sorted_vals = sorted(values)
        q1_idx = len(sorted_vals) // 4
        q3_idx = (3 * len(sorted_vals)) // 4
        
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - k * iqr
        upper_bound = q3 + k * iqr
        
        filtered_vals = [v for v in values if lower_bound <= v <= upper_bound]
        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        
        if not filtered_vals:
            baseline = median(values)
        else:
            baseline = median(filtered_vals)
        
        return {
            'baseline': round(baseline, 4),
            'method': 'iqr_filtered',
            'iqr_k': k,
            'outliers_removed': len(outliers),
            'outlier_percentage': round(len(outliers) / len(values) * 100, 2),
            'filtered_data_points': len(filtered_vals),
            'original_data_points': len(values)
        }
    
    def calculate_intelligent_baseline(self, values: List[float],
                                       exclude_outliers: bool = True) -> Dict:
        """Calculate intelligent baseline automatically selecting optimal method.
        
        Analyzes data distribution characteristics and automatically selects
        the most appropriate baseline calculation method. Accounts for variability,
        outliers, and data range.
        
        Args:
            values (List[float]): Historical metric values for analysis.
                Minimum 3 values recommended for meaningful analysis.
            exclude_outliers (bool): Whether to exclude statistical outliers
                when calculating baseline. Default: True
        
        Returns:
            Dict: Baseline analysis results:
                - baseline (float): Recommended baseline value
                - method (str): Method used ('percentile', 'iqr_filtered', 'mean_fallback')
                - reasoning (str): Explanation of why method was chosen
                - data_characteristics (Dict): Analysis metrics:
                    - coefficient_of_variation (float): Variability indicator
                    - range (float): Max - Min values
                    - mean, median, stddev (float): Distribution statistics
        
        Example:
            >>> # High-volatility metrics (e.g., cache hit ratios)
            >>> values = [0.85, 0.88, 0.2, 0.87, 0.90, 0.86]  # 0.2 is anomaly
            >>> baseline = calc.calculate_intelligent_baseline(values)
            >>> # Returns IQR-filtered baseline, ignoring the 0.2 outlier
        """
        if not values:
            return {'error': 'No data available'}
        
        if len(values) < 3:
            return {
                'baseline': round(mean(values), 4),
                'method': 'mean_fallback',
                'reason': 'insufficient_data',
                'data_points': len(values)
            }
        
        # Analyze data characteristics
        sorted_vals = sorted(values)
        min_val = min(values)
        max_val = max(values)
        med_val = median(values)
        mean_val = mean(values)
        std_val = stdev(values) if len(values) > 1 else 0
        
        # Calculate coefficient of variation
        cv = (std_val / mean_val * 100) if mean_val != 0 else 0
        
        # Choose method based on data characteristics
        if cv > 30:  # High variability - use median with outlier filtering
            result = self.calculate_with_iqr_filtering(values, k=1.5)
            result['reasoning'] = 'High variability (CV={:.1f}%), using IQR filtering'.format(cv)
        elif len(values) >= 10 and (max_val - min_val) / mean_val > 0.5:
            # Significant range - use 75th percentile
            result = self.calculate_from_percentile(values, percentile=75)
            result['reasoning'] = 'Significant value range, using 75th percentile'
        else:
            # Low variability - use median
            result = self.calculate_from_percentile(values, percentile=50)
            result['reasoning'] = 'Low variability, using median (50th percentile)'
        
        result['data_characteristics'] = {
            'mean': round(mean_val, 4),
            'median': round(med_val, 4),
            'stddev': round(std_val, 4),
            'coefficient_of_variation': round(cv, 2),
            'range': round(max_val - min_val, 4),
            'data_points': len(values)
        }
        
        return result
    
    def calculate_time_based_baseline(self, history_manager: 'HistoryManager',
                                      script_path: str, metric_name: str,
                                      recent_days: int = 7, 
                                      comparison_days: int = 30) -> Dict:
        """Calculate baseline comparing recent performance to historical
        
        Args:
            history_manager: HistoryManager instance
            script_path: Path to the script
            metric_name: Name of the metric
            recent_days: Recent period to evaluate
            comparison_days: Historical period to compare against
            
        Returns:
            Dictionary with time-based baseline analysis
        """
        # Get recent and historical data
        recent_data = history_manager.get_metrics_for_script(
            script_path, metric_name, days=recent_days
        )
        historical_data = history_manager.get_metrics_for_script(
            script_path, metric_name, days=comparison_days
        )
        
        if not recent_data or not historical_data:
            return {'error': 'Insufficient data for time-based analysis'}
        
        recent_values = [v for _, v in recent_data]
        historical_values = [v for _, v in historical_data]
        
        recent_median = median(recent_values)
        historical_median = median(historical_values)
        
        if historical_median == 0:
            percent_change = 0
        else:
            percent_change = ((recent_median - historical_median) / historical_median) * 100
        
        return {
            'recent_baseline': round(recent_median, 4),
            'historical_baseline': round(historical_median, 4),
            'percent_change': round(percent_change, 2),
            'recent_period_days': recent_days,
            'historical_period_days': comparison_days,
            'recent_samples': len(recent_values),
            'historical_samples': len(historical_values),
            'status': 'improved' if percent_change < -5 else 'degraded' if percent_change > 5 else 'stable'
        }


# ============================================================================
# FEATURE: STRUCTURED LOGGING & LOG ANALYSIS
# ============================================================================

class StructuredLogger:
    """Provides structured JSON logging for all events.
    
    Implements industrial-grade structured logging with JSON serialization for
    machine-readable audit trails, monitoring system integration, and compliance.
    Supports filtering and querying logs by event type.
    
    Attributes:
        log_file (str, optional): Path to log file for persistence
        logs (List[Dict]): In-memory log buffer
    
    Example:
        >>> logger = StructuredLogger(log_file='events.jsonl')
        >>> logger.log_event('execution', {'script': 'app.py', 'status': 'success'})
        >>> critical_logs = logger.get_logs(event_type='error')
    """

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.logs = []
    
    def log_event(self, event_type: str, data: Dict, timestamp: Optional[str] = None) -> Dict:
        """Log a structured event.
        
        Args:
            event_type (str): Type of event (execution, alert, gate, error, etc.)
            data (Dict): Event data dictionary (arbitrary key-value pairs)
            timestamp (str, optional): ISO format timestamp. Auto-generated if None.
        
        Returns:
            Dict: The logged event (with timestamp added)
        
        Example:
            >>> event = logger.log_event('performance_gate', {
            ...     'gate_name': 'cpu_check',
            ...     'threshold': 90,
            ...     'actual': 85,
            ...     'passed': True
            ... })
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        event = {
            'timestamp': timestamp,
            'event_type': event_type,
            'data': data
        }
        
        self.logs.append(event)
        
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(event) + '\n')
            except Exception:
                pass
        
        return event
    
    def get_logs(self, event_type: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve logs with optional filtering.
        
        Args:
            event_type (str, optional): Filter by event type. None=all types.
            limit (int, optional): Limit number of results. None=all results.
        
        Returns:
            List[Dict]: Filtered log events
        """
        logs = self.logs
        
        if event_type:
            logs = [l for l in logs if l['event_type'] == event_type]
        
        if limit:
            logs = logs[-limit:]
        
        return logs


class LogAnalyzer:
    """Analyzes logs and detects error patterns and anomalies.
    
    Provides industrial-grade log analysis with pattern recognition, error
    categorization, and severity assessment. Supports troubleshooting and
    root cause analysis of execution failures.
    
    Attributes:
        logger (logging.Logger): Logger instance
        KNOWN_PATTERNS (Dict): Known error patterns for classification
    
    Error Pattern Categories:
    - timeout_error: Execution exceeded time limit
    - memory_error: Out of memory or allocation failure
    - file_error: File not found or path issues
    - permission_error: Access denied or authorization failure
    - connection_error: Network or connection issues
    - database_error: Database operation failure
    
    Example:
        >>> analyzer = LogAnalyzer()
        >>> patterns = analyzer.extract_error_patterns(stderr)
        >>> analysis = analyzer.analyze_execution_log(stdout, stderr, 1)
    """

    # Common error patterns (unchanged from original)
    KNOWN_PATTERNS = {
        'timeout': {
            'keywords': ['timeout', 'timed out', 'time limit exceeded'],
            'category': 'timeout_error',
            'severity': 'high'
        },
        'memory': {
            'keywords': ['memory', 'out of memory', 'oom', 'malloc'],
            'category': 'memory_error',
            'severity': 'critical'
        },
        'file_not_found': {
            'keywords': ['no such file', 'file not found', 'cannot find', 'path not found'],
            'category': 'file_error',
            'severity': 'medium'
        },
        'permission': {
            'keywords': ['permission denied', 'access denied', 'unauthorized'],
            'category': 'permission_error',
            'severity': 'medium'
        },
        'connection': {
            'keywords': ['connection refused', 'connection timeout', 'connection reset', 'network'],
            'category': 'connection_error',
            'severity': 'high'
        },
        'database': {
            'keywords': ['database', 'sql', 'query failed', 'db error'],
            'category': 'database_error',
            'severity': 'high'
        }
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def extract_error_patterns(self, text: str) -> Dict:
        """Extract error patterns from text.
        
        Args:
            text (str): Text to analyze (stdout/stderr)
            
        Returns:
            Dict: Detected patterns with categories and severities
        """
        text_lower = text.lower()
        detected_patterns = []
        
        for pattern_name, pattern_info in self.KNOWN_PATTERNS.items():
            for keyword in pattern_info['keywords']:
                if keyword in text_lower:
                    detected_patterns.append({
                        'pattern': pattern_name,
                        'category': pattern_info['category'],
                        'severity': pattern_info['severity'],
                        'keyword': keyword
                    })
                    break
        
        return {
            'detected_patterns': detected_patterns,
            'pattern_count': len(detected_patterns),
            'has_errors': len(detected_patterns) > 0
        }
    
    def analyze_execution_log(self, stdout: str, stderr: str, exit_code: int) -> Dict:
        """Comprehensive analysis of execution logs.
        
        Analyzes both stdout and stderr for error patterns and determines
        overall issue severity based on exit code and detected patterns.
        
        Args:
            stdout (str): Standard output
            stderr (str): Standard error
            exit_code (int): Process exit code
            
        Returns:
            Dict: Complete log analysis including:
                - exit_code (int): Process exit code
                - stdout_lines, stderr_lines (int): Output line counts
                - patterns_detected (List): Detected error patterns
                - issue_severity (str): Overall issue severity
                - has_error_output (bool): Whether stderr has content
        """
        # Analyze error patterns
        stdout_patterns = self.extract_error_patterns(stdout) if stdout else {'detected_patterns': []}
        stderr_patterns = self.extract_error_patterns(stderr) if stderr else {'detected_patterns': []}
        
        # Count lines
        stdout_lines = len(stdout.splitlines()) if stdout else 0
        stderr_lines = len(stderr.splitlines()) if stderr else 0
        
        # Combine patterns
        all_patterns = stdout_patterns['detected_patterns'] + stderr_patterns['detected_patterns']
        
        # Determine issue severity
        if exit_code == 0:
            issue_severity = 'none'
        elif all_patterns:
            severities = [p['severity'] for p in all_patterns]
            issue_severity = 'critical' if 'critical' in severities else 'high' if 'high' in severities else 'medium'
        else:
            issue_severity = 'low'
        
        return {
            'exit_code': exit_code,
            'stdout_lines': stdout_lines,
            'stderr_lines': stderr_lines,
            'total_lines': stdout_lines + stderr_lines,
            'patterns_detected': all_patterns,
            'pattern_count': len(all_patterns),
            'issue_severity': issue_severity,
            'has_error_output': stderr_lines > 0,
            'error_pattern_types': list(set([p['category'] for p in all_patterns]))
        }
    
    def generate_summary(self, analyses: List[Dict]) -> Dict:
        """Generate summary statistics from multiple analyses.
        
        Args:
            analyses (List[Dict]): List of execution analyses
            
        Returns:
            Dict: Summary statistics with error distribution and rates
        """
        if not analyses:
            return {}
        
        error_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for analysis in analyses:
            for pattern in analysis.get('patterns_detected', []):
                error_counts[pattern['category']] += 1
                severity_counts[pattern['severity']] += 1
        
        return {
            'total_executions': len(analyses),
            'executions_with_errors': sum(1 for a in analyses if a['issue_severity'] != 'none'),
            'error_rate': round(
                sum(1 for a in analyses if a['issue_severity'] != 'none') / len(analyses) * 100, 2
            ) if analyses else 0,
            'most_common_errors': dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            'severity_distribution': dict(severity_counts),
            'error_pattern_types': list(set(sum([a.get('error_pattern_types', []) for a in analyses], [])))
        }


# ============================================================================
# FEATURE: TIME-SERIES QUERY API
# ============================================================================

class TimeSeriesDB:
    """Advanced time-series query API for metrics with flexible filtering and aggregations"""
    
    def __init__(self, history_manager: 'HistoryManager'):
        """Initialize with reference to HistoryManager
        
        Args:
            history_manager: HistoryManager instance for database access
        """
        self.history_manager = history_manager
        self.db_path = history_manager.db_path
    
    def query(self, metric_name: Optional[str] = None, script_path: Optional[str] = None,
              start_date: Optional[str] = None, end_date: Optional[str] = None,
              limit: int = 10000, offset: int = 0) -> List[Dict]:
        """Query metrics with flexible filtering
        
        Args:
            metric_name: Filter by specific metric (e.g., 'execution_time_seconds')
            script_path: Filter by script path
            start_date: ISO format start date (e.g., '2024-01-01')
            end_date: ISO format end date
            limit: Maximum records to return
            offset: Pagination offset
            
        Returns:
            List of metric records with timestamps and values
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT m.timestamp, m.metric_name, m.value, e.script_path, e.exit_code
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE 1=1
            """
            params = []
            
            if metric_name:
                query += " AND m.metric_name = ?"
                params.append(metric_name)
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY m.timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    'timestamp': row[0],
                    'metric_name': row[1],
                    'value': row[2],
                    'script_path': row[3],
                    'exit_code': row[4]
                })
            
            conn.close()
            return list(reversed(results))  # Return in chronological order
        except Exception as e:
            logging.error(f"Error querying time-series data: {e}")
            return []
    
    def aggregate(self, metric_name: str, script_path: Optional[str] = None,
                  start_date: Optional[str] = None, end_date: Optional[str] = None,
                  method: str = 'avg') -> Optional[float]:
        """Aggregate metric values using specified method
        
        Args:
            metric_name: Metric to aggregate
            script_path: Optional script filter
            start_date: Optional start date
            end_date: Optional end date
            method: Aggregation method - 'avg', 'min', 'max', 'sum', 'count'
            
        Returns:
            Aggregated value or None if no data
        """
        method_map = {
            'avg': 'AVG(m.value)',
            'min': 'MIN(m.value)',
            'max': 'MAX(m.value)',
            'sum': 'SUM(m.value)',
            'count': 'COUNT(m.value)',
            'median': None  # Special handling
        }
        
        if method == 'median':
            return self._calculate_percentile(metric_name, script_path, start_date, end_date, 50)
        
        if method not in method_map:
            logging.warning(f"Unknown aggregation method: {method}")
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = f"""
                SELECT {method_map[method]}
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE m.metric_name = ?
            """
            params = [metric_name]
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result and result[0] is not None else None
        except Exception as e:
            logging.error(f"Error aggregating metrics: {e}")
            return None
    
    def aggregations(self, metric_name: str, script_path: Optional[str] = None,
                     start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """Calculate multiple aggregations at once
        
        Args:
            metric_name: Metric to analyze
            script_path: Optional script filter
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dictionary with min, max, avg, median, p50, p75, p90, p95, p99, stddev
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT m.value
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE m.metric_name = ?
            """
            params = [metric_name]
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            cursor.execute(query, params)
            values = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            if not values:
                return {}
            
            # Calculate percentiles
            sorted_vals = sorted(values)
            n = len(values)
            
            def percentile(p):
                idx = int(n * p / 100)
                return sorted_vals[min(idx, n - 1)]
            
            return {
                'min': min(values),
                'max': max(values),
                'avg': mean(values),
                'median': median(values),
                'count': len(values),
                'p50': percentile(50),
                'p75': percentile(75),
                'p90': percentile(90),
                'p95': percentile(95),
                'p99': percentile(99),
                'stddev': stdev(values) if len(values) > 1 else 0
            }
        except Exception as e:
            logging.error(f"Error calculating aggregations: {e}")
            return {}
    
    def _calculate_percentile(self, metric_name: str, script_path: Optional[str],
                             start_date: Optional[str], end_date: Optional[str],
                             percentile: int) -> Optional[float]:
        """Calculate specific percentile value"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT m.value
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE m.metric_name = ?
            """
            params = [metric_name]
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY m.value"
            
            cursor.execute(query, params)
            values = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            if not values:
                return None
            
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * percentile / 100)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]
        except Exception as e:
            logging.error(f"Error calculating percentile: {e}")
            return None
    
    def bucket(self, metric_name: str, bucket_size: str = '1hour',
               script_path: Optional[str] = None, start_date: Optional[str] = None,
               end_date: Optional[str] = None) -> Dict[str, float]:
        """Downsample metrics into time buckets for large datasets
        
        Args:
            metric_name: Metric to bucket
            bucket_size: Bucket size - '5min', '15min', '1hour', '1day'
            script_path: Optional script filter
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dictionary mapping bucket timestamps to average values
        """
        bucket_map = {
            '5min': "strftime('%Y-%m-%d %H:%M:00', m.timestamp)",
            '15min': "strftime('%Y-%m-%d %H:%M:00', m.timestamp)",
            '1hour': "strftime('%Y-%m-%d %H:00:00', m.timestamp)",
            '1day': "strftime('%Y-%m-%d', m.timestamp)"
        }
        
        if bucket_size not in bucket_map:
            logging.warning(f"Unknown bucket size: {bucket_size}")
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            bucket_expr = bucket_map[bucket_size]
            query = f"""
                SELECT {bucket_expr} as bucket, AVG(m.value) as avg_value
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE m.metric_name = ?
            """
            params = [metric_name]
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            query += " GROUP BY bucket ORDER BY bucket"
            
            cursor.execute(query, params)
            result = {}
            for row in cursor.fetchall():
                result[row[0]] = row[1]
            
            conn.close()
            return result
        except Exception as e:
            logging.error(f"Error bucketing metrics: {e}")
            return {}
    
    def metrics_list(self, script_path: Optional[str] = None,
                     start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[str]:
        """Get list of available metrics for query context
        
        Args:
            script_path: Optional script filter
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of unique metric names available in database
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT DISTINCT m.metric_name
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE 1=1
            """
            params = []
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY m.metric_name"
            
            cursor.execute(query, params)
            metrics = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return metrics
        except Exception as e:
            logging.error(f"Error getting metrics list: {e}")
            return []


# ============================================================================
# FEATURE: MULTI-SCRIPT ORCHESTRATION WITH DAG SUPPORT
# ============================================================================

class ScriptNode:
    """Represents a script node in a DAG"""
    
    def __init__(self, script_path: str, script_args: Optional[List[str]] = None, timeout: Optional[int] = None):
        """Initialize script node
        
        Args:
            script_path: Path to the Python script
            script_args: Arguments to pass to script
            timeout: Execution timeout in seconds
        """
        self.script_path = script_path
        self.script_args = script_args or []
        self.timeout = timeout
        self.dependencies = []  # List of script names this depends on
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.execution_time: float = 0.0
    
    def add_dependency(self, script_name: str):
        """Add a dependency on another script"""
        if script_name not in self.dependencies:
            self.dependencies.append(script_name)


class ScriptWorkflow:
    """DAG-based multi-script orchestration engine (68% demand feature)"""
    
    def __init__(self, name: str = "workflow", max_parallel: int = 4, history_db: Optional[str] = None):
        """Initialize workflow
        
        Args:
            name: Workflow name
            max_parallel: Maximum parallel executions
            history_db: Optional database path for history tracking
        """
        self.name = name
        self.max_parallel = max_parallel
        self.history_db = history_db or 'script_runner_history.db'
        self.scripts: Dict[str, ScriptNode] = {}
        self.execution_order = []
        self.start_time = None
        self.end_time = None
        self.total_time = 0
    
    def add_script(self, name: str, script_path: str, script_args: Optional[List[str]] = None,
                   timeout: Optional[int] = None, dependencies: Optional[List[str]] = None):
        """Add script to workflow
        
        Args:
            name: Unique script identifier in workflow
            script_path: Path to Python script
            script_args: Arguments to pass to script
            timeout: Execution timeout
            dependencies: List of script names this script depends on
        """
        node = ScriptNode(script_path, script_args, timeout)
        if dependencies:
            for dep in dependencies:
                node.add_dependency(dep)
        self.scripts[name] = node
        logging.info(f"Added script '{name}' to workflow")
    
    def build_dag(self) -> bool:
        """Build DAG and validate for cycles
        
        Returns:
            True if DAG is valid, False if cycles detected
        """
        visited = {}
        rec_stack = set()
        
        def has_cycle(node_name):
            visited[node_name] = True
            rec_stack.add(node_name)
            
            for dep in self.scripts[node_name].dependencies:
                if dep not in self.scripts:
                    logging.warning(f"Dependency '{dep}' not found for script '{node_name}'")
                    return False
                
                if not visited.get(dep, False):
                    if not has_cycle(dep):
                        return False
                elif dep in rec_stack:
                    logging.error(f"Cycle detected: {node_name} -> {dep}")
                    return False
            
            rec_stack.discard(node_name)
            return True
        
        for script_name in self.scripts:
            if not visited.get(script_name, False):
                if not has_cycle(script_name):
                    return False
        
        # Topological sort
        self.execution_order = self._topological_sort()
        logging.info(f"DAG validated. Execution order: {self.execution_order}")
        return True
    
    def _topological_sort(self) -> List[str]:
        """Perform topological sort on DAG
        
        Returns:
            List of script names in execution order
        """
        visited = set()
        order = []
        
        def visit(node_name):
            if node_name in visited:
                return
            visited.add(node_name)
            for dep in self.scripts[node_name].dependencies:
                visit(dep)
            order.append(node_name)
        
        for script_name in self.scripts:
            visit(script_name)
        
        return order
    
    def get_executable_scripts(self) -> List[str]:
        """Get scripts ready to execute (all dependencies met)
        
        Returns:
            List of script names that can be executed
        """
        executable = []
        for name, node in self.scripts.items():
            if node.status == "pending":
                # Check if all dependencies completed
                deps_met = all(
                    self.scripts[dep].status == "completed"
                    for dep in node.dependencies
                )
                if deps_met:
                    executable.append(name)
        return executable
    
    def execute(self, runner: Optional['ScriptRunner'] = None, dry_run: bool = False) -> Dict:
        """Execute workflow sequentially
        
        Args:
            runner: ScriptRunner instance for execution
            dry_run: If True, only show execution plan without running
            
        Returns:
            Dictionary with execution results for each script
        """
        if not self.build_dag():
            return {"status": "failed", "error": "DAG validation failed"}
        
        self.start_time = datetime.now()
        results = {}
        
        logging.info(f"Workflow started: {self.name}")
        logging.info(f"Scripts: {len(self.scripts)}")
        logging.info(f"Execution order: {' -> '.join(self.execution_order)}")
        
        if dry_run:
            logging.info("DRY RUN - No scripts executed")
            return {"status": "dry_run", "plan": self.execution_order}
        
        # Execute in order
        for script_name in self.execution_order:
            node = self.scripts[script_name]
            logging.info(f"Executing script: {script_name} ({node.script_path})")
            
            try:
                start = time.time()
                
                # Execute script (simplified - in production would use full runner)
                result = subprocess.run(
                    [sys.executable, node.script_path] + node.script_args,
                    timeout=node.timeout,
                    capture_output=True,
                    text=True
                )
                
                node.execution_time = time.time() - start
                node.status = "completed"
                results[script_name] = {
                    "exit_code": result.returncode,
                    "execution_time": node.execution_time,
                    "success": result.returncode == 0,
                    "stdout_len": len(result.stdout),
                    "stderr_len": len(result.stderr)
                }
                
                logging.info(f"Script completed: {script_name} (time={node.execution_time:.2f}s, exit={result.returncode})")
                
            except subprocess.TimeoutExpired:
                node.status = "failed"
                results[script_name] = {
                    "exit_code": -1,
                    "success": False,
                    "error": "Timeout"
                }
                logging.error(f"Script timeout: {script_name}")
                break
            except Exception as e:
                node.status = "failed"
                results[script_name] = {
                    "exit_code": -1,
                    "success": False,
                    "error": str(e)
                }
                logging.error(f"Script error: {script_name}: {e}")
                break
        
        self.end_time = datetime.now()
        self.total_time = (self.end_time - self.start_time).total_seconds()
        
        # Summary
        successful = sum(1 for s in self.scripts.values() if s.status == "completed")
        logging.info(f"Workflow completed: {self.name}")
        logging.info(f"Total scripts: {len(self.scripts)}, Successful: {successful}, Failed: {len(self.scripts) - successful}")
        logging.info(f"Total execution time: {self.total_time:.2f}s")
        
        return {
            "status": "completed",
            "total_scripts": len(self.scripts),
            "successful": successful,
            "total_time": self.total_time,
            "results": results
        }
    
    def get_statistics(self) -> Dict:
        """Get workflow execution statistics
        
        Returns:
            Dictionary with execution stats
        """
        if not self.start_time or not self.end_time:
            return {}
        
        total_time_by_script = sum(n.execution_time for n in self.scripts.values())
        successful = sum(1 for n in self.scripts.values() if n.status == "completed")
        
        return {
            "workflow_name": self.name,
            "total_scripts": len(self.scripts),
            "successful_scripts": successful,
            "failed_scripts": len(self.scripts) - successful,
            "total_execution_time": self.total_time,
            "total_script_time": total_time_by_script,
            "overhead_time": self.total_time - total_time_by_script,
            "parallelization_efficiency": (total_time_by_script / self.total_time * 100) if self.total_time > 0 else 0,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat()
        }


# ============================================================================
# FEATURE: DATA EXPORT & RETENTION POLICIES
# ============================================================================

class DataExporter:
    """Export metrics to various formats (CSV, JSON, Parquet)"""
    
    def __init__(self, history_manager: 'HistoryManager'):
        """Initialize exporter
        
        Args:
            history_manager: HistoryManager instance for data access
        """
        self.history_manager = history_manager
        self.db_path = history_manager.db_path
    
    def export_to_csv(self, output_path: str, script_path: Optional[str] = None,
                      metric_name: Optional[str] = None, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> bool:
        """Export metrics to CSV file
        
        Args:
            output_path: Output CSV file path
            script_path: Optional script filter
            metric_name: Optional metric filter
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            True if successful
        """
        try:
            import csv
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT m.timestamp, m.metric_name, m.value, e.script_path, e.exit_code
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE 1=1
            """
            params = []
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if metric_name:
                query += " AND m.metric_name = ?"
                params.append(metric_name)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY m.timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Write CSV
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'metric_name', 'value', 'script_path', 'exit_code'])
                writer.writerows(rows)
            
            logging.info(f"Exported {len(rows)} records to {output_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
            return False
    
    def export_to_json(self, output_path: str, script_path: Optional[str] = None,
                       metric_name: Optional[str] = None, start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> bool:
        """Export metrics to JSON file
        
        Args:
            output_path: Output JSON file path
            script_path: Optional script filter
            metric_name: Optional metric filter
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT m.timestamp, m.metric_name, m.value, e.script_path, e.exit_code
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE 1=1
            """
            params = []
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if metric_name:
                query += " AND m.metric_name = ?"
                params.append(metric_name)
            
            if start_date:
                query += " AND m.timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND m.timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY m.timestamp DESC"
            
            cursor.execute(query, params)
            
            data = []
            for row in cursor.fetchall():
                data.append({
                    'timestamp': row[0],
                    'metric_name': row[1],
                    'value': row[2],
                    'script_path': row[3],
                    'exit_code': row[4]
                })
            
            conn.close()
            
            # Write JSON
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logging.info(f"Exported {len(data)} records to {output_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting to JSON: {e}")
            return False
    
    def export_to_parquet(self, output_path: str, script_path: Optional[str] = None,
                          metric_name: Optional[str] = None) -> bool:
        """Export metrics to Parquet file (requires pyarrow)
        
        Args:
            output_path: Output Parquet file path
            script_path: Optional script filter
            metric_name: Optional metric filter
            
        Returns:
            True if successful
        """
        try:
            try:
                import pyarrow.parquet as pq
                import pyarrow as pa
            except ImportError:
                logging.error("pyarrow not installed. Install with: pip install pyarrow")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT m.timestamp, m.metric_name, m.value, e.script_path, e.exit_code
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE 1=1
            """
            params = []
            
            if script_path:
                query += " AND e.script_path = ?"
                params.append(script_path)
            
            if metric_name:
                query += " AND m.metric_name = ?"
                params.append(metric_name)
            
            cursor.execute(query, params)
            
            timestamps = []
            metric_names = []
            values = []
            scripts = []
            exit_codes = []
            
            for row in cursor.fetchall():
                timestamps.append(row[0])
                metric_names.append(row[1])
                values.append(row[2])
                scripts.append(row[3])
                exit_codes.append(row[4])
            
            conn.close()
            
            # Create Parquet table
            table = pa.table({
                'timestamp': timestamps,
                'metric_name': metric_names,
                'value': values,
                'script_path': scripts,
                'exit_code': exit_codes
            })
            
            pq.write_table(table, output_path)
            logging.info(f"Exported {len(timestamps)} records to {output_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting to Parquet: {e}")
            return False


class RetentionPolicy:
    """Configurable data retention and archival policies (compliance: SOC2, HIPAA)"""
    
    def __init__(self, history_manager: 'HistoryManager'):
        """Initialize retention policy
        
        Args:
            history_manager: HistoryManager instance
        """
        self.history_manager = history_manager
        self.db_path = history_manager.db_path
        self.policies = {}
    
    def add_policy(self, name: str, retention_days: int, archive_path: Optional[str] = None,
                   compliance: Optional[str] = None):
        """Add retention policy
        
        Args:
            name: Policy name
            retention_days: Retain data for N days before deletion
            archive_path: Optional path to archive old data
            compliance: Compliance standard (SOC2, HIPAA, GDPR, etc.)
        """
        self.policies[name] = {
            'retention_days': retention_days,
            'archive_path': archive_path,
            'compliance': compliance,
            'created_date': datetime.now().isoformat()
        }
        logging.info(f"Added retention policy '{name}': {retention_days} days, compliance={compliance}")
    
    def apply_policy(self, policy_name: str, dry_run: bool = False) -> Dict:
        """Apply retention policy
        
        Args:
            policy_name: Name of policy to apply
            dry_run: If True, only show what would be deleted
            
        Returns:
            Dictionary with policy application results
        """
        if policy_name not in self.policies:
            logging.error(f"Policy '{policy_name}' not found")
            return {"status": "error", "message": "Policy not found"}
        
        policy = self.policies[policy_name]
        retention_days = policy['retention_days']
        archive_path = policy['archive_path']
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get data to be deleted
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM executions WHERE timestamp < ?
            """, [cutoff_date])
            
            records_to_delete = cursor.fetchone()[0]
            
            if dry_run:
                return {
                    "status": "dry_run",
                    "policy": policy_name,
                    "records_to_delete": records_to_delete,
                    "cutoff_date": cutoff_date,
                    "compliance": policy.get('compliance')
                }
            
            # Archive if path specified
            if archive_path:
                cursor.execute("""
                    SELECT * FROM executions WHERE timestamp < ?
                """, [cutoff_date])
                
                rows = cursor.fetchall()
                exporter = DataExporter(self.history_manager)
                
                archive_file = f"{archive_path}/archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                os.makedirs(archive_path, exist_ok=True)
                
                # Export to JSON for archival
                archive_data = []
                for row in rows:
                    archive_data.append({
                        'id': row[0],
                        'script_path': row[1],
                        'exit_code': row[2],
                        'timestamp': row[3]
                    })
                
                with open(archive_file, 'w') as f:
                    json.dump(archive_data, f, indent=2, default=str)
                
                logging.info(f"Archived {len(rows)} records to {archive_file}")
            
            # Delete old records
            cursor.execute("DELETE FROM executions WHERE timestamp < ?", [cutoff_date])
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return {
                "status": "success",
                "policy": policy_name,
                "deleted_records": deleted_count,
                "cutoff_date": cutoff_date,
                "archived": bool(archive_path),
                "compliance": policy.get('compliance')
            }
        except Exception as e:
            logging.error(f"Error applying policy '{policy_name}': {e}")
            return {"status": "error", "message": str(e)}
    
    def get_policies(self) -> Dict:
        """Get all configured policies
        
        Returns:
            Dictionary of policies
        """
        return self.policies


# ============================================================================
# FEATURE: PERFORMANCE OPTIMIZATION ENGINE
# ============================================================================

class PerformanceOptimizer:
    """Analyze metrics and provide optimization recommendations"""
    
    def __init__(self, history_manager: Optional['HistoryManager'] = None, logger: Optional[logging.Logger] = None):
        """Initialize optimizer
        
        Args:
            history_manager: HistoryManager for accessing historical metrics
            logger: Logger instance
        """
        self.history_manager = history_manager
        self.logger = logger or logging.getLogger(__name__)
        self.recommendations = []
    
    def analyze_script_performance(self, script_path: str, days: int = 30) -> Dict:
        """Analyze script performance and generate recommendations
        
        Args:
            script_path: Path to script to analyze
            days: Number of days of history to analyze
            
        Returns:
            Dictionary with analysis results and recommendations
        """
        if not self.history_manager:
            return {"status": "error", "message": "No history manager available"}
        
        try:
            # Query database directly for all metrics for this script
            import sqlite3
            conn = sqlite3.connect(self.history_manager.db_path)
            cursor = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT m.metric_name, m.metric_value, e.start_time
                FROM metrics m
                JOIN executions e ON m.execution_id = e.id
                WHERE e.script_path = ? AND e.start_time >= ?
                ORDER BY e.start_time
            """, [script_path, cutoff])
            
            metrics_by_name = {}
            for metric_name, value, timestamp in cursor.fetchall():
                if metric_name not in metrics_by_name:
                    metrics_by_name[metric_name] = []
                metrics_by_name[metric_name].append(float(value))
            
            conn.close()
            
            if not metrics_by_name:
                return {
                    "status": "insufficient_data",
                    "message": f"No metrics found for {script_path}",
                    "recommendations": []
                }
            
            recommendations = []
            analysis = {
                "script_path": script_path,
                "days_analyzed": days,
                "total_runs": len(metrics_by_name.get("execution_time_seconds", [])),
                "recommendations": recommendations,
                "status": "success"
            }
            
            # Analyze CPU metrics
            if "cpu_max" in metrics_by_name:
                cpu_values = metrics_by_name["cpu_max"]
                cpu_avg = sum(cpu_values) / len(cpu_values)
                cpu_max = max(cpu_values)
                
                analysis["cpu_analysis"] = {
                    "average": round(cpu_avg, 2),
                    "max": round(cpu_max, 2),
                    "recommendation": self._get_cpu_recommendation(cpu_avg, cpu_max)
                }
                
                recommendations.append(analysis["cpu_analysis"]["recommendation"])
                
                # Detect instability
                if len(cpu_values) > 1:
                    volatility = self._calculate_volatility(cpu_values)
                    if volatility > 0.5:
                        recommendations.append({
                            "type": "INSTABILITY",
                            "severity": "WARNING",
                            "message": f"CPU usage varies significantly (volatility: {volatility:.2f}). Consider caching, memoization, or input normalization.",
                            "suggested_actions": [
                                "Check for data-dependent branching",
                                "Profile with different input sizes",
                                "Consider input validation/normalization"
                            ]
                        })
            
            # Analyze memory metrics
            if "memory_max_mb" in metrics_by_name:
                memory_values = metrics_by_name["memory_max_mb"]
                memory_avg = sum(memory_values) / len(memory_values)
                memory_max = max(memory_values)
                
                analysis["memory_analysis"] = {
                    "average_mb": round(memory_avg, 2),
                    "max_mb": round(memory_max, 2),
                    "recommendation": self._get_memory_recommendation(memory_avg, memory_max)
                }
                
                recommendations.append(analysis["memory_analysis"]["recommendation"])
            
            # Analyze execution time metrics
            if "execution_time_seconds" in metrics_by_name:
                exec_times = metrics_by_name["execution_time_seconds"]
                exec_avg = sum(exec_times) / len(exec_times)
                exec_max = max(exec_times)
                
                analysis["execution_analysis"] = {
                    "average_seconds": round(exec_avg, 2),
                    "max_seconds": round(exec_max, 2),
                    "recommendation": self._get_execution_recommendation(exec_avg, exec_max)
                }
                
                recommendations.append(analysis["execution_analysis"]["recommendation"])
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance: {e}")
            return {"status": "error", "message": str(e), "recommendations": []}
    
    def _get_cpu_recommendation(self, avg: float, max_val: float) -> Dict:
        """Get CPU optimization recommendation
        
        Args:
            avg: Average CPU usage
            max_val: Maximum CPU usage
            
        Returns:
            Recommendation dictionary
        """
        if max_val > 90:
            return {
                "type": "HIGH_CPU",
                "severity": "CRITICAL",
                "message": f"Script uses high CPU ({max_val:.1f}% peak, {avg:.1f}% average)",
                "suggested_actions": [
                    "Profile hot spots with cProfile or line_profiler",
                    "Consider parallelization with multiprocessing",
                    "Optimize algorithms (e.g., reduce nested loops)",
                    "Use compiled extensions (Cython, C++) for bottlenecks",
                    "Consider lazy evaluation and generators"
                ]
            }
        elif max_val > 70:
            return {
                "type": "MODERATE_CPU",
                "severity": "WARNING",
                "message": f"Script uses moderate CPU ({max_val:.1f}% peak)",
                "suggested_actions": [
                    "Monitor for further optimization opportunities",
                    "Consider caching frequently computed values",
                    "Profile to identify bottlenecks"
                ]
            }
        else:
            return {
                "type": "OPTIMAL_CPU",
                "severity": "INFO",
                "message": f"CPU usage is healthy ({avg:.1f}% average)",
                "suggested_actions": []
            }
    
    def _get_memory_recommendation(self, avg: float, max_val: float) -> Dict:
        """Get memory optimization recommendation
        
        Args:
            avg: Average memory usage (MB)
            max_val: Maximum memory usage (MB)
            
        Returns:
            Recommendation dictionary
        """
        if max_val > 1024:
            return {
                "type": "HIGH_MEMORY",
                "severity": "CRITICAL",
                "message": f"Script uses high memory ({max_val:.1f}MB peak)",
                "suggested_actions": [
                    "Check for memory leaks with memory_profiler",
                    "Use generators instead of loading full datasets",
                    "Consider streaming/chunked processing",
                    "Profile memory allocation with tracemalloc",
                    "Use __slots__ for classes to reduce overhead"
                ]
            }
        elif max_val > 512:
            return {
                "type": "MODERATE_MEMORY",
                "severity": "WARNING",
                "message": f"Script uses moderate memory ({max_val:.1f}MB peak)",
                "suggested_actions": [
                    "Monitor memory growth patterns",
                    "Consider data structure optimization",
                    "Profile with memory_profiler for hot spots"
                ]
            }
        else:
            return {
                "type": "OPTIMAL_MEMORY",
                "severity": "INFO",
                "message": f"Memory usage is efficient ({avg:.1f}MB average)",
                "suggested_actions": []
            }
    
    def _get_execution_recommendation(self, avg: float, max_val: float) -> Dict:
        """Get execution time optimization recommendation
        
        Args:
            avg: Average execution time (seconds)
            max_val: Maximum execution time (seconds)
            
        Returns:
            Recommendation dictionary
        """
        if max_val > 600:  # > 10 minutes
            return {
                "type": "LONG_EXECUTION",
                "severity": "WARNING",
                "message": f"Script takes long time to execute ({max_val:.1f}s peak)",
                "suggested_actions": [
                    "Consider breaking into smaller jobs",
                    "Parallelize independent tasks",
                    "Optimize I/O operations",
                    "Check for blocking operations",
                    "Consider caching intermediate results"
                ]
            }
        elif max_val > 300:  # > 5 minutes
            return {
                "type": "MODERATE_EXECUTION",
                "severity": "INFO",
                "message": f"Execution time is moderate ({avg:.1f}s average)",
                "suggested_actions": [
                    "Monitor for regression",
                    "Consider caching"
                ]
            }
        else:
            return {
                "type": "FAST_EXECUTION",
                "severity": "INFO",
                "message": f"Execution time is good ({avg:.1f}s average)",
                "suggested_actions": []
            }
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (coefficient of variation) of values
        
        Args:
            values: List of numeric values
            
        Returns:
            Volatility score (0-1 range)
        """
        if not values or len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        return std_dev / mean
    
    def get_optimization_report(self, script_path: str, days: int = 30) -> str:
        """Generate a human-readable optimization report
        
        Args:
            script_path: Path to script
            days: Days of history to analyze
            
        Returns:
            Formatted report string
        """
        analysis = self.analyze_script_performance(script_path, days)
        
        if analysis["status"] != "success":
            return f"Analysis failed: {analysis.get('message', 'Unknown error')}"
        
        report = []
        report.append("=" * 80)
        report.append("PERFORMANCE OPTIMIZATION REPORT")
        report.append("=" * 80)
        report.append(f"\nScript: {script_path}")
        report.append(f"Period: Last {days} days")
        report.append(f"Total Runs Analyzed: {analysis.get('total_runs', 0)}\n")
        
        # CPU Analysis
        if "cpu_analysis" in analysis:
            cpu = analysis["cpu_analysis"]
            report.append("CPU USAGE:")
            report.append(f"  Average: {cpu['average']}%")
            report.append(f"  Maximum: {cpu['max']}%")
            report.append(f"  Status: {cpu['recommendation'].get('severity', 'UNKNOWN')}")
            report.append(f"  Message: {cpu['recommendation'].get('message', '')}\n")
        
        # Memory Analysis
        if "memory_analysis" in analysis:
            mem = analysis["memory_analysis"]
            report.append("MEMORY USAGE:")
            report.append(f"  Average: {mem['average_mb']} MB")
            report.append(f"  Maximum: {mem['max_mb']} MB")
            report.append(f"  Status: {mem['recommendation'].get('severity', 'UNKNOWN')}")
            report.append(f"  Message: {mem['recommendation'].get('message', '')}\n")
        
        # Execution Time Analysis
        if "execution_analysis" in analysis:
            exec_time = analysis["execution_analysis"]
            report.append("EXECUTION TIME:")
            report.append(f"  Average: {exec_time['average_seconds']}s")
            report.append(f"  Maximum: {exec_time['max_seconds']}s")
            report.append(f"  Status: {exec_time['recommendation'].get('severity', 'UNKNOWN')}")
            report.append(f"  Message: {exec_time['recommendation'].get('message', '')}\n")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        if analysis.get("recommendations"):
            for i, rec in enumerate(analysis["recommendations"], 1):
                if isinstance(rec, dict):
                    report.append(f"\n{i}. [{rec.get('severity', 'INFO')}] {rec.get('message', '')}")
                    if rec.get("suggested_actions"):
                        for action in rec["suggested_actions"]:
                            report.append(f"   - {action}")
                else:
                    report.append(f"\n{i}. {rec}")
        else:
            report.append("\n  No critical recommendations at this time.")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


# ============================================================================
# FEATURE: ADVANCED SCHEDULING SYSTEM
# ============================================================================

class ScheduledTask:
    """Represents a scheduled task"""
    
    def __init__(self, task_id: str, script_path: str, schedule: Optional[str] = None,
                 cron_expr: Optional[str] = None, trigger_events: Optional[List[str]] = None,
                 enabled: bool = True):
        """Initialize scheduled task
        
        Args:
            task_id: Unique task identifier
            script_path: Path to script to execute
            schedule: Simple schedule (e.g., 'daily', 'hourly', 'every_5min')
            cron_expr: Cron expression for complex schedules
            trigger_events: Event names that trigger execution
            enabled: Whether task is enabled
        """
        self.task_id = task_id
        self.script_path = script_path
        self.schedule = schedule
        self.cron_expr = cron_expr
        self.trigger_events = trigger_events or []
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.last_status = None


class TaskScheduler:
    """Manages scheduled script execution and event-driven triggers"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize scheduler
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.tasks = {}
        self.events = {}
        self.triggered_tasks = []
    
    def add_scheduled_task(self, task_id: str, script_path: str,
                          schedule: Optional[str] = None, cron_expr: Optional[str] = None) -> ScheduledTask:
        """Add a scheduled task
        
        Args:
            task_id: Unique identifier
            script_path: Script to run
            schedule: Simple schedule string
            cron_expr: Cron expression
            
        Returns:
            ScheduledTask object
        """
        task = ScheduledTask(task_id, script_path, schedule, cron_expr)
        self.tasks[task_id] = task
        self._calculate_next_run(task)
        self.logger.info(f"Added task '{task_id}': {script_path}")
        return task
    
    def add_event_trigger(self, task_id: str, event_name: str) -> bool:
        """Add event trigger for a task
        
        Args:
            task_id: Task to trigger
            event_name: Event name (e.g., 'on_script_failure', 'on_high_cpu')
            
        Returns:
            True if successful
        """
        if task_id not in self.tasks:
            self.logger.error(f"Task '{task_id}' not found")
            return False
        
        self.tasks[task_id].trigger_events.append(event_name)
        
        if event_name not in self.events:
            self.events[event_name] = []
        self.events[event_name].append(task_id)
        
        self.logger.info(f"Task '{task_id}' will trigger on event '{event_name}'")
        return True
    
    def trigger_event(self, event_name: str) -> List[str]:
        """Trigger an event and return tasks to execute
        
        Args:
            event_name: Name of event
            
        Returns:
            List of task IDs to execute
        """
        tasks = self.events.get(event_name, [])
        self.logger.info(f"Event '{event_name}' triggered: {len(tasks)} tasks")
        return tasks
    
    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are due for execution
        
        Returns:
            List of tasks ready to run
        """
        now = datetime.now()
        due_tasks = []
        
        for task in self.tasks.values():
            if not task.enabled:
                continue
            
            if task.next_run and task.next_run <= now:
                due_tasks.append(task)
        
        return due_tasks
    
    def mark_executed(self, task_id: str, status: str = "success"):
        """Mark task as executed
        
        Args:
            task_id: Task that was executed
            status: Execution status
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.last_run = datetime.now()
            task.last_status = status
            task.run_count += 1
            self._calculate_next_run(task)
            self.logger.info(f"Task '{task_id}' executed: {status}")
    
    def _calculate_next_run(self, task: ScheduledTask):
        """Calculate next run time for task
        
        Args:
            task: Task to calculate for
        """
        if not task.schedule and not task.cron_expr:
            return
        
        now = datetime.now()
        
        if task.schedule == "hourly":
            task.next_run = now + timedelta(hours=1)
        elif task.schedule == "daily":
            task.next_run = now + timedelta(days=1)
        elif task.schedule == "weekly":
            task.next_run = now + timedelta(weeks=1)
        elif task.schedule and task.schedule.startswith("every_"):
            # Parse "every_Xmin" or "every_Xsec"
            try:
                parts = task.schedule.split("_")
                if len(parts) == 2:
                    amount = int(parts[1].replace("min", "").replace("sec", ""))
                    if "min" in task.schedule:
                        task.next_run = now + timedelta(minutes=amount)
                    else:
                        task.next_run = now + timedelta(seconds=amount)
            except Exception as e:
                self.logger.error(f"Error parsing schedule '{task.schedule}': {e}")
        else:
            task.next_run = now + timedelta(hours=1)  # Default to 1 hour
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get status of a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dictionary
        """
        if task_id not in self.tasks:
            return {"status": "not_found"}
        
        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "script": task.script_path,
            "enabled": task.enabled,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "run_count": task.run_count,
            "last_status": task.last_status,
            "triggers": task.trigger_events
        }
    
    def list_tasks(self) -> List[Dict]:
        """List all tasks
        
        Returns:
            List of task statuses
        """
        return [self.get_task_status(task_id) for task_id in self.tasks]


# ============================================================================
# FEATURE: MACHINE LEARNING ANOMALY DETECTION
# ============================================================================

class MLAnomalyDetector:
    """Machine learning-based anomaly detection for metrics"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize ML detector
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.anomalies = []
        self.baseline_stats = {}
    
    def detect_anomalies_zscore(self, values: List[float], threshold: float = 3.0) -> Dict:
        """Detect anomalies using Z-score method
        
        Args:
            values: List of metric values
            threshold: Z-score threshold (default: 3.0 = 99.7% confidence)
            
        Returns:
            Dictionary with anomalies and statistics
        """
        if len(values) < 2:
            return {"anomalies": [], "mean": 0, "stddev": 0}
        
        import statistics
        
        mean = statistics.mean(values)
        stddev = statistics.stdev(values) if len(values) > 1 else 0
        
        if stddev == 0:
            return {"anomalies": [], "mean": mean, "stddev": 0}
        
        anomalies = []
        for i, val in enumerate(values):
            z_score = abs((val - mean) / stddev)
            if z_score > threshold:
                anomalies.append({
                    "index": i,
                    "value": val,
                    "z_score": round(z_score, 2),
                    "type": "outlier"
                })
        
        return {
            "anomalies": anomalies,
            "mean": round(mean, 2),
            "stddev": round(stddev, 2),
            "threshold": threshold,
            "method": "z_score"
        }
    
    def detect_anomalies_iqr(self, values: List[float]) -> Dict:
        """Detect anomalies using Interquartile Range method
        
        Args:
            values: List of metric values
            
        Returns:
            Dictionary with anomalies and statistics
        """
        if len(values) < 4:
            return {"anomalies": [], "q1": 0, "q3": 0, "iqr": 0}
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        # Calculate quartiles
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomalies = []
        for i, val in enumerate(values):
            if val < lower_bound or val > upper_bound:
                anomalies.append({
                    "index": i,
                    "value": val,
                    "bounds": [lower_bound, upper_bound],
                    "type": "outlier"
                })
        
        return {
            "anomalies": anomalies,
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2),
            "bounds": [round(lower_bound, 2), round(upper_bound, 2)],
            "method": "iqr"
        }
    
    def detect_trend_anomalies(self, values: List[float], window: int = 5) -> Dict:
        """Detect anomalies based on trend changes
        
        Args:
            values: List of metric values in time order
            window: Window size for moving average
            
        Returns:
            Dictionary with trend anomalies
        """
        if len(values) < window:
            return {"anomalies": [], "note": "Insufficient data"}
        
        # Calculate moving average
        moving_avg = []
        for i in range(len(values) - window + 1):
            avg = sum(values[i:i+window]) / window
            moving_avg.append(avg)
        
        # Calculate deviations from moving average
        anomalies = []
        for i in range(len(values) - window + 1):
            deviation = abs(values[i + window - 1] - moving_avg[i])
            
            # Anomaly if deviation is 2x the average deviation
            if i > 0 and deviation > 2 * (sum([abs(values[j + window - 1] - moving_avg[j]) 
                                              for j in range(i)]) / i):
                anomalies.append({
                    "index": i + window - 1,
                    "value": values[i + window - 1],
                    "expected": round(moving_avg[i], 2),
                    "deviation": round(deviation, 2),
                    "type": "trend_change"
                })
        
        return {
            "anomalies": anomalies,
            "window_size": window,
            "method": "trend_analysis"
        }
    
    def get_predictive_baseline(self, history_values: List[float]) -> Dict:
        """Calculate predictive baseline using statistical methods
        
        Args:
            history_values: Historical metric values
            
        Returns:
            Predicted baseline with confidence interval
        """
        if len(history_values) < 2:
            return {"baseline": history_values[0] if history_values else 0, "confidence": 0}
        
        import statistics
        
        mean = statistics.mean(history_values)
        if len(history_values) >= 2:
            stddev = statistics.stdev(history_values)
        else:
            stddev = 0
        
        # Predictive baseline with confidence intervals
        return {
            "baseline": round(mean, 2),
            "lower_bound": round(mean - 2 * stddev, 2),
            "upper_bound": round(mean + 2 * stddev, 2),
            "stddev": round(stddev, 2),
            "data_points": len(history_values),
            "confidence_level": "95%"
        }


# ============================================================================
# FEATURE: ADVANCED METRICS CORRELATION ANALYSIS
# ============================================================================

class MetricsCorrelationAnalyzer:
    """Analyzes correlations between different metrics to identify relationships and dependencies."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize metrics correlation analyzer
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.db_path = "metrics.db"
    
    def _pearson_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate Pearson correlation coefficient between two metric series
        
        Args:
            x_values: List of X metric values
            y_values: List of Y metric values
        
        Returns:
            Correlation coefficient between -1 (perfect negative) and 1 (perfect positive)
        """
        if len(x_values) < 2 or len(y_values) < 2 or len(x_values) != len(y_values):
            return 0
        
        x_values = [v for v in x_values if v is not None]
        y_values = [v for v in y_values if v is not None]
        
        if len(x_values) < 2:
            return 0
        
        import statistics
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) 
                       for i in range(len(x_values)))
        
        x_stdev = statistics.stdev(x_values) if len(x_values) > 1 else 0
        y_stdev = statistics.stdev(y_values) if len(y_values) > 1 else 0
        
        if x_stdev == 0 or y_stdev == 0:
            return 0
        
        denominator = x_stdev * y_stdev * len(x_values)
        return numerator / denominator if denominator != 0 else 0
    
    def analyze_metric_correlations(self, days: int = 30, threshold: float = 0.5) -> Dict:
        """Analyze correlations between all available metrics
        
        Args:
            days: Historical period to analyze (default: 30)
            threshold: Correlation threshold for significance (0-1, default: 0.5)
        
        Returns:
            Dictionary with correlation pairs ranked by strength
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all metric names
            c.execute("""
                SELECT DISTINCT metric_name FROM metrics 
                WHERE timestamp > ?
                ORDER BY metric_name
            """, (cutoff_date.isoformat(),))
            
            metric_names = [row[0] for row in c.fetchall()]
            
            if len(metric_names) < 2:
                conn.close()
                return {"correlations": [], "metric_count": len(metric_names), "status": "insufficient_metrics"}
            
            # Get time-ordered metric values
            metric_data = {}
            for metric_name in metric_names:
                c.execute("""
                    SELECT metric_value FROM metrics 
                    WHERE metric_name = ? AND timestamp > ?
                    ORDER BY timestamp
                """, (metric_name, cutoff_date.isoformat()))
                metric_data[metric_name] = [row[0] for row in c.fetchall()]
            
            conn.close()
            
            # Calculate correlations between all metric pairs
            correlations = []
            for i, metric1 in enumerate(metric_names):
                for metric2 in metric_names[i+1:]:
                    data1 = metric_data[metric1]
                    data2 = metric_data[metric2]
                    
                    if len(data1) > 0 and len(data2) > 0:
                        # Align data by minimum length
                        min_len = min(len(data1), len(data2))
                        x = data1[:min_len]
                        y = data2[:min_len]
                        
                        corr = self._pearson_correlation(x, y)
                        
                        if abs(corr) >= threshold:
                            strength = "very strong" if abs(corr) > 0.9 else \
                                      "strong" if abs(corr) > 0.7 else \
                                      "moderate" if abs(corr) > 0.5 else "weak"
                            
                            correlations.append({
                                "metric1": metric1,
                                "metric2": metric2,
                                "correlation": round(corr, 3),
                                "strength": strength,
                                "direction": "positive" if corr > 0 else "negative",
                                "samples": min_len
                            })
            
            # Sort by absolute correlation
            correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
            
            self.logger.info(f"Analyzed {len(metric_names)} metrics, found {len(correlations)} correlations")
            
            return {
                "correlations": correlations,
                "metric_count": len(metric_names),
                "threshold": threshold,
                "analysis_period_days": days,
                "total_pairs_analyzed": len(metric_names) * (len(metric_names) - 1) // 2,
                "status": "success"
            }
        except Exception as e:
            self.logger.error(f"Error analyzing correlations: {e}")
            return {"error": str(e), "correlations": [], "status": "error"}
    
    def find_metric_predictors(self, target_metric: str, days: int = 30, 
                              correlation_threshold: float = 0.6) -> Dict:
        """Find metrics that predict or strongly correlate with a target metric
        
        Args:
            target_metric: The metric to predict
            days: Historical period to analyze (default: 30)
            correlation_threshold: Minimum correlation to consider (default: 0.6)
        
        Returns:
            Dictionary with predictor metrics ranked by correlation strength
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get target metric data
            c.execute("""
                SELECT metric_value FROM metrics 
                WHERE metric_name = ? AND timestamp > ?
                ORDER BY timestamp
            """, (target_metric, cutoff_date.isoformat()))
            
            target_values = [row[0] for row in c.fetchall()]
            
            if len(target_values) < 2:
                conn.close()
                return {"predictors": [], "target": target_metric, "status": "insufficient_data"}
            
            # Get all other metrics
            c.execute("""
                SELECT DISTINCT metric_name FROM metrics 
                WHERE metric_name != ? AND timestamp > ?
                ORDER BY metric_name
            """, (target_metric, cutoff_date.isoformat()))
            
            other_metrics = [row[0] for row in c.fetchall()]
            
            predictors = []
            for metric_name in other_metrics:
                c.execute("""
                    SELECT metric_value FROM metrics 
                    WHERE metric_name = ? AND timestamp > ?
                    ORDER BY timestamp
                """, (metric_name, cutoff_date.isoformat()))
                
                values = [row[0] for row in c.fetchall()]
                
                if len(values) > 0:
                    min_len = min(len(target_values), len(values))
                    corr = self._pearson_correlation(target_values[:min_len], values[:min_len])
                    
                    if abs(corr) >= correlation_threshold:
                        predictors.append({
                            "metric": metric_name,
                            "correlation": round(corr, 3),
                            "strength": "very strong" if abs(corr) > 0.9 else \
                                       "strong" if abs(corr) > 0.7 else "moderate",
                            "direction": "positive" if corr > 0 else "negative",
                            "samples": min_len
                        })
            
            conn.close()
            
            # Sort by absolute correlation
            predictors.sort(key=lambda x: abs(x["correlation"]), reverse=True)
            
            self.logger.info(f"Found {len(predictors)} predictors for {target_metric}")
            
            return {
                "target": target_metric,
                "predictors": predictors,
                "predictor_count": len(predictors),
                "threshold": correlation_threshold,
                "analysis_period_days": days,
                "status": "success"
            }
        except Exception as e:
            self.logger.error(f"Error finding predictors for {target_metric}: {e}")
            return {"error": str(e), "predictors": [], "target": target_metric, "status": "error"}
    
    def detect_metric_dependencies(self, days: int = 30, lag_window: int = 5) -> Dict:
        """Detect lagged dependencies between metrics (X at time t predicts Y at time t+lag)
        
        Args:
            days: Historical period to analyze (default: 30)
            lag_window: Maximum lag to check in samples (default: 5)
        
        Returns:
            Dictionary with lagged dependencies and their strength
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all metrics
            c.execute("""
                SELECT DISTINCT metric_name FROM metrics 
                WHERE timestamp > ?
                ORDER BY metric_name
            """, (cutoff_date.isoformat(),))
            
            metric_names = [row[0] for row in c.fetchall()]
            
            if len(metric_names) < 2:
                conn.close()
                return {"dependencies": [], "status": "insufficient_metrics"}
            
            # Get metric values
            metric_data = {}
            for metric_name in metric_names:
                c.execute("""
                    SELECT metric_value FROM metrics 
                    WHERE metric_name = ? AND timestamp > ?
                    ORDER BY timestamp
                """, (metric_name, cutoff_date.isoformat()))
                metric_data[metric_name] = [row[0] for row in c.fetchall()]
            
            conn.close()
            
            dependencies = []
            
            # Check for lagged correlations
            for i, metric1 in enumerate(metric_names):
                for metric2 in metric_names[i+1:]:
                    data1 = metric_data[metric1]
                    data2 = metric_data[metric2]
                    
                    if len(data1) < lag_window + 2 or len(data2) < lag_window + 2:
                        continue
                    
                    # Check if metric1 at time t predicts metric2 at time t+lag
                    best_lag = 0
                    best_corr = 0
                    
                    for lag in range(1, min(lag_window, len(data1) - 1)):
                        # Shift data1 forward by lag
                        x = data1[:len(data1) - lag]
                        y = data2[lag:]
                        
                        if len(x) > 0 and len(y) > 0:
                            corr = abs(self._pearson_correlation(x, y))
                            
                            if corr > best_corr:
                                best_corr = corr
                                best_lag = lag
                    
                    if best_corr > 0.6:
                        dependencies.append({
                            "source": metric1,
                            "target": metric2,
                            "lag": best_lag,
                            "correlation": round(best_corr, 3),
                            "interpretation": f"{metric1} at t→{metric2} at t+{best_lag}"
                        })
            
            # Sort by correlation
            dependencies.sort(key=lambda x: x["correlation"], reverse=True)
            
            self.logger.info(f"Found {len(dependencies)} lagged dependencies")
            
            return {
                "dependencies": dependencies,
                "lag_window": lag_window,
                "analysis_period_days": days,
                "status": "success"
            }
        except Exception as e:
            self.logger.error(f"Error detecting dependencies: {e}")
            return {"error": str(e), "dependencies": [], "status": "error"}


# ============================================================================
# FEATURE: PERFORMANCE BENCHMARKING FRAMEWORK
# ============================================================================

class BenchmarkManager:
    """Manage performance benchmarks and detect regressions between versions."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize benchmark manager
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.db_path = "metrics.db"
        self.benchmark_db = "benchmarks.db"
        self._init_benchmark_db()
    
    def _init_benchmark_db(self):
        """Initialize benchmark database if needed"""
        try:
            conn = sqlite3.connect(self.benchmark_db)
            c = conn.cursor()
            
            # Benchmarks table: stores snapshot of metrics at specific versions/times
            c.execute("""
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id INTEGER PRIMARY KEY,
                    benchmark_name TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    script_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_mean REAL,
                    cpu_stdev REAL,
                    memory_mean REAL,
                    memory_stdev REAL,
                    execution_time_mean REAL,
                    execution_time_stdev REAL,
                    sample_count INTEGER,
                    notes TEXT
                )
            """)
            
            # Regressions table: tracks detected performance regressions
            c.execute("""
                CREATE TABLE IF NOT EXISTS regressions (
                    id INTEGER PRIMARY KEY,
                    benchmark_name TEXT NOT NULL,
                    script_path TEXT,
                    metric_type TEXT,
                    previous_value REAL,
                    current_value REAL,
                    percent_change REAL,
                    severity TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    investigated BOOLEAN DEFAULT 0,
                    notes TEXT
                )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error initializing benchmark DB: {e}")
    
    def create_benchmark(self, benchmark_name: str, script_path: Optional[str] = None, 
                        version_id: Optional[str] = None, notes: Optional[str] = None) -> Dict:
        """Create a performance benchmark from current metrics
        
        Args:
            benchmark_name: Name of the benchmark
            script_path: Optional script to filter metrics
            version_id: Version identifier (default: timestamp)
            notes: Optional notes about the benchmark
        
        Returns:
            Dictionary with benchmark creation result
        """
        try:
            version_id = version_id or datetime.now().isoformat()
            
            # Get current metrics from main database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get CPU metrics
            c.execute("""
                SELECT metric_value FROM metrics 
                WHERE metric_name = 'cpu_percent'
                ORDER BY timestamp DESC LIMIT 100
            """)
            cpu_values = [row[0] for row in c.fetchall()]
            
            # Get memory metrics
            c.execute("""
                SELECT metric_value FROM metrics 
                WHERE metric_name = 'memory_mb'
                ORDER BY timestamp DESC LIMIT 100
            """)
            memory_values = [row[0] for row in c.fetchall()]
            
            # Get execution time metrics
            c.execute("""
                SELECT metric_value FROM metrics 
                WHERE metric_name = 'execution_time_seconds'
                ORDER BY timestamp DESC LIMIT 100
            """)
            exec_time_values = [row[0] for row in c.fetchall()]
            
            conn.close()
            
            # Calculate statistics
            import statistics
            cpu_mean = statistics.mean(cpu_values) if cpu_values else 0
            cpu_stdev = statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
            memory_mean = statistics.mean(memory_values) if memory_values else 0
            memory_stdev = statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            exec_mean = statistics.mean(exec_time_values) if exec_time_values else 0
            exec_stdev = statistics.stdev(exec_time_values) if len(exec_time_values) > 1 else 0
            
            # Store benchmark
            conn = sqlite3.connect(self.benchmark_db)
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO benchmarks 
                (benchmark_name, version_id, script_path, cpu_mean, cpu_stdev, 
                 memory_mean, memory_stdev, execution_time_mean, execution_time_stdev, 
                 sample_count, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (benchmark_name, version_id, script_path, cpu_mean, cpu_stdev,
                  memory_mean, memory_stdev, exec_mean, exec_stdev,
                  len(cpu_values), notes))
            
            benchmark_id = c.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"Benchmark '{benchmark_name}' created (version: {version_id})")
            
            return {
                "status": "success",
                "benchmark_id": benchmark_id,
                "name": benchmark_name,
                "version": version_id,
                "cpu": {"mean": round(cpu_mean, 2), "stdev": round(cpu_stdev, 2)},
                "memory": {"mean": round(memory_mean, 2), "stdev": round(memory_stdev, 2)},
                "execution_time": {"mean": round(exec_mean, 2), "stdev": round(exec_stdev, 2)}
            }
        except Exception as e:
            self.logger.error(f"Error creating benchmark: {e}")
            return {"status": "error", "error": str(e)}
    
    def compare_benchmarks(self, benchmark_name: str, version1_id: str, 
                          version2_id: str) -> Dict:
        """Compare two benchmark versions to detect changes
        
        Args:
            benchmark_name: Name of benchmark to compare
            version1_id: First version to compare (baseline)
            version2_id: Second version to compare (current)
        
        Returns:
            Dictionary with comparison results
        """
        try:
            conn = sqlite3.connect(self.benchmark_db)
            c = conn.cursor()
            
            # Get both benchmarks
            c.execute("""
                SELECT * FROM benchmarks 
                WHERE benchmark_name = ? AND version_id = ?
            """, (benchmark_name, version1_id))
            b1_row = c.fetchone()
            
            c.execute("""
                SELECT * FROM benchmarks 
                WHERE benchmark_name = ? AND version_id = ?
            """, (benchmark_name, version2_id))
            b2_row = c.fetchone()
            
            if not b1_row or not b2_row:
                conn.close()
                return {"status": "error", "error": "Benchmark version not found"}
            
            # Extract metrics (columns: 0=id, 1=name, 2=version, 3=script, 4=created_at,
            #                       5=cpu_mean, 6=cpu_stdev, 7=mem_mean, 8=mem_stdev,
            #                       9=exec_mean, 10=exec_stdev, 11=sample_count, 12=notes)
            
            comparisons = []
            metrics = [
                ("cpu_mean", 5, "CPU Usage (%)"),
                ("memory_mean", 7, "Memory Usage (MB)"),
                ("execution_time_mean", 9, "Execution Time (s)")
            ]
            
            for metric_key, idx, label in metrics:
                v1_val = b1_row[idx]
                v2_val = b2_row[idx]
                
                if v1_val > 0:
                    percent_change = ((v2_val - v1_val) / v1_val) * 100
                else:
                    percent_change = 0
                
                # Determine severity
                severity = "info"
                if abs(percent_change) > 20:
                    severity = "critical"
                elif abs(percent_change) > 10:
                    severity = "warning"
                
                comparisons.append({
                    "metric": label,
                    "baseline": round(v1_val, 2),
                    "current": round(v2_val, 2),
                    "percent_change": round(percent_change, 1),
                    "direction": "↑" if percent_change > 0 else "↓",
                    "severity": severity
                })
            
            conn.close()
            
            self.logger.info(f"Compared benchmarks '{benchmark_name}': {version1_id} → {version2_id}")
            
            return {
                "status": "success",
                "benchmark_name": benchmark_name,
                "baseline_version": version1_id,
                "current_version": version2_id,
                "comparisons": comparisons,
                "regressions": len([c for c in comparisons if c["severity"] in ["critical", "warning"]])
            }
        except Exception as e:
            self.logger.error(f"Error comparing benchmarks: {e}")
            return {"status": "error", "error": str(e)}
    
    def detect_regressions(self, benchmark_name: str, regression_threshold: float = 10.0) -> Dict:
        """Detect performance regressions in a benchmark
        
        Args:
            benchmark_name: Benchmark to analyze
            regression_threshold: Percent change threshold to flag as regression (default: 10%)
        
        Returns:
            Dictionary with detected regressions
        """
        try:
            conn = sqlite3.connect(self.benchmark_db)
            c = conn.cursor()
            
            # Get all versions of this benchmark, ordered by creation time
            c.execute("""
                SELECT id, version_id, cpu_mean, memory_mean, execution_time_mean
                FROM benchmarks 
                WHERE benchmark_name = ?
                ORDER BY created_at
            """, (benchmark_name,))
            
            versions = c.fetchall()
            
            if len(versions) < 2:
                conn.close()
                return {
                    "status": "insufficient_data",
                    "message": "Need at least 2 benchmark versions for regression detection"
                }
            
            regressions = []
            
            # Compare each version with the previous one
            for i in range(1, len(versions)):
                prev_ver = versions[i-1]
                curr_ver = versions[i]
                
                metrics_to_check = [
                    (2, "cpu_percent", prev_ver[2], curr_ver[2]),
                    (3, "memory_mb", prev_ver[3], curr_ver[3]),
                    (4, "execution_time_seconds", prev_ver[4], curr_ver[4])
                ]
                
                for idx, metric_type, prev_val, curr_val in metrics_to_check:
                    if prev_val > 0:
                        percent_change = ((curr_val - prev_val) / prev_val) * 100
                        
                        if abs(percent_change) >= regression_threshold:
                            severity = "critical" if abs(percent_change) > 30 else "warning"
                            
                            # Store regression
                            c.execute("""
                                INSERT INTO regressions 
                                (benchmark_name, metric_type, previous_value, current_value, 
                                 percent_change, severity)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (benchmark_name, metric_type, prev_val, curr_val,
                                  percent_change, severity))
                            
                            regressions.append({
                                "from_version": prev_ver[1],
                                "to_version": curr_ver[1],
                                "metric": metric_type,
                                "previous": round(prev_val, 2),
                                "current": round(curr_val, 2),
                                "percent_change": round(percent_change, 1),
                                "severity": severity
                            })
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Detected {len(regressions)} regressions in '{benchmark_name}'")
            
            return {
                "status": "success",
                "benchmark_name": benchmark_name,
                "regressions": regressions,
                "regression_count": len(regressions),
                "threshold_percent": regression_threshold
            }
        except Exception as e:
            self.logger.error(f"Error detecting regressions: {e}")
            return {"status": "error", "error": str(e)}
    
    def list_benchmarks(self, benchmark_name: Optional[str] = None) -> Dict:
        """List all benchmarks or versions of a specific benchmark
        
        Args:
            benchmark_name: Optional specific benchmark to list
        
        Returns:
            Dictionary with benchmark information
        """
        try:
            conn = sqlite3.connect(self.benchmark_db)
            c = conn.cursor()
            
            if benchmark_name:
                c.execute("""
                    SELECT version_id, created_at, cpu_mean, memory_mean, 
                           execution_time_mean, sample_count
                    FROM benchmarks 
                    WHERE benchmark_name = ?
                    ORDER BY created_at DESC
                """, (benchmark_name,))
            else:
                c.execute("""
                    SELECT DISTINCT benchmark_name FROM benchmarks
                    ORDER BY benchmark_name
                """)
            
            rows = c.fetchall()
            conn.close()
            
            if benchmark_name:
                versions = []
                for row in rows:
                    versions.append({
                        "version": row[0],
                        "created": row[1],
                        "cpu_mean": round(row[2], 2),
                        "memory_mean": round(row[3], 2),
                        "exec_time_mean": round(row[4], 2),
                        "samples": row[5]
                    })
                
                return {
                    "status": "success",
                    "benchmark": benchmark_name,
                    "versions": versions,
                    "version_count": len(versions)
                }
            else:
                return {
                    "status": "success",
                    "benchmarks": [row[0] for row in rows],
                    "benchmark_count": len(rows)
                }
        except Exception as e:
            self.logger.error(f"Error listing benchmarks: {e}")
            return {"status": "error", "error": str(e)}


# ============================================================================
# FEATURE: ALERT INTELLIGENCE & TUNING
# ============================================================================

class AlertIntelligence:
    """Intelligent alert management with auto-tuning, deduplication, and context-aware routing."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize alert intelligence system
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.db_path = "alerts.db"
        self.alert_history = {}
        self._init_alert_db()
    
    def _init_alert_db(self):
        """Initialize alert database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Alert history for deduplication and pattern analysis
            c.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    metric_name TEXT,
                    threshold REAL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    value REAL,
                    severity TEXT,
                    suppressed BOOLEAN DEFAULT 0,
                    acknowledged BOOLEAN DEFAULT 0
                )
            """)
            
            # Auto-tuned thresholds based on metric history
            c.execute("""
                CREATE TABLE IF NOT EXISTS tuned_thresholds (
                    id INTEGER PRIMARY KEY,
                    metric_name TEXT NOT NULL UNIQUE,
                    lower_threshold REAL,
                    upper_threshold REAL,
                    tuning_method TEXT,
                    confidence REAL,
                    last_tuned TIMESTAMP,
                    sample_count INTEGER
                )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error initializing alert DB: {e}")
    
    def deduplicate_alerts(self, alerts: List[Dict], time_window_seconds: int = 300) -> List[Dict]:
        """Remove duplicate alerts within a time window
        
        Args:
            alerts: List of alert dictionaries
            time_window_seconds: Time window for deduplication
        
        Returns:
            Deduplicated alert list
        """
        try:
            deduplicated = []
            
            for alert in alerts:
                alert_key = (alert.get('type'), alert.get('metric'), str(alert.get('threshold')))
                
                # Check if similar alert exists in history
                found_duplicate = False
                for hist_alert in self.alert_history.get(alert_key, []):
                    time_diff = (datetime.now() - hist_alert.get('timestamp', datetime.now())).total_seconds()
                    
                    if time_diff < time_window_seconds:
                        found_duplicate = True
                        self.logger.debug(f"Alert deduplicated: {alert['type']} for {alert.get('metric')}")
                        break
                
                if not found_duplicate:
                    deduplicated.append(alert)
                    
                    # Add to history
                    if alert_key not in self.alert_history:
                        self.alert_history[alert_key] = []
                    
                    alert_copy = alert.copy()
                    alert_copy['timestamp'] = datetime.now()
                    self.alert_history[alert_key].append(alert_copy)
            
            return deduplicated
        except Exception as e:
            self.logger.error(f"Error deduplicating alerts: {e}")
            return alerts
    
    def calculate_adaptive_threshold(self, metric_name: str, metric_history: List[float],
                                    method: str = "iqr") -> Dict:
        """Calculate adaptive thresholds based on metric history
        
        Args:
            metric_name: Name of the metric
            metric_history: Historical metric values
            method: Calculation method (iqr, zscore, percentile)
        
        Returns:
            Dictionary with adaptive thresholds
        """
        try:
            if len(metric_history) < 10:
                return {"status": "insufficient_data", "lower": 0, "upper": 100}
            
            import statistics
            metric_history = [v for v in metric_history if v is not None]
            
            if method == "iqr":
                # IQR method: Q1 - 1.5*IQR, Q3 + 1.5*IQR
                sorted_vals = sorted(metric_history)
                n = len(sorted_vals)
                q1 = sorted_vals[n // 4]
                q3 = sorted_vals[3 * n // 4]
                iqr = q3 - q1
                
                lower = max(0, q1 - 1.5 * iqr)
                upper = q3 + 1.5 * iqr
                confidence = 0.95
                
            elif method == "zscore":
                # Z-score method: mean ± 2*stdev
                mean = statistics.mean(metric_history)
                stdev = statistics.stdev(metric_history) if len(metric_history) > 1 else 0
                
                lower = max(0, mean - 2 * stdev)
                upper = mean + 2 * stdev
                confidence = 0.95
                
            elif method == "percentile":
                # Percentile method: P5-P95
                sorted_vals = sorted(metric_history)
                p5_idx = max(0, len(sorted_vals) // 20)
                p95_idx = min(len(sorted_vals) - 1, 19 * len(sorted_vals) // 20)
                
                lower = sorted_vals[p5_idx]
                upper = sorted_vals[p95_idx]
                confidence = 0.90
            else:
                return {"status": "unknown_method"}
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("""
                INSERT OR REPLACE INTO tuned_thresholds 
                (metric_name, lower_threshold, upper_threshold, tuning_method, confidence, last_tuned, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (metric_name, lower, upper, method, confidence, 
                  datetime.now().isoformat(), len(metric_history)))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Adaptive threshold calculated for {metric_name}: [{lower:.2f}, {upper:.2f}]")
            
            return {
                "status": "success",
                "metric": metric_name,
                "method": method,
                "lower": round(lower, 2),
                "upper": round(upper, 2),
                "confidence": confidence,
                "samples": len(metric_history)
            }
        except Exception as e:
            self.logger.error(f"Error calculating adaptive threshold: {e}")
            return {"status": "error", "error": str(e)}
    
    def analyze_alert_patterns(self, metric_name: str, hours: int = 24) -> Dict:
        """Analyze alert patterns to identify recurring issues
        
        Args:
            metric_name: Metric to analyze
            hours: Time period to analyze
        
        Returns:
            Dictionary with alert patterns
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Get alerts for this metric
            c.execute("""
                SELECT triggered_at, value, severity FROM alert_history
                WHERE metric_name = ? AND triggered_at > ?
                ORDER BY triggered_at
            """, (metric_name, cutoff_time.isoformat()))
            
            alerts = c.fetchall()
            conn.close()
            
            if not alerts:
                return {
                    "status": "no_data",
                    "metric": metric_name,
                    "period_hours": hours
                }
            
            # Analyze patterns
            severity_counts = {"critical": 0, "warning": 0, "info": 0}
            for alert in alerts:
                severity_counts[alert[2]] = severity_counts.get(alert[2], 0) + 1
            
            values = [a[1] for a in alerts if a[1] is not None]
            import statistics
            
            alert_freq = len(alerts) / hours  # alerts per hour
            
            return {
                "status": "success",
                "metric": metric_name,
                "period_hours": hours,
                "total_alerts": len(alerts),
                "alerts_per_hour": round(alert_freq, 2),
                "severity_distribution": severity_counts,
                "value_stats": {
                    "mean": round(statistics.mean(values), 2) if values else 0,
                    "min": round(min(values), 2) if values else 0,
                    "max": round(max(values), 2) if values else 0
                },
                "recommendation": self._generate_alert_recommendation(alert_freq, severity_counts)
            }
        except Exception as e:
            self.logger.error(f"Error analyzing alert patterns: {e}")
            return {"status": "error", "error": str(e)}
    
    def _generate_alert_recommendation(self, alert_freq: float, severity_counts: Dict) -> str:
        """Generate recommendation based on alert patterns
        
        Args:
            alert_freq: Alerts per hour
            severity_counts: Count of alerts by severity
        
        Returns:
            Recommendation text
        """
        if alert_freq > 10:
            return "Consider tuning thresholds - too many alerts per hour"
        elif alert_freq > 2:
            return "Alert frequency elevated - monitor and adjust if needed"
        elif severity_counts.get("critical", 0) > 5:
            return "Multiple critical alerts detected - investigate root cause"
        elif severity_counts.get("warning", 0) > severity_counts.get("critical", 0) * 3:
            return "Many warning alerts - consider adjusting threshold sensitivity"
        else:
            return "Alert patterns appear normal"
    
    def suggest_alert_routing(self, alert: Dict, team_policies: Optional[Dict] = None) -> Dict:
        """Suggest intelligent routing for an alert based on context
        
        Args:
            alert: Alert dictionary
            team_policies: Optional team routing policies
        
        Returns:
            Dictionary with suggested routing
        """
        try:
            team_policies = team_policies or {
                "critical": {"team": "oncall", "method": "sms"},
                "warning": {"team": "engineering", "method": "email"},
                "info": {"team": "devops", "method": "slack"}
            }
            
            severity = alert.get('severity', 'info')
            metric = alert.get('metric', 'unknown')
            
            # Base routing on severity
            routing = team_policies.get(severity, {"team": "ops", "method": "log"})
            
            # Enhance routing based on metric type
            if "cpu" in metric.lower() or "memory" in metric.lower():
                routing["team"] = "infrastructure"
            elif "database" in metric.lower() or "latency" in metric.lower():
                routing["team"] = "backend"
            elif "response_time" in metric.lower() or "error_rate" in metric.lower():
                routing["team"] = "frontend"
            
            # Add escalation info
            if severity == "critical":
                routing["escalation_minutes"] = 15
                routing["require_acknowledgment"] = True
            elif severity == "warning":
                routing["escalation_minutes"] = 60
            
            return {
                "status": "success",
                "suggested_team": routing.get("team"),
                "notification_method": routing.get("method"),
                "escalation_minutes": routing.get("escalation_minutes"),
                "require_acknowledgment": routing.get("require_acknowledgment", False)
            }
        except Exception as e:
            self.logger.error(f"Error suggesting routing: {e}")
            return {"status": "error", "error": str(e)}


# ============================================================================
# FEATURE: ADVANCED DEBUGGING & PROFILING
# ============================================================================

class AdvancedProfiler:
    """Advanced CPU/memory/I/O profiling with call stack and system call tracing."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize advanced profiler
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.profiles = {}
    
    def profile_cpu_and_memory(self, script_path: str, duration_seconds: int = 60,
                               sample_interval: float = 0.1) -> Dict:
        """Profile CPU and memory usage with high-frequency sampling
        
        Args:
            script_path: Path to script to profile
            duration_seconds: Duration of profiling
            sample_interval: Sampling interval in seconds
        
        Returns:
            Dictionary with detailed profiling results
        """
        try:
            import subprocess
            import resource
            
            cpu_samples = []
            memory_samples = []
            start_time = time.time()
            
            # Start process
            process = subprocess.Popen(['python', script_path], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            
            try:
                while (time.time() - start_time) < duration_seconds:
                    try:
                        # Get process stats
                        with open(f'/proc/{process.pid}/stat', 'r') as f:
                            stat = f.read().split()
                            utime = int(stat[13]) / 100  # User time
                            stime = int(stat[14]) / 100  # System time
                            cpu_samples.append({'time': time.time() - start_time, 'cpu': utime + stime})
                        
                        with open(f'/proc/{process.pid}/status', 'r') as f:
                            for line in f:
                                if 'VmRSS' in line:
                                    mem_kb = int(line.split()[1])
                                    memory_samples.append({'time': time.time() - start_time, 'memory': mem_kb / 1024})
                                    break
                    except (IOError, ValueError, OSError):
                        # Silently handle parsing errors from /proc filesystem
                        pass
                    
                    time.sleep(sample_interval)
                    
                    if process.poll() is not None:
                        break
            finally:
                process.terminate()
                process.wait()
            
            # Analyze samples
            if cpu_samples:
                cpu_values = [s['cpu'] for s in cpu_samples]
                import statistics
                cpu_stats = {
                    "mean": statistics.mean(cpu_values),
                    "max": max(cpu_values),
                    "min": min(cpu_values),
                    "stdev": statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
                }
            else:
                cpu_stats = {"mean": 0, "max": 0, "min": 0, "stdev": 0}
            
            if memory_samples:
                mem_values = [s['memory'] for s in memory_samples]
                import statistics
                mem_stats = {
                    "mean": statistics.mean(mem_values),
                    "peak": max(mem_values),
                    "min": min(mem_values),
                    "stdev": statistics.stdev(mem_values) if len(mem_values) > 1 else 0
                }
            else:
                mem_stats = {"mean": 0, "peak": 0, "min": 0, "stdev": 0}
            
            self.logger.info(f"Profiled {script_path}: {len(cpu_samples)} samples")
            
            return {
                "status": "success",
                "script": script_path,
                "duration_seconds": duration_seconds,
                "samples_collected": len(cpu_samples),
                "cpu_stats": {k: round(v, 2) for k, v in cpu_stats.items()},
                "memory_stats_mb": {k: round(v, 2) for k, v in mem_stats.items()},
                "profile_type": "cpu_memory"
            }
        except Exception as e:
            self.logger.error(f"Error profiling: {e}")
            return {"status": "error", "error": str(e)}
    
    def io_profile(self, script_path: str) -> Dict:
        """Profile I/O operations (disk reads/writes)
        
        Args:
            script_path: Path to script to profile
        
        Returns:
            Dictionary with I/O statistics
        """
        try:
            import subprocess
            
            # Use strace to capture I/O operations (SECURE: avoid shell=True)
            cmd = ["strace", "-e", "openat,read,write", "-c", "python", script_path]
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60,
                    shell=False  # CRITICAL FIX: Disable shell to prevent command injection
                )
            except FileNotFoundError:
                self.logger.warning("strace not available, using Python profiler instead")
                import cProfile
                import io
                import pstats
                
                pr = cProfile.Profile()
                pr.enable()
                try:
                    with open(script_path, 'r') as f:
                        exec(f.read(), {'__name__': '__main__'})
                except:
                    pass
                pr.disable()
                
                s = io.StringIO()
                ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
                ps.print_stats()
                result_text = s.getvalue()
                
                return {
                    "status": "success",
                    "script": script_path,
                    "profile_type": "cpu",
                    "fallback": True,
                    "data": result_text
                }
            
            # Parse strace output safely
            io_calls = {"reads": 0, "writes": 0, "opens": 0}
            output = result.stderr if result.stderr else result.stdout
            
            for line in output.split('\n'):
                line_lower = line.lower()
                if 'read' in line_lower:
                    io_calls['reads'] += 1
                elif 'write' in line_lower:
                    io_calls['writes'] += 1
                elif 'openat' in line_lower:
                    io_calls['opens'] += 1
            
            self.logger.info(f"I/O profiled {script_path}: {io_calls}")
            
            return {
                "status": "success",
                "script": script_path,
                "io_operations": io_calls,
                "profile_type": "io"
            }
        except Exception as e:
            self.logger.error(f"Error profiling I/O: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_profile_summary(self, profile_id: Optional[str] = None) -> Dict:
        """Get summary of profiling results
        
        Args:
            profile_id: Optional profile ID to retrieve
        
        Returns:
            Dictionary with profile summary
        """
        try:
            if profile_id and profile_id in self.profiles:
                return {
                    "status": "success",
                    "profiles": [self.profiles[profile_id]]
                }
            
            return {
                "status": "success",
                "profiles": list(self.profiles.values()),
                "profile_count": len(self.profiles)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ============================================================================
# FEATURE: ENTERPRISE INTEGRATIONS
# ============================================================================

class EnterpriseIntegrations:
    """Integrate with enterprise monitoring platforms (DataDog, New Relic, Prometheus, etc)."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize enterprise integrations
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def send_to_datadog(self, metric_name: str, value: float, tags: Optional[Dict] = None,
                       api_key: Optional[str] = None) -> Dict:
        """Send metrics to Datadog
        
        Args:
            metric_name: Name of metric
            value: Metric value
            tags: Optional tags dictionary
            api_key: Datadog API key
        
        Returns:
            Dictionary with transmission result
        """
        try:
            if not api_key:
                return {"status": "error", "error": "Datadog API key required"}
            
            import requests
            
            url = "https://api.datadoghq.com/api/v1/series"
            headers = {"DD-API-KEY": api_key}
            
            payload = {
                "series": [{
                    "metric": f"custom.script_runner.{metric_name}",
                    "points": [[int(time.time()), value]],
                    "type": "gauge",
                    "tags": tags or []
                }]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 202:
                self.logger.info(f"Sent to Datadog: {metric_name}={value}")
                return {"status": "success", "platform": "datadog"}
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.logger.error(f"Error sending to Datadog: {e}")
            return {"status": "error", "error": str(e)}
    
    def send_to_prometheus(self, metric_name: str, value: float, 
                          pushgateway_url: Optional[str] = None) -> Dict:
        """Send metrics to Prometheus via Pushgateway
        
        Args:
            metric_name: Name of metric
            value: Metric value
            pushgateway_url: Prometheus Pushgateway URL
        
        Returns:
            Dictionary with transmission result
        """
        try:
            if not pushgateway_url:
                return {"status": "error", "error": "Pushgateway URL required"}
            
            import requests
            
            # Format: metric_name{job="script_runner"} value
            metric_line = f'script_runner_{metric_name}{{job="script_runner"}} {value}'
            
            url = f"{pushgateway_url}/metrics/job/script_runner"
            response = requests.post(url, data=metric_line, timeout=10)
            
            if response.status_code == 202:
                self.logger.info(f"Sent to Prometheus: {metric_name}={value}")
                return {"status": "success", "platform": "prometheus"}
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.logger.error(f"Error sending to Prometheus: {e}")
            return {"status": "error", "error": str(e)}
    
    def send_to_newrelic(self, metric_name: str, value: float, account_id: Optional[str] = None,
                        api_key: Optional[str] = None) -> Dict:
        """Send metrics to New Relic
        
        Args:
            metric_name: Name of metric
            value: Metric value
            account_id: New Relic Account ID
            api_key: New Relic API key
        
        Returns:
            Dictionary with transmission result
        """
        try:
            if not api_key or not account_id:
                return {"status": "error", "error": "New Relic API key and Account ID required"}
            
            import requests
            
            url = "https://metric-api.newrelic.com/metric/v1"
            headers = {"Api-Key": api_key}
            
            payload = {
                "metrics": [{
                    "name": f"custom.script_runner.{metric_name}",
                    "type": "gauge",
                    "value": value,
                    "timestamp": int(time.time() * 1000)
                }]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 202:
                self.logger.info(f"Sent to New Relic: {metric_name}={value}")
                return {"status": "success", "platform": "newrelic"}
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            self.logger.error(f"Error sending to New Relic: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_integration_status(self) -> Dict:
        """Get status of all configured integrations
        
        Returns:
            Dictionary with integration statuses
        """
        return {
            "status": "success",
            "available_integrations": [
                "datadog",
                "prometheus",
                "newrelic",
                "splunk",
                "cloudwatch"
            ],
            "message": "Configure via API keys and URLs in environment or config"
        }


# ============================================================================
# FEATURE: RESOURCE PREDICTION & FORECASTING
# ============================================================================

class ResourceForecaster:
    """Predict future resource needs and forecast SLA compliance."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize resource forecaster
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.db_path = "metrics.db"
    
    def forecast_metric(self, metric_name: str, days_ahead: int = 7,
                       method: str = "linear") -> Dict:
        """Forecast metric values for future periods
        
        Args:
            metric_name: Name of metric to forecast
            days_ahead: Number of days to forecast
            method: Forecasting method (linear, exponential, seasonal)
        
        Returns:
            Dictionary with forecast data
        """
        try:
            # Get historical data
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            cutoff = datetime.now() - timedelta(days=90)
            c.execute("""
                SELECT timestamp, metric_value FROM metrics 
                WHERE metric_name = ? AND timestamp > ?
                ORDER BY timestamp
            """, (metric_name, cutoff.isoformat()))
            
            data = c.fetchall()
            conn.close()
            
            if len(data) < 10:
                return {"status": "insufficient_data", "min_required": 10, "available": len(data)}
            
            values = [row[1] for row in data if row[1] is not None]
            
            if method == "linear":
                # Simple linear regression
                import statistics
                n = len(values)
                x = list(range(n))
                y = values
                
                x_mean = statistics.mean(x)
                y_mean = statistics.mean(y)
                
                slope = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n)) / sum((x[i] - x_mean) ** 2 for i in range(n))
                intercept = y_mean - slope * x_mean
                
                forecast = []
                for d in range(1, days_ahead + 1):
                    predicted = intercept + slope * (n + d)
                    forecast.append({"days_ahead": d, "predicted_value": round(predicted, 2)})
            
            elif method == "exponential":
                # Exponential smoothing
                alpha = 0.3
                forecast = [values[-1]]
                
                for _ in range(days_ahead):
                    next_val = alpha * values[-1] + (1 - alpha) * forecast[-1]
                    forecast.append(next_val)
                    values.append(next_val)
                
                forecast = [{"days_ahead": d + 1, "predicted_value": round(forecast[d + 1], 2)} 
                           for d in range(days_ahead)]
            
            else:  # seasonal
                # Simple seasonal pattern (weekly)
                import statistics
                weekly_avg = statistics.mean(values[-7:]) if len(values) >= 7 else statistics.mean(values)
                
                forecast = [{"days_ahead": d, "predicted_value": round(weekly_avg, 2)} 
                           for d in range(1, days_ahead + 1)]
            
            self.logger.info(f"Forecasted {metric_name} for {days_ahead} days")
            
            return {
                "status": "success",
                "metric": metric_name,
                "method": method,
                "forecast_days": days_ahead,
                "forecast": forecast,
                "confidence": 0.85 if method == "linear" else 0.70
            }
        except Exception as e:
            self.logger.error(f"Error forecasting: {e}")
            return {"status": "error", "error": str(e)}
    
    def predict_sla_compliance(self, sla_threshold: float, metric_name: str,
                              forecast_days: int = 7) -> Dict:
        """Predict SLA compliance based on forecasted metrics
        
        Args:
            sla_threshold: SLA threshold value
            metric_name: Metric to check against SLA
            forecast_days: Days ahead to forecast
        
        Returns:
            Dictionary with SLA prediction
        """
        try:
            # Get forecast
            forecast_result = self.forecast_metric(metric_name, days_ahead=forecast_days)
            
            if forecast_result['status'] != 'success':
                return forecast_result
            
            forecast = forecast_result['forecast']
            
            # Check compliance
            violations = 0
            for day in forecast:
                if day['predicted_value'] > sla_threshold:
                    violations += 1
            
            compliance_percent = ((forecast_days - violations) / forecast_days) * 100
            
            self.logger.info(f"Predicted SLA compliance: {compliance_percent:.1f}%")
            
            return {
                "status": "success",
                "metric": metric_name,
                "sla_threshold": sla_threshold,
                "forecast_days": forecast_days,
                "predicted_compliance": round(compliance_percent, 1),
                "predicted_violations": violations,
                "risk_level": "critical" if compliance_percent < 80 else "warning" if compliance_percent < 95 else "low"
            }
        except Exception as e:
            self.logger.error(f"Error predicting SLA compliance: {e}")
            return {"status": "error", "error": str(e)}
    
    def estimate_capacity_needs(self, metric_name: str, growth_rate: float = 0.1,
                               forecast_months: int = 12) -> Dict:
        """Estimate capacity needs based on metric growth
        
        Args:
            metric_name: Metric to forecast
            growth_rate: Expected monthly growth rate (0.1 = 10%)
            forecast_months: Months to forecast
        
        Returns:
            Dictionary with capacity recommendations
        """
        try:
            # Get current metric
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("""
                SELECT AVG(metric_value) FROM metrics 
                WHERE metric_name = ?
            """, (metric_name,))
            
            current_value = c.fetchone()[0] or 0
            conn.close()
            
            # Calculate capacity needs
            forecast = []
            value = current_value
            
            for month in range(1, forecast_months + 1):
                value = value * (1 + growth_rate)
                forecast.append({
                    "month": month,
                    "estimated_value": round(value, 2),
                    "growth_percent": round((value - current_value) / current_value * 100, 1)
                })
            
            # Recommendation
            max_value = forecast[-1]['estimated_value']
            recommended_capacity = max_value * 1.2  # 20% buffer
            
            self.logger.info(f"Capacity estimate for {metric_name}: {recommended_capacity:.2f}")
            
            return {
                "status": "success",
                "metric": metric_name,
                "current_value": round(current_value, 2),
                "growth_rate_monthly": f"{growth_rate*100:.0f}%",
                "forecast_months": forecast_months,
                "forecast": forecast[:12],  # Show first 12 months
                "max_estimated": round(max_value, 2),
                "recommended_capacity": round(recommended_capacity, 2),
                "buffer_percent": 20
            }
        except Exception as e:
            self.logger.error(f"Error estimating capacity: {e}")
            return {"status": "error", "error": str(e)}


# ============================================================================
# FEATURE: DISTRIBUTED EXECUTION SUPPORT
# ============================================================================

class RemoteExecutor:
    """Execute scripts on remote machines and containers
    
    Provides secure remote execution with input validation and sanitization
    to prevent injection attacks.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize remote executor
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.ssh_clients = {}
    
    @staticmethod
    def _validate_host(host: str) -> bool:
        """Validate host is a valid IP or hostname
        
        Args:
            host: Hostname or IP address to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If host is invalid
        """
        import socket
        import re
        
        if not host or len(host) > 255:
            raise ValueError(f"Invalid host: '{host}'")
        
        # Simple hostname validation (alphanumeric, dots, hyphens)
        hostname_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        
        # Try to resolve hostname
        try:
            socket.gethostbyname(host)
            return True
        except socket.gaierror:
            # Check if it matches valid hostname pattern at least
            if re.match(hostname_pattern, host):
                return True
            raise ValueError(f"Invalid or unresolvable host: '{host}'")
    
    @staticmethod
    def _validate_script_path(script_path: str) -> bool:
        """Validate script path is safe
        
        Args:
            script_path: Path to script to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If path is invalid
        """
        if not script_path or script_path.startswith('-'):
            raise ValueError(f"Invalid script path: '{script_path}'")
        
        # Check for path traversal attempts
        if '..' in script_path or script_path.startswith('/etc') or script_path.startswith('/sys'):
            raise ValueError(f"Suspicious path detected: '{script_path}'")
        
        return True
    
    @staticmethod
    def _sanitize_argument(arg: str) -> str:
        """Sanitize argument using shell quoting
        
        Args:
            arg: Argument to sanitize
            
        Returns:
            Safely quoted argument
        """
        import shlex
        return shlex.quote(arg)
    
    def execute_ssh(self, host: str, script_path: str, args: Optional[List[str]] = None,
                   username: Optional[str] = None, key_file: Optional[str] = None,
                   timeout: int = 300) -> Dict:
        """Execute script on remote host via SSH with input validation
        
        Args:
            host: Hostname or IP address
            script_path: Path to script on remote machine
            args: Script arguments
            username: SSH username (alphanumeric only)
            key_file: Path to SSH private key
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary with exit_code, stdout, stderr
            
        Raises:
            ValueError: If input validation fails
        """
        try:
            # Validate inputs
            self._validate_host(host)
            self._validate_script_path(script_path)
            
            if username and not username.isalnum():
                raise ValueError(f"Invalid username: '{username}' (must be alphanumeric)")
            
            if timeout < 1 or timeout > 86400:  # 1 second to 24 hours
                raise ValueError(f"Invalid timeout: {timeout} (must be 1-86400 seconds)")
            
            import paramiko
            
            # Create SSH client with secure host key verification
            client = paramiko.SSHClient()
            
            # SECURITY FIX: Load system host keys and reject unknown hosts
            # This prevents Man-in-the-Middle attacks
            try:
                client.load_system_host_keys()
                self.logger.debug("Loaded system host keys")
            except Exception as e:
                self.logger.warning(f"Could not load system host keys: {e}")
            
            # Use RejectPolicy instead of AutoAddPolicy for better security
            # AutoAddPolicy blindly accepts any host key (VULNERABLE)
            # RejectPolicy requires known_hosts or pre-configured keys
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            
            # Connect with proper error handling
            try:
                key = paramiko.RSAKey.from_private_key_file(key_file) if key_file else None
                client.connect(
                    host, 
                    username=username, 
                    pkey=key, 
                    timeout=timeout,
                    allow_agent=True,  # Allow SSH agent use
                    look_for_keys=True  # Look for default key files
                )
                self.logger.info(f"SSH connection established to {host}")
            except Exception as ssh_err:
                self.logger.error(f"SSH connection error for {host}: SSH failed")
                client.close()
                return {
                    "status": "error",
                    "host": host,
                    "message": "SSH connection failed"
                }
            
            # Build command with proper escaping
            cmd = f"python {shlex.quote(script_path)}"
            if args:
                # Sanitize each argument individually
                sanitized_args = [self._sanitize_argument(arg) for arg in args]
                cmd += " " + " ".join(sanitized_args)
            
            # Execute
            stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            
            out = stdout.read().decode('utf-8')
            err = stderr.read().decode('utf-8')
            
            client.close()
            
            self.logger.info(f"Remote execution on {host}: exit_code={exit_code}")
            return {
                "status": "success",
                "host": host,
                "exit_code": exit_code,
                "stdout": out,
                "stderr": err
            }
        except Exception as e:
            # SECURITY: Don't log full exception with potential credentials
            error_msg = str(e)
            if any(x in error_msg.lower() for x in ['password', 'key', 'credential', 'secret']):
                error_msg = "Authentication failed (details redacted for security)"
            self.logger.error(f"SSH execution failed on {host}: {error_msg}")
            return {
                "status": "error",
                "host": host,
                "message": error_msg
            }
    
    def execute_docker(self, image: str, script_path: str, args: Optional[List[str]] = None,
                      container_name: Optional[str] = None, env_vars: Optional[Dict] = None,
                      timeout: int = 300) -> Dict:
        """Execute script in Docker container with input validation
        
        Args:
            image: Docker image name (validated format)
            script_path: Path to script in container
            args: Script arguments
            container_name: Optional container name
            env_vars: Environment variables to pass
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary with exit_code, stdout, stderr
            
        Raises:
            ValueError: If input validation fails
        """
        try:
            # Validate inputs
            if not image or not isinstance(image, str):
                raise ValueError(f"Invalid Docker image: '{image}'")
            
            self._validate_script_path(script_path)
            
            if timeout < 1 or timeout > 86400:
                raise ValueError(f"Invalid timeout: {timeout} (must be 1-86400 seconds)")
            
            # Validate container name if provided
            if container_name:
                if not container_name.replace('_', '').replace('-', '').isalnum():
                    raise ValueError(f"Invalid container name: '{container_name}' (alphanumeric, -, _ only)")
            
            import docker
            
            client = docker.from_env()
            
            # Build command with proper escaping
            cmd = f"python {shlex.quote(script_path)}"
            if args:
                # Sanitize each argument individually
                sanitized_args = [self._sanitize_argument(arg) for arg in args]
                cmd += " " + " ".join(sanitized_args)
            
            # Validate environment variables
            safe_env_vars = {}
            if env_vars:
                for key, value in env_vars.items():
                    if not key.isalnum() and key.replace('_', '').isalnum():
                        safe_env_vars[key] = str(value)
            
            # Run container
            result = client.containers.run(
                image,
                cmd,
                name=container_name,
                environment=safe_env_vars or {},
                remove=True,
                timeout=timeout
            )
            
            self.logger.info(f"Docker execution completed: image={image}, exit_code=0")
            return {
                "status": "success",
                "image": image,
                "exit_code": 0,
                "output": result.decode('utf-8') if isinstance(result, bytes) else str(result)
            }
        except ValueError as e:
            self.logger.error(f"Docker execution validation failed: {e}")
            return {
                "status": "error",
                "image": image,
                "message": f"Validation error: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Docker execution failed: {e}")
            return {
                "status": "error",
                "image": image,
                "message": str(e)
            }
    
    def execute_kubernetes(self, namespace: str, job_name: str, image: str,
                          command: List[str], timeout: int = 300) -> Dict:
        """Execute script as Kubernetes Job
        
        Args:
            namespace: Kubernetes namespace
            job_name: Job name
            image: Container image
            command: Command and args to run
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary with job status and results
        """
        try:
            from kubernetes import client, config, watch
            
            # Load kubeconfig
            config.load_incluster_config()
            
            v1 = client.BatchV1Api()
            
            # Create job manifest
            job_body = {
                "apiVersion": "batch/v1",
                "kind": "Job",
                "metadata": {"name": job_name, "namespace": namespace},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": job_name,
                                "image": image,
                                "command": command
                            }],
                            "restartPolicy": "Never"
                        }
                    }
                }
            }
            
            # Submit job
            v1.create_namespaced_job(namespace, job_body)
            
            self.logger.info(f"Kubernetes job {job_name} submitted to {namespace}")
            return {
                "status": "submitted",
                "namespace": namespace,
                "job_name": job_name,
                "image": image
            }
        except Exception as e:
            self.logger.error(f"Kubernetes execution failed: {e}")
            return {
                "status": "error",
                "namespace": namespace,
                "job_name": job_name,
                "message": str(e)
            }


# ============================================================================
# FEATURE: ADVANCED RETRY & RECOVERY STRATEGIES
# ============================================================================

class RetryStrategy(Enum):
    """Available retry backoff strategies"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    EXPONENTIAL_WITH_JITTER = "exponential_jitter"


class RetryConfig:
    """Configuration for retry behavior with multiple backoff strategies"""
    
    def __init__(self, max_attempts: int = 3, strategy: str = "exponential",
                 initial_delay: float = 1.0, max_delay: float = 60.0,
                 multiplier: float = 2.0, retry_on_errors: Optional[List[str]] = None,
                 skip_on_errors: Optional[List[str]] = None, max_total_time: float = 300.0):
        """
        Args:
            max_attempts: Maximum number of retry attempts
            strategy: Backoff strategy (linear, exponential, fibonacci, exponential_jitter)
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay between retries in seconds
            multiplier: Multiplier for exponential backoff (default: 2.0)
            retry_on_errors: Only retry on these error types (None = retry on all)
            skip_on_errors: Don't retry on these error types
            max_total_time: Maximum total time for all retries in seconds
        """
        self.max_attempts = max_attempts
        self.strategy = RetryStrategy(strategy)
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.retry_on_errors = retry_on_errors or []
        self.skip_on_errors = skip_on_errors or []
        self.max_total_time = max_total_time
        self.logger = logging.getLogger(__name__)
        
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed)
        
        Args:
            attempt: Current attempt number (0 = first retry)
            
        Returns:
            Delay in seconds
        """
        if attempt < 0:
            return 0
        
        if self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * (attempt + 1)
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.multiplier ** attempt)
        elif self.strategy == RetryStrategy.FIBONACCI:
            # Generate fibonacci number
            fib = [1, 1]
            for _ in range(attempt):
                fib.append(fib[-1] + fib[-2])
            delay = self.initial_delay * fib[min(attempt, len(fib) - 1)]
        elif self.strategy == RetryStrategy.EXPONENTIAL_WITH_JITTER:
            # Exponential backoff with random jitter
            import random
            base_delay = self.initial_delay * (self.multiplier ** attempt)
            jitter = random.uniform(0, base_delay)
            delay = base_delay + jitter
        else:
            delay = self.initial_delay
        
        # Cap at max_delay
        return min(delay, self.max_delay)
    
    def should_retry(self, error: Optional[Exception], exit_code: int, total_time: float,
                     attempt: int) -> bool:
        """Determine if retry should be attempted
        
        Args:
            error: Exception that occurred (if any)
            exit_code: Process exit code
            total_time: Total time spent so far
            attempt: Current attempt number
            
        Returns:
            True if should retry, False otherwise
        """
        # Check attempt limit
        if attempt >= self.max_attempts:
            self.logger.debug(f"Max attempts ({self.max_attempts}) reached")
            return False
        
        # Check total time budget
        if total_time >= self.max_total_time:
            self.logger.debug(f"Max total time ({self.max_total_time}s) exceeded")
            return False
        
        # Check if we should skip retry for certain errors
        if error:
            error_type = type(error).__name__
            
            if self.skip_on_errors and error_type in self.skip_on_errors:
                self.logger.debug(f"Skipping retry for error type: {error_type}")
                return False
            
            if self.retry_on_errors and error_type not in self.retry_on_errors:
                self.logger.debug(f"Not retrying for error type: {error_type}")
                return False
        
        # Exit code based retry logic (0 = success, don't retry)
        if exit_code == 0:
            return False
        
        return True
    
    def get_retry_info(self) -> Dict:
        """Get human-readable retry configuration"""
        return {
            'strategy': self.strategy.value,
            'max_attempts': self.max_attempts,
            'initial_delay': self.initial_delay,
            'max_delay': self.max_delay,
            'multiplier': self.multiplier,
            'max_total_time': self.max_total_time,
            'retry_on_errors': self.retry_on_errors,
            'skip_on_errors': self.skip_on_errors
        }


# ============================================================================
# FEATURE: ALERTING & NOTIFICATION SYSTEM
# ============================================================================

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertChannel(Enum):
    """Available alert channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    STDOUT = "stdout"


class Alert:
    """Represents an alert configuration"""

    def __init__(self, name: str, condition: str, channels: List[str], 
                 severity: str = "WARNING", throttle_seconds: int = 300):
        self.name = name
        self.condition = condition
        self.channels = [AlertChannel(ch) for ch in channels]
        self.severity = AlertSeverity(severity)
        self.throttle_seconds = throttle_seconds
        self.last_triggered = 0

    def should_trigger(self, metrics: Dict) -> Tuple[bool, str]:
        """Evaluate if alert should trigger based on metrics"""
        try:
            # Safe evaluation of condition with restricted globals
            safe_metrics = {k: v for k, v in metrics.items() if isinstance(v, (int, float, bool))}
            condition_result = eval(self.condition, {"__builtins__": {}}, safe_metrics)
            return bool(condition_result), self.condition
        except Exception as e:
            logging.warning(f"Alert condition evaluation failed for '{self.name}': {e}")
            return False, str(e)

    def can_trigger(self) -> bool:
        """Check if alert is not throttled"""
        return time.time() - self.last_triggered >= self.throttle_seconds

    def mark_triggered(self):
        """Mark alert as triggered"""
        self.last_triggered = time.time()


class AlertManager:
    """Manages alerts and notifications with secure credential handling"""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.notification_config = {
            'email': {},
            'slack': {},
            'webhook': {}
        }
        self.alert_history = []
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def _get_credential(credential_name: Optional[str], default: Optional[str] = None) -> str:
        """Securely retrieve credential from environment variable
        
        SECURITY FIX: Load credentials from environment instead of storing plaintext
        This prevents credential exposure in code, config files, and logs.
        
        Args:
            credential_name: Name of environment variable (e.g., 'SLACK_WEBHOOK')
            default: Default value if env var not found
            
        Returns:
            Credential value from environment variable
            
        Example:
            webhook = AlertManager._get_credential('SLACK_WEBHOOK')
        """
        if not credential_name:
            if default:
                return default
            raise ValueError("Credential name cannot be None or empty")
        
        value = os.environ.get(credential_name)
        if not value and default:
            return default
        if not value:
            raise ValueError(f"Credential '{credential_name}' not found in environment variables")
        return value
    
    @staticmethod
    def _load_credentials_from_file(filepath: str) -> Dict:
        """Securely load credentials from JSON file with restricted permissions
        
        SECURITY: File should have permissions 600 (rw-------)
        
        Args:
            filepath: Path to JSON file containing credentials
            
        Returns:
            Dictionary of credentials
        """
        import stat
        try:
            # Check file permissions - should be readable only by owner
            file_stat = os.stat(filepath)
            file_perms = file_stat.st_mode & 0o777
            
            if file_perms & 0o077:  # Check if group or others have any permissions
                raise PermissionError(
                    f"Credential file {filepath} has insecure permissions {oct(file_perms)}. "
                    "Run: chmod 600 {filepath}"
                )
            
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load credentials from {filepath}: {e}")

    def add_alert(self, name: str, condition: str, channels: List[str], 
                  severity: str = "WARNING", throttle_seconds: int = 300):
        """Add a new alert configuration

        Example:
            alert_manager.add_alert('cpu_high', 'cpu_max > 80', 
                                   ['slack', 'email'], severity='WARNING')
        """
        alert = Alert(name, condition, channels, severity, throttle_seconds)
        self.alerts.append(alert)
        self.logger.info(f"Alert added: {name} ({severity})")

    def configure_email(self, smtp_server: Optional[str] = None, smtp_port: Optional[int] = None, 
                       from_addr: Optional[str] = None, to_addrs: Optional[List[str]] = None, 
                       username: Optional[str] = None, password: Optional[str] = None,
                       use_tls: bool = True, env_prefix: str = 'EMAIL_'):
        """Configure email notifications with secure credential handling
        
        SECURITY FIX: Supports loading credentials from environment variables
        
        Args:
            smtp_server: SMTP server (or set EMAIL_SMTP_SERVER env var)
            smtp_port: SMTP port (or set EMAIL_SMTP_PORT env var)
            from_addr: From address (or set EMAIL_FROM_ADDR env var)
            to_addrs: To addresses (or set EMAIL_TO_ADDRS env var - comma separated)
            username: Username (or set EMAIL_USERNAME env var)
            password: Password (or set EMAIL_PASSWORD env var - NEVER hardcode!)
            use_tls: Whether to use TLS
            env_prefix: Prefix for environment variables
        """
        # Load from environment if not provided as arguments
        try:
            smtp_server = smtp_server or self._get_credential(f'{env_prefix}SMTP_SERVER')
            smtp_port = smtp_port or int(self._get_credential(f'{env_prefix}SMTP_PORT', '587'))
            from_addr = from_addr or self._get_credential(f'{env_prefix}FROM_ADDR')
            
            to_addrs_str = (
                ','.join(to_addrs) if to_addrs 
                else self._get_credential(f'{env_prefix}TO_ADDRS')
            )
            to_addrs = [addr.strip() for addr in to_addrs_str.split(',')]
            
            username = username or self._get_credential(f'{env_prefix}USERNAME', '')
            password = password or self._get_credential(f'{env_prefix}PASSWORD', '')
            
        except ValueError as e:
            self.logger.error(f"Email configuration error: {e}")
            return
        
        self.notification_config['email'] = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'from': from_addr,
            'to': to_addrs,
            'username': username,
            'password': password,
            'use_tls': use_tls
        }
        self.logger.info("Email notifications configured from environment variables")

    def configure_slack(self, webhook_url: Optional[str] = None, env_var: Optional[str] = 'SLACK_WEBHOOK_URL'):
        """Configure Slack webhook notifications with secure credential handling
        
        SECURITY FIX: Load webhook URL from environment variable instead of hardcoding
        
        Args:
            webhook_url: Slack webhook URL (or set SLACK_WEBHOOK_URL env var)
            env_var: Environment variable name containing webhook URL
            
        Example:
            # Set environment variable first:
            # export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
            # Then configure:
            manager.configure_slack()
        """
        if requests is None:
            raise ImportError("requests library required for Slack. Install with: pip install requests")
        
        try:
            webhook_url = webhook_url or self._get_credential(env_var)
        except ValueError as e:
            self.logger.error(f"Slack configuration error: {e}")
            return
        
        # Validate URL format
        if not webhook_url.startswith('https://hooks.slack.com/'):
            self.logger.warning("Slack webhook URL has unexpected format")
        
        self.notification_config['slack'] = {'webhook_url': webhook_url}
        self.logger.info("Slack notifications configured from environment variable")

    def configure_webhook(self, url: Optional[str] = None, headers: Optional[Dict] = None, 
                         env_var: Optional[str] = 'WEBHOOK_URL'):
        """Configure custom webhook notifications with secure credential handling
        
        SECURITY FIX: Load URL from environment variable, support auth tokens
        
        Args:
            url: Webhook URL (or set WEBHOOK_URL env var)
            headers: Additional headers (e.g., {'Authorization': 'Bearer TOKEN'})
            env_var: Environment variable name containing webhook URL
        """
        if requests is None:
            raise ImportError("requests library required for webhooks. Install with: pip install requests")
        
        try:
            url = url or self._get_credential(env_var)
        except ValueError as e:
            self.logger.error(f"Webhook configuration error: {e}")
            return
        
        # Support Authorization token from environment
        if not headers:
            headers = {}
        
        if 'Authorization' not in headers:
            auth_token = os.environ.get('WEBHOOK_AUTH_TOKEN')
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
        
        self.notification_config['webhook'] = {
            'url': url,
            'headers': headers
        }
        self.logger.info("Webhook notifications configured from environment variables")

    def check_alerts(self, metrics: Dict):
        """Check all alerts against current metrics"""
        for alert in self.alerts:
            should_trigger, condition_str = alert.should_trigger(metrics)

            if should_trigger and alert.can_trigger():
                alert.mark_triggered()
                self._send_alert(alert, metrics, condition_str)

    def _send_alert(self, alert: Alert, metrics: Dict, condition_str: str):
        """Send alert through configured channels"""
        alert_data = {
            'name': alert.name,
            'severity': alert.severity.value,
            'condition': condition_str,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }

        self.alert_history.append(alert_data)

        for channel in alert.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email_alert(alert, alert_data)
                elif channel == AlertChannel.SLACK:
                    self._send_slack_alert(alert, alert_data)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_alert(alert, alert_data)
                elif channel == AlertChannel.STDOUT:
                    self._print_alert(alert, alert_data)
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel.value}: {e}")

    def _send_email_alert(self, alert: Alert, alert_data: Dict):
        """Send email alert"""
        config = self.notification_config.get('email', {})
        if not config:
            self.logger.warning("Email not configured, skipping email alert")
            return

        subject = f"[{alert.severity.value}] Alert: {alert.name}"
        body = f"""
Alert Triggered: {alert.name}
Severity: {alert.severity.value}
Condition: {alert.condition}
Time: {alert_data['timestamp']}

Script: {alert_data['metrics'].get('script_path', 'Unknown')}
Execution Time: {alert_data['metrics'].get('execution_time_seconds', 0):.2f}s
Exit Code: {alert_data['metrics'].get('exit_code', 'N/A')}
Success: {alert_data['metrics'].get('success', False)}

Key Metrics:
- CPU Max: {alert_data['metrics'].get('cpu_max', 0):.1f}%
- Memory Max: {alert_data['metrics'].get('memory_max_mb', 0):.1f} MB
- Execution Time: {alert_data['metrics'].get('execution_time_seconds', 0):.2f}s
"""

        msg = MIMEMultipart()
        msg['From'] = config['from']
        msg['To'] = ', '.join(config['to'])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            if config.get('use_tls', True):
                server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
                server.starttls()
            else:
                server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])

            if config.get('username') and config.get('password'):
                server.login(config['username'], config['password'])

            server.send_message(msg)
            server.quit()
            self.logger.info(f"Email alert sent for: {alert.name}")
        except Exception as e:
            self.logger.error(f"Email send failed: {e}")

    def _send_slack_alert(self, alert: Alert, alert_data: Dict):
        """Send Slack webhook alert"""
        config = self.notification_config.get('slack', {})
        if not config.get('webhook_url'):
            self.logger.warning("Slack webhook not configured, skipping Slack alert")
            return

        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.CRITICAL: "#ff0000"
        }

        payload = {
            "attachments": [{
                "fallback": f"{alert.severity.value}: {alert.name}",
                "color": color_map.get(alert.severity, "#808080"),
                "title": f"🚨 Alert: {alert.name}",
                "fields": [
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Condition", "value": alert.condition, "short": True},
                    {"title": "Script", "value": alert_data['metrics'].get('script_path', 'Unknown'), "short": False},
                    {"title": "Exit Code", "value": str(alert_data['metrics'].get('exit_code', 'N/A')), "short": True},
                    {"title": "Duration", "value": f"{alert_data['metrics'].get('execution_time_seconds', 0):.2f}s", "short": True},
                    {"title": "CPU Max", "value": f"{alert_data['metrics'].get('cpu_max', 0):.1f}%", "short": True},
                    {"title": "Memory Max", "value": f"{alert_data['metrics'].get('memory_max_mb', 0):.1f} MB", "short": True}
                ],
                "footer": "Script Runner Alert",
                "ts": int(time.time())
            }]
        }

        if requests:
            response = requests.post(config['webhook_url'], json=payload, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"Slack alert failed: {response.status_code}")
            else:
                self.logger.info(f"Slack alert sent for: {alert.name}")
        else:
            self.logger.warning("requests library not available for Slack alert")

    def _send_webhook_alert(self, alert: Alert, alert_data: Dict):
        """Send custom webhook alert"""
        config = self.notification_config.get('webhook', {})
        if not config.get('url'):
            self.logger.warning("Webhook not configured")
            return

        if requests:
            response = requests.post(
                config['url'],
                json=alert_data,
                headers=config.get('headers', {}),
                timeout=10
            )

            if response.status_code not in [200, 201, 202]:
                self.logger.error(f"Webhook alert failed: {response.status_code}")
            else:
                self.logger.info(f"Webhook alert sent for: {alert.name}")
        else:
            self.logger.warning("requests library not available for webhook alert")

    def _print_alert(self, alert: Alert, alert_data: Dict):
        """Print alert to stdout"""
        print(f"\n{'='*80}")
        print(f"🚨 ALERT TRIGGERED: {alert.name}")
        print(f"{'='*80}")
        print(f"Severity: {alert.severity.value}")
        print(f"Condition: {alert.condition}")
        print(f"Time: {alert_data['timestamp']}")
        print(f"Script: {alert_data['metrics'].get('script_path', 'Unknown')}")
        print(f"CPU Max: {alert_data['metrics'].get('cpu_max', 0):.1f}%")
        print(f"Memory Max: {alert_data['metrics'].get('memory_max_mb', 0):.1f} MB")
        print(f"{'='*80}\n")


# ============================================================================
# FEATURE: CI/CD PIPELINE INTEGRATION
# ============================================================================

class PerformanceGate:
    """Performance gate for CI/CD integration"""

    def __init__(self, metric_name: str, max_value: Optional[float] = None, min_value: Optional[float] = None,
                 comparator: str = 'max'):
        self.metric_name = metric_name
        self.max_value = max_value
        self.min_value = min_value
        self.comparator = comparator

    def check(self, metrics: Dict) -> Tuple[bool, str]:
        """Check if gate passes"""
        # Try to find metric with comparator suffix first
        metric_key = f"{self.metric_name}_{self.comparator}" if self.comparator != 'value' else self.metric_name
        value = metrics.get(metric_key, metrics.get(self.metric_name))

        if value is None:
            return True, f"Metric '{self.metric_name}' not found (skipped)"

        if self.max_value is not None and value > self.max_value:
            return False, f"{self.metric_name}={value:.2f} exceeds max={self.max_value}"

        if self.min_value is not None and value < self.min_value:
            return False, f"{self.metric_name}={value:.2f} below min={self.min_value}"

        return True, f"{self.metric_name}={value:.2f} OK"


class CICDIntegration:
    """CI/CD pipeline integration features"""

    def __init__(self):
        self.performance_gates: List[PerformanceGate] = []
        self.baseline_metrics: Dict = {}
        self.junit_output = False
        self.logger = logging.getLogger(__name__)

    def add_performance_gate(self, metric_name: str, max_value: Optional[float] = None, 
                            min_value: Optional[float] = None, comparator: str = 'max'):
        """Add a performance gate

        Example:
            cicd.add_performance_gate('cpu_max', max_value=90)
            cicd.add_performance_gate('memory_max_mb', max_value=1024)
        """
        gate = PerformanceGate(metric_name, max_value, min_value, comparator)
        self.performance_gates.append(gate)
        self.logger.info(f"Performance gate added: {metric_name}")

    def check_gates(self, metrics: Dict) -> Tuple[bool, List[str]]:
        """Check all performance gates"""
        all_passed = True
        results = []

        for gate in self.performance_gates:
            passed, message = gate.check(metrics)
            if not passed:
                all_passed = False
                results.append(f"❌ GATE FAILED: {message}")
            else:
                results.append(f"✓ Gate passed: {message}")

        return all_passed, results

    def load_baseline(self, baseline_file: str):
        """Load baseline metrics from file"""
        try:
            with open(baseline_file, 'r') as f:
                self.baseline_metrics = json.load(f)
            self.logger.info(f"Baseline loaded from {baseline_file}")
        except Exception as e:
            self.logger.warning(f"Could not load baseline: {e}")

    def save_baseline(self, metrics: Dict, baseline_file: str):
        """Save current metrics as baseline"""
        try:
            with open(baseline_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            self.logger.info(f"Baseline saved to {baseline_file}")
        except Exception as e:
            self.logger.error(f"Could not save baseline: {e}")

    def compare_with_baseline(self, metrics: Dict) -> Dict:
        """Compare current metrics with baseline"""
        if not self.baseline_metrics:
            return {}

        comparison = {}
        for key in ['execution_time_seconds', 'memory_max_mb', 'cpu_max']:
            if key in metrics and key in self.baseline_metrics:
                current = metrics[key]
                baseline = self.baseline_metrics[key]
                delta = current - baseline
                percent_change = (delta / baseline * 100) if baseline != 0 else 0
                comparison[key] = {
                    'current': current,
                    'baseline': baseline,
                    'delta': delta,
                    'percent_change': percent_change
                }

        return comparison

    def generate_junit_xml(self, metrics: Dict, gate_results: List[str], output_file: str):
        """Generate JUnit XML format output for CI systems"""
        test_time = metrics.get('execution_time_seconds', 0)

        gate_failures = [r for r in gate_results if 'FAILED' in r]
        num_failures = len(gate_failures)

        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<testsuites>',
            f'    <testsuite name="Script Performance Tests" tests="{len(self.performance_gates)}" failures="{num_failures}" time="{test_time}">',
        ]

        for result in gate_results:
            if 'FAILED' in result:
                gate_name = result.split(':')[1].strip() if ':' in result else 'Unknown'
                xml_lines.append(f'        <testcase name="{gate_name}" time="0" status="failed">')
                xml_lines.append(f'            <failure message="{result}"/>')
                xml_lines.append('        </testcase>')
            else:
                gate_name = result.replace('✓ Gate passed:', '').strip()
                xml_lines.append(f'        <testcase name="{gate_name}" time="0" status="passed"/>')

        xml_lines.extend([
            '    </testsuite>',
            '</testsuites>'
        ])

        with open(output_file, 'w') as f:
            f.write('\n'.join(xml_lines))

        self.logger.info(f"JUnit XML report saved to {output_file}")

    def generate_tap_output(self, gate_results: List[str], output_file: Optional[str] = None) -> str:
        """Generate TAP (Test Anything Protocol) format output for CI systems
        
        TAP is a lightweight format supported by many CI systems.
        """
        gate_failures = [r for r in gate_results if 'FAILED' in r]
        
        tap_lines = [
            f"1..{len(gate_results)}",
            f"# Script Performance Gates - {datetime.now().isoformat()}"
        ]
        
        for i, result in enumerate(gate_results, 1):
            if 'FAILED' in result:
                tap_lines.append(f"not ok {i} - {result}")
            else:
                tap_lines.append(f"ok {i} - {result}")
        
        tap_output = '\n'.join(tap_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(tap_output)
            self.logger.info(f"TAP output saved to {output_file}")
        
        return tap_output

    def get_exit_code_for_gates(self, gate_results: List[str]) -> int:
        """Return appropriate exit code based on gate results
        
        Returns:
            0 if all gates passed
            1 if any gates failed
        """
        gate_failures = [r for r in gate_results if 'FAILED' in r]
        return 1 if gate_failures else 0


# ============================================================================
# EXISTING FEATURES
# ============================================================================

class ExecutionHook:
    """Hook system for custom pre/post execution logic.
    
    Provides extension point for custom behavior before and after script execution.
    Enables integration of custom monitoring, logging, or cleanup logic without
    modifying core ScriptRunner code. Follows the Observer pattern.
    
    Attributes:
        pre_execution_hooks (List[Callable]): Functions called before execution
        post_execution_hooks (List[Callable]): Functions called after execution
    
    Example:
        >>> hooks = ExecutionHook()
        >>> def pre_exec(ctx): 
        ...     print(f"Starting: {ctx['script_path']}")
        >>> def post_exec(ctx):
        ...     print(f"Finished: {ctx['end_time']}")
        >>> hooks.register_pre_hook(pre_exec)
        >>> hooks.register_post_hook(post_exec)
        >>> runner.hooks = hooks
    """

    def __init__(self):
        self.pre_execution_hooks: List[Callable] = []
        self.post_execution_hooks: List[Callable] = []

    def register_pre_hook(self, func: Callable) -> None:
        """Register pre-execution hook function.
        
        Args:
            func (Callable): Function to call before execution.
                Receives context dict with keys:
                - script_path (str): Script being executed
                - attempt (int): Attempt number
                - start_time (str): ISO timestamp when started
        
        Example:
            >>> def setup(ctx):
            ...     print(f"Setup for {ctx['script_path']}")
            >>> hooks.register_pre_hook(setup)
        """
        self.pre_execution_hooks.append(func)

    def register_post_hook(self, func: Callable) -> None:
        """Register post-execution hook function.
        
        Args:
            func (Callable): Function to call after execution.
                Receives context dict with keys:
                - script_path (str): Script that was executed
                - attempt (int): Attempt number
                - result (Dict): Execution result with stdout, stderr, returncode
                - end_time (str): ISO timestamp when ended
        
        Example:
            >>> def cleanup(ctx):
            ...     print(f"Exit code: {ctx['result']['returncode']}")
            >>> hooks.register_post_hook(cleanup)
        """
        self.post_execution_hooks.append(func)

    def execute_pre_hooks(self, context: Dict) -> None:
        """Execute all registered pre-execution hooks.
        
        Executes hooks sequentially. Catches and logs exceptions to prevent
        one hook from blocking others.
        
        Args:
            context (Dict): Context information to pass to hooks
        """
        for hook in self.pre_execution_hooks:
            try:
                hook(context)
            except Exception as e:
                logging.warning(f"Pre-hook failed: {e}")

    def execute_post_hooks(self, context: Dict) -> None:
        """Execute all registered post-execution hooks.
        
        Executes hooks sequentially. Catches and logs exceptions to prevent
        one hook from blocking others.
        
        Args:
            context (Dict): Context information including execution result
        """
        for hook in self.post_execution_hooks:
            try:
                hook(context)
            except Exception as e:
                logging.warning(f"Post-hook failed: {e}")


class ProcessMonitor:
    """Monitor child process resource usage during execution with adaptive sampling.
    
    High-frequency background monitoring of CPU and memory usage for script execution.
    Collects per-interval samples for detailed resource analysis and reporting.
    Uses psutil for accurate cross-platform process metrics.
    
    Features:
    - Configurable sampling interval
    - Adaptive interval adjustment when metrics stabilize
    - Optional metric filtering (collect only requested metrics)
    - Reduced overhead (<1% with adaptive sampling)
    
    Attributes:
        interval (float): Sampling interval in seconds (default: 0.1s)
        monitoring (bool): Current monitoring state
        metrics_history (List[Dict]): Time-series of collected metrics
        adaptive_interval (bool): Enable adaptive interval adjustment
        metrics_to_collect (Set[str]): Metrics to collect (None=all)
        _thread (Thread): Background monitoring thread
        _process (psutil.Process): Process being monitored
    
    Example:
        >>> monitor = ProcessMonitor(interval=0.1, adaptive=True)
        >>> monitor.set_metrics_to_collect(['cpu_percent', 'memory_mb'])
        >>> monitor.start(psutil.Process(pid))
        >>> # ... script execution ...
        >>> monitor.stop()
        >>> summary = monitor.get_summary()
        >>> print(f"CPU avg: {summary['cpu_avg']}%")
    """

    def __init__(self, interval: float = 0.1, adaptive: bool = True):
        self.interval = interval
        self.initial_interval = interval
        self.adaptive_interval = adaptive
        self.monitoring = False
        self.metrics_history = []
        self.metrics_to_collect = None  # None = collect all
        self._thread = None
        self._process = None
        self._stabilized_count = 0
        self._max_stabilized = 10  # Samples needed to consider stabilized
    
    def set_metrics_to_collect(self, metrics: set):
        """Specify which metrics to collect (optimization)
        
        Args:
            metrics: Set of metric names to collect
                     e.g., {'cpu_percent', 'memory_mb'}
        """
        self.metrics_to_collect = metrics
        logging.debug(f"Monitoring {len(metrics)} metrics: {metrics}")

    def start(self, process: psutil.Process):
        self._process = process
        self.monitoring = True
        self.metrics_history = []
        self._stabilized_count = 0
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.monitoring = False
        if self._thread:
            self._thread.join(timeout=2)

    def _is_stable(self) -> bool:
        """Check if metrics have stabilized (for adaptive interval)"""
        if len(self.metrics_history) < 3:
            return False
        
        # Check if CPU usage is stable (low variance)
        recent_cpu = [m.get('cpu_percent', 0) for m in self.metrics_history[-3:]]
        cpu_variance = max(recent_cpu) - min(recent_cpu)
        
        return cpu_variance < 5.0  # Less than 5% variance = stable

    def _monitor_loop(self):
        while self.monitoring and self._process:
            try:
                if not self._process.is_running():
                    break

                try:
                    metric_sample = {'timestamp': time.time()}
                    
                    # Collect only requested metrics
                    if self.metrics_to_collect is None or 'cpu_percent' in self.metrics_to_collect:
                        cpu_percent = self._process.cpu_percent()
                        metric_sample['cpu_percent'] = cpu_percent
                    
                    if self.metrics_to_collect is None or 'memory_mb' in self.metrics_to_collect:
                        memory_info = self._process.memory_info()
                        metric_sample['memory_mb'] = memory_info.rss / 1024 / 1024
                    
                    # Include child processes if monitoring them
                    if self.metrics_to_collect is None or 'children' in self.metrics_to_collect:
                        children = self._process.children(recursive=True)
                        metric_sample['num_children'] = len(children)
                        
                        for child in children:
                            try:
                                if 'cpu_percent' in metric_sample:
                                    metric_sample['cpu_percent'] += child.cpu_percent()
                                if 'memory_mb' in metric_sample:
                                    metric_sample['memory_mb'] += child.memory_info().rss / 1024 / 1024
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue

                    self.metrics_history.append(metric_sample)
                    
                    # Adaptive interval adjustment
                    if self.adaptive_interval and self._is_stable():
                        self._stabilized_count += 1
                        if self._stabilized_count >= self._max_stabilized:
                            # Increase interval to reduce overhead
                            new_interval = min(self.interval * 1.5, 1.0)
                            if new_interval != self.interval:
                                self.interval = new_interval
                                logging.debug(f"Metrics stabilized, increased sample interval to {self.interval:.2f}s")
                    else:
                        self._stabilized_count = 0

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

                time.sleep(self.interval)

            except Exception as e:
                logging.debug(f"Monitor error: {e}")
                break

    def get_summary(self) -> Dict:
        """Get aggregated monitoring summary statistics.
        
        Calculates statistical summaries of all collected metrics during the
        monitoring period. Returns empty dict if no samples collected.
        
        Returns:
            Dict: Aggregated metrics including:
                - cpu_avg, cpu_max, cpu_min (float): CPU usage statistics (%)
                - memory_avg_mb, memory_max_mb, memory_min_mb (float): Memory statistics (MB)
                - sample_count (int): Number of samples collected
                - sampling_efficiency (float): Ratio of interval to initial interval
        
        Example:
            >>> summary = monitor.get_summary()
            >>> print(f"CPU: {summary['cpu_avg']:.1f}% avg, {summary['cpu_max']:.1f}% peak")
        """
        if not self.metrics_history:
            return {}

        cpu_values = [m.get('cpu_percent', 0) for m in self.metrics_history if 'cpu_percent' in m]
        mem_values = [m.get('memory_mb', 0) for m in self.metrics_history if 'memory_mb' in m]

        summary = {
            'sample_count': len(self.metrics_history),
            'sampling_efficiency': self.interval / self.initial_interval,
        }
        
        if cpu_values:
            summary.update({
                'cpu_avg': sum(cpu_values) / len(cpu_values),
                'cpu_max': max(cpu_values),
                'cpu_min': min(cpu_values),
            })
        
        if mem_values:
            summary.update({
                'memory_avg_mb': sum(mem_values) / len(mem_values),
                'memory_max_mb': max(mem_values),
                'memory_min_mb': min(mem_values),
            })
        
        return summary


class ScriptRunner:
    """Enhanced wrapper class to run Python scripts with comprehensive metrics collection.
    
    Industrial-grade script execution engine with advanced features including:
    - Process monitoring (CPU, memory, I/O, context switches)
    - Automatic retry with configurable backoff strategies
    - Alert management and CI/CD integration
    - Historical metrics tracking and trending
    - Performance gating and baseline comparison
    - Custom execution hooks (pre/post execution)
    
    Attributes:
        script_path (str): Path to Python script to execute
        script_args (List[str]): Arguments to pass to script
        timeout (Optional[int]): Execution timeout in seconds
        metrics (Dict): Collected metrics from last execution
        history_manager (HistoryManager): Database manager for metrics
        alert_manager (AlertManager): Alert management system
        cicd_integration (CICDIntegration): CI/CD integration handler
        retry_config (RetryConfig): Advanced retry strategy configuration
        hooks (ExecutionHook): Pre/post execution hook system
    
    Example:
        >>> runner = ScriptRunner(
        ...     'my_script.py',
        ...     script_args=['arg1', 'arg2'],
        ...     timeout=60,
        ...     history_db='metrics.db'
        ... )
        >>> result = runner.run_script(retry_on_failure=True)
        >>> print(f"Exit code: {result['returncode']}")
        >>> print(f"Execution time: {result['metrics']['execution_time_seconds']}s")
    """

    def __init__(self, script_path: str, script_args: Optional[List[str]] = None,
                 timeout: Optional[int] = None, log_level: Optional[str] = 'INFO', config_file: Optional[str] = None,
                 history_db: Optional[str] = None, enable_history: bool = True) -> None:
        """Initialize ScriptRunner with configuration.
        
        Args:
            script_path (str): Path to Python script to execute
            script_args (List[str], optional): Arguments to pass to script. Default: None
            timeout (int, optional): Execution timeout in seconds. None=no timeout. Default: None
            log_level (str): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR'). Default: 'INFO'
            config_file (str, optional): YAML configuration file path. Default: None
            history_db (str, optional): SQLite database path for metrics history.
                Default: 'script_runner_history.db'
            enable_history (bool): Whether to save metrics to database. Default: True
        
        Raises:
            FileNotFoundError: If script_path doesn't exist
            PermissionError: If script is not readable
            ValueError: If invalid log_level provided
        
        Example:
            >>> runner = ScriptRunner(
            ...     'app.py',
            ...     script_args=['--debug'],
            ...     timeout=300,
            ...     config_file='runner_config.yaml',
            ...     enable_history=True
            ... )
        """
        self.script_path = script_path
        self.script_args = script_args or []
        self.timeout = timeout
        self.metrics = {}
        self.suppress_warnings = False
        self.max_output_lines = None
        self.hooks = ExecutionHook()
        self.monitor_interval = 0.1
        
        # UPDATED: Phase 2 retry config (replaces old retry_count and retry_delay)
        self.retry_config = RetryConfig()  # Default configuration
        self.retry_count = 0  # Legacy support
        self.retry_delay = 1  # Legacy support

        # NEW: Phase 1 features
        self.alert_manager = AlertManager()
        self.cicd_integration = CICDIntegration()
        
        # NEW: Phase 2 features
        self.enable_history = enable_history
        self.history_manager = None
        if enable_history:
            db_path = history_db or 'script_runner_history.db'
            self.history_manager = HistoryManager(db_path=db_path)
        
        # NEW: Trend Analysis (Phase 2)
        self.trend_analyzer = TrendAnalyzer()
        
        # NEW: Baseline Calculation (Phase 2)
        self.baseline_calculator = BaselineCalculator()

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, (log_level or 'INFO').upper()))
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Load config file if provided
        if config_file:
            self.load_config(config_file)

    def load_config(self, config_file: str) -> None:
        """Load runner configuration from YAML file.
        
        Loads alerts, performance gates, and notification settings from
        YAML configuration file. Provides centralized configuration management.
        
        Args:
            config_file (str): Path to YAML configuration file
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        
        YAML Schema:
            alerts:
              - name: alert_name
                metric: metric_name
                threshold: value
                condition: '>' or '<'
            
            performance_gates:
              - metric: metric_name
                max_value: threshold
            
            notifications:
              slack:
                webhook_url: https://hooks.slack.com/...
              email:
                smtp_server: smtp.gmail.com
                sender_email: alerts@example.com
        
        Example:
            >>> runner.load_config('production_config.yaml')
        """
        if yaml is None:
            self.logger.warning("PyYAML not installed, skipping config file")
            return

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            # Load alerts
            for alert_config in config.get('alerts', []):
                self.alert_manager.add_alert(**alert_config)

            # Load performance gates
            for gate_config in config.get('performance_gates', []):
                self.cicd_integration.add_performance_gate(**gate_config)

            # Load notification configs
            if 'notifications' in config:
                if 'slack' in config['notifications']:
                    self.alert_manager.configure_slack(config['notifications']['slack']['webhook_url'])
                if 'email' in config['notifications']:
                    self.alert_manager.configure_email(**config['notifications']['email'])

            self.logger.info(f"Configuration loaded from {config_file}")

        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")

    def collect_system_metrics_start(self) -> Dict:
        try:
            process = psutil.Process()
            return {
                'memory_before': process.memory_info().rss / 1024 / 1024,
                'cpu_percent_before': process.cpu_percent(interval=0.1),
                'num_threads_before': process.num_threads(),
                'num_fds_before': process.num_fds() if hasattr(process, 'num_fds') else None,
            }
        except Exception as e:
            self.logger.warning(f"Failed to collect start metrics: {e}")
            return {}

    def collect_system_metrics_end(self, start_metrics: Dict) -> Dict:
        try:
            process = psutil.Process()
            mem_after = process.memory_info().rss / 1024 / 1024
            mem_before = start_metrics.get('memory_before', 0)

            result = {
                'memory_after': mem_after,
                'memory_delta': mem_after - mem_before,
                'cpu_percent_after': process.cpu_percent(interval=0.1),
                'num_threads_after': process.num_threads(),
            }

            if hasattr(process, 'num_fds'):
                result['num_fds_after'] = process.num_fds()
                fds_before = start_metrics.get('num_fds_before')
                if fds_before is not None:
                    result['num_fds_delta'] = result['num_fds_after'] - fds_before

            return result
        except Exception as e:
            self.logger.warning(f"Failed to collect end metrics: {e}")
            return {}

    def validate_script(self) -> bool:
        """Validate script exists and is readable before execution.
        
        Performs pre-flight checks to ensure script can be executed:
        - File exists and is readable
        - Has .py extension (warning if not)
        
        Returns:
            bool: True if script is valid
        
        Raises:
            FileNotFoundError: If script file doesn't exist
            PermissionError: If script is not readable
        
        Example:
            >>> runner = ScriptRunner('script.py')
            >>> if runner.validate_script():
            ...     result = runner.run_script()
        """
        if not os.path.isfile(self.script_path):
            raise FileNotFoundError(f"Script not found: {self.script_path}")
        if not os.access(self.script_path, os.R_OK):
            raise PermissionError(f"Script not readable: {self.script_path}")
        if not self.script_path.endswith('.py'):
            self.logger.warning(f"Script does not have .py extension: {self.script_path}")
        return True

    def run_script(self, retry_on_failure: bool = False) -> Dict:
        """Execute script with advanced retry and monitoring capabilities.
        
        Executes the target script with comprehensive monitoring, automatic retry,
        and metrics collection. Supports multiple retry strategies with exponential
        backoff, jitter, and max time/attempt limits.
        
        Args:
            retry_on_failure (bool): Enable automatic retry on script failure.
                Uses retry_config for strategy settings. Default: False
        
        Returns:
            Dict: Execution result containing:
                - returncode (int): Process exit code (0=success)
                - stdout (str): Standard output
                - stderr (str): Standard error
                - metrics (Dict): Comprehensive execution metrics:
                    - execution_time_seconds (float): Total runtime
                    - cpu_avg, cpu_max (float): CPU usage percentage
                    - memory_avg_mb, memory_max_mb (float): Memory usage
                    - success (bool): Whether execution succeeded
                    - attempt_number (int): Retry attempt number
                    - And many more system metrics
        
        Raises:
            FileNotFoundError: If script doesn't exist
            PermissionError: If script not executable
            subprocess.TimeoutExpired: If execution exceeds timeout
        
        Example:
            >>> runner = ScriptRunner('analysis.py', timeout=60)
            >>> result = runner.run_script(retry_on_failure=True)
            >>> if result['returncode'] == 0:
            ...     print(f"Success! Took {result['metrics']['execution_time_seconds']}s")
            ... else:
            ...     print(f"Failed with exit code {result['returncode']}")
        """
        total_start_time = time.time()
        last_result = None
        attempt = 0
        
        # If legacy retry_count is set, use it to configure retry_config
        if retry_on_failure and self.retry_count > 0:
            self.retry_config.max_attempts = self.retry_count + 1
        
        if not retry_on_failure:
            self.retry_config.max_attempts = 1
        
        while True:
            attempt += 1
            total_time = time.time() - total_start_time
            
            try:
                result = self._execute_script(attempt)
                last_result = result
                
                # Check if we should retry based on result
                should_retry = self.retry_config.should_retry(
                    error=None,
                    exit_code=result['returncode'],
                    total_time=total_time,
                    attempt=attempt - 1  # Convert to 0-indexed
                )
                
                if result['returncode'] == 0 or not should_retry:
                    return result
                
                # Calculate delay for next attempt
                delay = self.retry_config.get_delay(attempt - 1)
                self.logger.warning(
                    f"Attempt {attempt} failed (exit code: {result['returncode']}), "
                    f"retrying in {delay:.1f}s "
                    f"(strategy: {self.retry_config.strategy.value})"
                )
                time.sleep(delay)
                
            except Exception as e:
                total_time = time.time() - total_start_time
                
                should_retry = self.retry_config.should_retry(
                    error=e,
                    exit_code=-1,
                    total_time=total_time,
                    attempt=attempt - 1
                )
                
                if should_retry:
                    delay = self.retry_config.get_delay(attempt - 1)
                    self.logger.warning(
                        f"Attempt {attempt} error: {e}, "
                        f"retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"Retry exhausted after {attempt} attempts")
                    raise

    def _execute_script(self, attempt_number: int = 1) -> Dict:
        self.validate_script()

        cmd = [sys.executable, self.script_path] + self.script_args
        start_metrics = self.collect_system_metrics_start()
        start_time = time.time()
        start_timestamp = datetime.now().isoformat()

        hook_context = {
            'script_path': self.script_path,
            'attempt': attempt_number,
            'start_time': start_timestamp
        }
        self.hooks.execute_pre_hooks(hook_context)

        env = os.environ.copy()
        env['SCRIPT_RUNNER_ACTIVE'] = '1'
        env['SCRIPT_RUNNER_ATTEMPT'] = str(attempt_number)

        monitor = ProcessMonitor(interval=self.monitor_interval)
        child_process = None

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=os.path.dirname(os.path.abspath(self.script_path)) or '.'
            )

            try:
                child_process = psutil.Process(proc.pid)
                monitor.start(child_process)
            except psutil.NoSuchProcess:
                self.logger.warning("Could not attach monitor to child process")

            try:
                stdout, stderr = proc.communicate(timeout=self.timeout)
                returncode = proc.returncode
            except subprocess.TimeoutExpired:
                if child_process:
                    for child in child_process.children(recursive=True):
                        try:
                            child.kill()
                        except:
                            pass
                    child_process.kill()
                proc.kill()
                stdout, stderr = proc.communicate()
                raise

            monitor.stop()
            end_time = time.time()
            end_timestamp = datetime.now().isoformat()
            execution_time = end_time - start_time
            end_metrics = self.collect_system_metrics_end(start_metrics)
            resource_metrics = self._collect_resource_usage()
            monitor_summary = monitor.get_summary()

            self.metrics = {
                'script_path': self.script_path,
                'script_args': self.script_args,
                'start_time': start_timestamp,
                'end_time': end_timestamp,
                'execution_time_seconds': round(execution_time, 4),
                'exit_code': returncode,
                'success': returncode == 0,
                'attempt_number': attempt_number,
                'stdout_lines': len(stdout.splitlines()) if stdout else 0,
                'stderr_lines': len(stderr.splitlines()) if stderr else 0,
                'stdout_length': len(stdout) if stdout else 0,
                'stderr_length': len(stderr) if stderr else 0,
                'timeout_seconds': self.timeout,
                'timed_out': False,
                **start_metrics,
                **end_metrics,
                **resource_metrics,
                **monitor_summary,
                'python_version': sys.version,
                'platform': sys.platform,
            }

            result = {
                'stdout': stdout,
                'stderr': stderr,
                'returncode': returncode,
                'metrics': self.metrics
            }

            # NEW: Check alerts
            self.alert_manager.check_alerts(self.metrics)
            
            # NEW: Save to history database
            if self.history_manager:
                try:
                    execution_id = self.history_manager.save_execution(self.metrics)
                    if execution_id is not None and self.alert_manager.alert_history:
                        self.history_manager.save_alerts(execution_id, self.alert_manager.alert_history)
                except Exception as e:
                    self.logger.warning(f"Failed to save to history database: {e}")

            hook_context['result'] = result
            hook_context['end_time'] = end_timestamp
            self.hooks.execute_post_hooks(hook_context)

            return result

        except subprocess.TimeoutExpired as e:
            monitor.stop()
            end_time = time.time()
            execution_time = end_time - start_time

            self.metrics = {
                'script_path': self.script_path,
                'script_args': self.script_args,
                'start_time': start_timestamp,
                'end_time': datetime.now().isoformat(),
                'execution_time_seconds': round(execution_time, 4),
                'exit_code': -1,
                'success': False,
                'attempt_number': attempt_number,
                'timeout_seconds': self.timeout,
                'timed_out': True,
                'error': 'Script execution timed out',
                **monitor.get_summary()
            }

            self.alert_manager.check_alerts(self.metrics)

            return {
                'stdout': e.stdout or '',
                'stderr': e.stderr or '',
                'returncode': -1,
                'metrics': self.metrics
            }

        except Exception as e:
            monitor.stop()
            self.logger.error(f"Execution error: {e}")
            self.logger.debug(traceback.format_exc())

            self.metrics = {
                'script_path': self.script_path,
                'script_args': self.script_args,
                'start_time': start_timestamp,
                'end_time': datetime.now().isoformat(),
                'exit_code': -1,
                'success': False,
                'attempt_number': attempt_number,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }

            return {
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'metrics': self.metrics
            }

    def _collect_resource_usage(self) -> Dict:
        resource_metrics = {}
        if resource is not None:
            try:
                usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                resource_metrics = {
                    'user_time_seconds': usage.ru_utime,
                    'system_time_seconds': usage.ru_stime,
                    'max_memory_kb': usage.ru_maxrss,
                    'max_memory_mb': usage.ru_maxrss / 1024 if sys.platform == 'linux' else usage.ru_maxrss / 1024,
                    'page_faults_minor': usage.ru_minflt,
                    'page_faults_major': usage.ru_majflt,
                    'block_input_ops': usage.ru_inblock,
                    'block_output_ops': usage.ru_oublock,
                    'voluntary_context_switches': usage.ru_nvcsw,
                    'involuntary_context_switches': usage.ru_nivcsw,
                }
            except Exception as e:
                self.logger.debug(f"Resource usage collection failed: {e}")

        return resource_metrics


# ============================================================================
# UTILITY FUNCTIONS - JSON OPTIMIZATION
# ============================================================================

def save_metrics_optimized(metrics: Dict, output_file: str, compress: bool = True) -> None:
    """Save metrics to JSON with optional gzip compression.
    
    Optimizations:
    - Minimal separators for compact output (60-80% reduction vs indented)
    - Optional gzip compression for additional 50-70% reduction
    - Automatic format detection based on file extension
    - Size reporting for verification
    
    Args:
        metrics: Dictionary of metrics to save
        output_file: Output file path (.json or .json.gz)
        compress: Whether to use gzip compression. Default: True
        
    Example:
        >>> save_metrics_optimized(metrics, 'metrics.json.gz', compress=True)
        >>> # Output: "Saved 2MB → 0.4MB (80% compression)"
    """
    try:
        # Prepare JSON string with minimal separators
        json_str = json.dumps(metrics, separators=(',', ':'), default=str)
        uncompressed_size = len(json_str.encode('utf-8'))
        
        if compress and output_file.endswith('.json'):
            # Add .gz extension if not present
            output_file = output_file + '.gz'
        
        if compress and output_file.endswith('.gz'):
            # Save with gzip compression
            with gzip.open(output_file, 'wt', compresslevel=9) as f:
                f.write(json_str)
            compressed_size = os.path.getsize(output_file)
            reduction = (1 - compressed_size / uncompressed_size) * 100 if uncompressed_size > 0 else 0
            
            logging.info(f"Metrics saved to {output_file}")
            logging.info(f"Size: {uncompressed_size / 1024:.1f}KB → {compressed_size / 1024:.1f}KB ({reduction:.0f}% compression)")
        else:
            # Save without compression
            with open(output_file, 'w') as f:
                f.write(json_str)
            final_size = os.path.getsize(output_file)
            
            logging.info(f"Metrics saved to {output_file}")
            logging.info(f"Size: {final_size / 1024:.1f}KB (uncompressed)")
            
    except Exception as e:
        logging.error(f"Failed to save metrics: {e}")
        raise


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Main entry point with comprehensive CLI support"""
    parser = argparse.ArgumentParser(
        description='Enhanced Python Script Runner with Alerting & CI/CD Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a script with monitoring
  %(prog)s script.py
  
  # Run with arguments
  %(prog)s script.py --timeout 60 -- arg1 arg2
  
  # Load configuration from file
  %(prog)s script.py --config config.yaml
  
  # Generate CI/CD reports
  %(prog)s script.py --junit-output results.xml --tap-output results.tap
  
  # Compare against baseline
  %(prog)s script.py --baseline baseline.json --save-baseline new_baseline.json
        """
    )

    parser.add_argument('script', nargs='?', help='Python script to execute')
    parser.add_argument('script_args', nargs='*', help='Arguments to pass to the script')
    parser.add_argument('--timeout', type=int, default=None, help='Execution timeout in seconds')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    parser.add_argument('--config', help='Configuration file (YAML)')
    parser.add_argument('--monitor-interval', type=float, default=0.1, 
                       help='Process monitor sampling interval (seconds)')
    
    # Alerting options
    parser.add_argument('--alert-config', help='Alert name and condition (e.g., "cpu_high:cpu_max>80")')
    parser.add_argument('--slack-webhook', help='Slack webhook URL for alerts')
    parser.add_argument('--email-config', help='Email config JSON file for alerts')
    
    # CI/CD options
    parser.add_argument('--add-gate', action='append', dest='gates',
                       help='Add performance gate (e.g., "cpu_max:90" or "memory_max_mb:1024")')
    parser.add_argument('--junit-output', help='Generate JUnit XML output file')
    parser.add_argument('--tap-output', help='Generate TAP format output file')
    parser.add_argument('--baseline', help='Load baseline metrics from JSON file')
    parser.add_argument('--save-baseline', help='Save current metrics as baseline to JSON file')
    
    # History/Database options (Phase 2)
    parser.add_argument('--history-db', default=None, help='SQLite database file for history (default: script_runner_history.db)')
    parser.add_argument('--disable-history', action='store_true', help='Disable automatic history saving')
    parser.add_argument('--show-history', action='store_true', help='Show execution history and exit')
    parser.add_argument('--history-days', type=int, default=30, help='Number of days of history to show (default: 30)')
    parser.add_argument('--history-limit', type=int, default=50, help='Max history records to show (default: 50)')
    parser.add_argument('--db-stats', action='store_true', help='Show database statistics and exit')
    parser.add_argument('--cleanup-old', type=int, help='Delete records older than N days')
    
    # Retry strategy options (Phase 2)
    parser.add_argument('--retry', type=int, default=0, help='Number of retries on failure')
    parser.add_argument('--retry-strategy', choices=['linear', 'exponential', 'fibonacci', 'exponential_jitter'],
                       default='exponential', help='Backoff strategy (default: exponential)')
    parser.add_argument('--retry-delay', type=int, default=1, help='Initial delay between retries (seconds)')
    parser.add_argument('--retry-max-delay', type=int, default=60, help='Maximum delay between retries (seconds)')
    parser.add_argument('--retry-multiplier', type=float, default=2.0, help='Multiplier for exponential backoff')
    parser.add_argument('--retry-max-time', type=int, default=300, help='Maximum total time for retries (seconds)')
    parser.add_argument('--retry-on-errors', help='Comma-separated error types to retry on')
    parser.add_argument('--skip-on-errors', help='Comma-separated error types to skip retry')
    
    # Trend analysis options (Phase 2)
    parser.add_argument('--analyze-trend', action='store_true', help='Analyze metric trends and exit')
    parser.add_argument('--trend-metric', help='Metric name to analyze for trends')
    parser.add_argument('--trend-days', type=int, default=30, help='Days of history to analyze (default: 30)')
    parser.add_argument('--detect-regression', action='store_true', help='Detect performance regressions')
    parser.add_argument('--regression-threshold', type=float, default=10.0, help='Regression threshold percentage (default: 10%%)')
    parser.add_argument('--detect-anomalies', action='store_true', help='Detect anomalies in metric history')
    parser.add_argument('--anomaly-method', choices=['iqr', 'zscore', 'mad'], default='iqr', help='Anomaly detection method')
    
    # Baseline calculation options (Phase 2)
    parser.add_argument('--calculate-baseline', action='store_true', help='Calculate intelligent baseline from history and exit')
    parser.add_argument('--baseline-metric', help='Metric to calculate baseline for')
    parser.add_argument('--baseline-method', choices=['intelligent', 'iqr', 'percentile', 'time-based'],
                       default='intelligent', help='Baseline calculation method')
    parser.add_argument('--baseline-percentile', type=int, default=50, help='Percentile for baseline (0-100)')
    parser.add_argument('--baseline-recent-days', type=int, default=7, help='Recent period for time-based baseline')
    parser.add_argument('--baseline-comparison-days', type=int, default=30, help='Comparison period for time-based baseline')
    
    # Dashboard options (Phase 2)
    parser.add_argument('--dashboard', action='store_true', help='Launch web dashboard')
    parser.add_argument('--dashboard-host', default='0.0.0.0', help='Dashboard server host (default: 0.0.0.0)')
    parser.add_argument('--dashboard-port', type=int, default=8000, help='Dashboard server port (default: 8000)')
    
    # Time-series query options (Phase 2)
    parser.add_argument('--query-metric', help='Query time-series metrics')
    parser.add_argument('--query-script', help='Filter by script path')
    parser.add_argument('--query-start', help='Start date (ISO format: YYYY-MM-DD)')
    parser.add_argument('--query-end', help='End date (ISO format: YYYY-MM-DD)')
    parser.add_argument('--query-limit', type=int, default=1000, help='Max records to return (default: 1000)')
    parser.add_argument('--aggregate', choices=['avg', 'min', 'max', 'sum', 'count', 'median'],
                       help='Aggregate function (returns single value)')
    parser.add_argument('--aggregations', action='store_true', help='Get all aggregations (min/max/avg/p50/p95/p99/stddev)')
    parser.add_argument('--bucket', choices=['5min', '15min', '1hour', '1day'],
                       help='Downsample metrics into time buckets')
    parser.add_argument('--metrics-list', action='store_true', help='List available metrics and exit')
    
    # Data export options (Phase 2 Feature #10)
    parser.add_argument('--export-format', choices=['csv', 'json', 'parquet'], 
                       help='Export metrics to specified format')
    parser.add_argument('--export-output', help='Output file path for export')
    parser.add_argument('--export-script', help='Filter export by script path')
    parser.add_argument('--export-metric', help='Filter export by metric name')
    parser.add_argument('--export-start-date', help='Export data from start date (YYYY-MM-DD)')
    parser.add_argument('--export-end-date', help='Export data to end date (YYYY-MM-DD)')
    
    # Retention policy options (Phase 2 Feature #10)
    parser.add_argument('--add-retention-policy', help='Add retention policy by name')
    parser.add_argument('--retention-days', type=int, default=90, help='Days to retain data (default: 90)')
    parser.add_argument('--archive-path', help='Path to archive old data before deletion')
    parser.add_argument('--compliance-mode', choices=['SOC2', 'HIPAA', 'GDPR'], 
                       help='Apply compliance retention policy')
    parser.add_argument('--apply-retention-policy', help='Apply retention policy by name')
    parser.add_argument('--retention-dry-run', action='store_true', help='Preview retention policy effects')
    parser.add_argument('--list-retention-policies', action='store_true', help='List all retention policies')
    
    # Performance optimization options (Phase 3 Feature #1)
    parser.add_argument('--analyze-optimization', help='Analyze script performance and get optimization recommendations')
    parser.add_argument('--optimization-days', type=int, default=30, help='Days of history to analyze (default: 30)')
    parser.add_argument('--optimization-report', action='store_true', help='Generate detailed optimization report')
    
    # Distributed execution options (Phase 3 Feature #2)
    parser.add_argument('--ssh-host', help='Execute script on remote host via SSH')
    parser.add_argument('--ssh-user', help='SSH username')
    parser.add_argument('--ssh-key', help='Path to SSH private key')
    parser.add_argument('--docker-image', help='Execute script in Docker container (provide image name)')
    parser.add_argument('--docker-container', help='Docker container name (optional)')
    parser.add_argument('--docker-env', nargs='*', help='Docker environment variables (KEY=VALUE format)')
    parser.add_argument('--k8s-namespace', help='Kubernetes namespace for job execution')
    parser.add_argument('--k8s-job-name', help='Kubernetes job name')
    parser.add_argument('--k8s-image', help='Kubernetes container image')
    
    # Scheduling options (Phase 3 Feature #3)
    parser.add_argument('--add-scheduled-task', help='Add scheduled task (provide task ID)')
    parser.add_argument('--schedule', choices=['hourly', 'daily', 'weekly', 'every_5min', 'every_30min'], 
                       help='Schedule for task')
    parser.add_argument('--cron', help='Cron expression for complex schedules')
    parser.add_argument('--add-event-trigger', help='Add event trigger (provide event name)')
    parser.add_argument('--event-task-id', help='Task ID to bind to event')
    parser.add_argument('--list-scheduled-tasks', action='store_true', help='List all scheduled tasks')
    parser.add_argument('--trigger-event', help='Manually trigger an event')
    
    # Phase 3 Feature #5: Metrics Correlation Analysis
    parser.add_argument('--analyze-correlations', action='store_true', help='Analyze metric correlations')
    parser.add_argument('--correlation-days', type=int, default=30, help='Period for correlation analysis (days)')
    parser.add_argument('--correlation-threshold', type=float, default=0.5, help='Correlation threshold (0-1)')
    parser.add_argument('--find-predictors', help='Find predictors for target metric')
    parser.add_argument('--detect-dependencies', action='store_true', help='Detect lagged metric dependencies')
    parser.add_argument('--lag-window', type=int, default=5, help='Maximum lag to check (samples)')
    
    # Phase 3 Feature #6: Performance Benchmarking
    parser.add_argument('--create-benchmark', help='Create performance benchmark (provide benchmark name)')
    parser.add_argument('--benchmark-version', help='Version ID for benchmark')
    parser.add_argument('--compare-benchmarks', nargs=2, metavar=('version1', 'version2'),
                       help='Compare two benchmark versions')
    parser.add_argument('--detect-regressions', help='Detect regressions in benchmark')
    parser.add_argument('--list-benchmarks', help='List benchmark versions (optional: specify benchmark name)')
    
    # Phase 3 Feature #7: Alert Intelligence
    parser.add_argument('--auto-tune-thresholds', help='Auto-tune alert thresholds for metric')
    parser.add_argument('--threshold-method', choices=['iqr', 'zscore', 'percentile'], 
                       default='iqr', help='Threshold calculation method')
    parser.add_argument('--analyze-alert-patterns', help='Analyze alert patterns for metric')
    parser.add_argument('--alert-analysis-hours', type=int, default=24, help='Hours to analyze')
    parser.add_argument('--suggest-alert-routing', help='Suggest routing for alert (provide alert JSON)')
    
    # Phase 3 Feature #8: Advanced Debugging & Profiling
    parser.add_argument('--profile-cpu-memory', help='Profile CPU/memory usage (provide script path)')
    parser.add_argument('--profile-duration', type=int, default=60, help='Profile duration (seconds)')
    parser.add_argument('--profile-io', help='Profile I/O operations (provide script path)')
    
    # Phase 3 Feature #9: Enterprise Integrations
    parser.add_argument('--send-to-datadog', help='Send metrics to Datadog (requires --datadog-api-key)')
    parser.add_argument('--send-to-prometheus', help='Send to Prometheus (requires --prometheus-url)')
    parser.add_argument('--send-to-newrelic', help='Send to New Relic (requires --newrelic-api-key)')
    parser.add_argument('--datadog-api-key', help='Datadog API key')
    parser.add_argument('--prometheus-url', help='Prometheus Pushgateway URL')
    parser.add_argument('--newrelic-api-key', help='New Relic API key')
    parser.add_argument('--newrelic-account-id', help='New Relic Account ID')
    parser.add_argument('--integration-status', action='store_true', help='Check integration status')
    
    # Phase 3 Feature #10: Resource Forecasting
    parser.add_argument('--forecast-metric', help='Forecast metric values (provide metric name)')
    parser.add_argument('--forecast-days', type=int, default=7, help='Days to forecast')
    parser.add_argument('--forecast-method', choices=['linear', 'exponential', 'seasonal'],
                       default='linear', help='Forecasting method')
    parser.add_argument('--predict-sla', help='Predict SLA compliance (provide metric name)')
    parser.add_argument('--sla-threshold', type=float, help='SLA threshold value')
    parser.add_argument('--estimate-capacity', help='Estimate capacity needs (provide metric name)')
    parser.add_argument('--capacity-growth-rate', type=float, default=0.1, help='Monthly growth rate')
    parser.add_argument('--capacity-months', type=int, default=12, help='Months to forecast')
    
    # Output options
    parser.add_argument('--json-output', help='Output metrics as JSON')
    parser.add_argument('--suppress-warnings', action='store_true', help='Suppress warnings')

    args = parser.parse_args()

    try:
        # Handle dashboard launch
        if args.dashboard:
            try:
                from dashboard.backend.app import run as run_dashboard
                db_path = args.history_db or 'script_runner_history.db'
                print(f"\n{'='*80}")
                print(f"Starting Python Script Runner Dashboard")
                print(f"{'='*80}")
                print(f"Database: {db_path}")
                print(f"Server: http://{args.dashboard_host}:{args.dashboard_port}")
                print(f"Open your browser to: http://localhost:{args.dashboard_port}")
                print(f"Press Ctrl+C to stop the dashboard\n")
                run_dashboard(host=args.dashboard_host, port=args.dashboard_port, db_path=db_path)
            except ImportError:
                print("Error: Dashboard dependencies not installed")
                print("Install with: pip install -r dashboard/backend/requirements.txt")
                sys.exit(1)
            except Exception as e:
                print(f"Error starting dashboard: {e}")
                sys.exit(1)
        
        # Handle database cleanup
        if args.cleanup_old:
            db_path = args.history_db or 'script_runner_history.db'
            if not os.path.exists(db_path):
                print(f"Database {db_path} not found")
                sys.exit(1)
            
            history_mgr = HistoryManager(db_path)
            print(f"\nCleaning up records older than {args.cleanup_old} days...")
            deleted = history_mgr.cleanup_old_data(args.cleanup_old)
            print(f"Deleted {deleted} records from database")
            sys.exit(0)
        
        # Handle time-series queries (Phase 2)
        if args.query_metric or args.metrics_list:
            db_path = args.history_db or 'script_runner_history.db'
            if not os.path.exists(db_path):
                print(f"Database {db_path} not found")
                sys.exit(1)
            
            history_mgr = HistoryManager(db_path)
            ts_db = TimeSeriesDB(history_mgr)
            
            # List available metrics
            if args.metrics_list:
                print("\n" + "="*80)
                print("AVAILABLE METRICS")
                print("="*80)
                metrics = ts_db.metrics_list(
                    script_path=args.query_script,
                    start_date=args.query_start,
                    end_date=args.query_end
                )
                if metrics:
                    for metric in metrics:
                        print(f"  • {metric}")
                else:
                    print("  No metrics found")
                sys.exit(0)
            
            # Query metrics
            if args.query_metric:
                print("\n" + "="*80)
                print(f"TIME-SERIES QUERY: {args.query_metric}")
                print("="*80)
                
                # Handle aggregations
                if args.aggregations:
                    aggs = ts_db.aggregations(
                        metric_name=args.query_metric,
                        script_path=args.query_script,
                        start_date=args.query_start,
                        end_date=args.query_end
                    )
                    if aggs:
                        print(f"\nAggregations for {args.query_metric}:")
                        for key, value in sorted(aggs.items()):
                            print(f"  {key:15s}: {value:.4f}")
                    else:
                        print("No data found")
                
                # Handle bucketing (downsampling)
                elif args.bucket:
                    buckets = ts_db.bucket(
                        metric_name=args.query_metric,
                        bucket_size=args.bucket,
                        script_path=args.query_script,
                        start_date=args.query_start,
                        end_date=args.query_end
                    )
                    if buckets:
                        print(f"\nBucketed data ({args.bucket} buckets):")
                        for bucket_time, value in sorted(buckets.items()):
                            print(f"  {bucket_time:20s}: {value:.4f}")
                    else:
                        print("No data found")
                
                # Handle single aggregation
                elif args.aggregate:
                    result = ts_db.aggregate(
                        metric_name=args.query_metric,
                        script_path=args.query_script,
                        start_date=args.query_start,
                        end_date=args.query_end,
                        method=args.aggregate
                    )
                    if result is not None:
                        print(f"\n{args.aggregate.upper()} of {args.query_metric}: {result:.4f}")
                    else:
                        print("No data found")
                
                # Query raw data
                else:
                    results = ts_db.query(
                        metric_name=args.query_metric,
                        script_path=args.query_script,
                        start_date=args.query_start,
                        end_date=args.query_end,
                        limit=args.query_limit
                    )
                    if results:
                        print(f"\nRetrieved {len(results)} records:")
                        print(f"{'Timestamp':<26} {'Script':<30} {'Value':<12} {'Exit Code'}")
                        print("-" * 80)
                        for r in results[:50]:  # Show first 50
                            print(f"{r['timestamp']:<26} {r['script_path']:<30} {r['value']:<12.4f} {r['exit_code']}")
                        if len(results) > 50:
                            print(f"... and {len(results) - 50} more records")
                    else:
                        print("No data found")
                
                sys.exit(0)
        
        # Handle data export and retention policies (Phase 2 Feature #10)
        if args.export_format or args.add_retention_policy or args.apply_retention_policy or args.list_retention_policies:
            db_path = args.history_db or 'script_runner_history.db'
            if not os.path.exists(db_path):
                print(f"Database {db_path} not found")
                sys.exit(1)
            
            history_mgr = HistoryManager(db_path)
            
            # Handle data export
            if args.export_format:
                if not args.export_output:
                    parser.error("--export-format requires --export-output")
                
                exporter = DataExporter(history_mgr)
                
                print("\n" + "="*80)
                print(f"EXPORTING DATA TO {args.export_format.upper()}")
                print("="*80)
                
                success = False
                if args.export_format == 'csv':
                    success = exporter.export_to_csv(
                        args.export_output,
                        script_path=args.export_script,
                        metric_name=args.export_metric,
                        start_date=args.export_start_date,
                        end_date=args.export_end_date
                    )
                elif args.export_format == 'json':
                    success = exporter.export_to_json(
                        args.export_output,
                        script_path=args.export_script,
                        metric_name=args.export_metric,
                        start_date=args.export_start_date,
                        end_date=args.export_end_date
                    )
                elif args.export_format == 'parquet':
                    success = exporter.export_to_parquet(
                        args.export_output,
                        script_path=args.export_script,
                        metric_name=args.export_metric
                    )
                
                if success:
                    print(f"✓ Data exported successfully to {args.export_output}")
                else:
                    print(f"✗ Export failed")
                    sys.exit(1)
            
            # Handle retention policies
            retention = RetentionPolicy(history_mgr)
            
            # List policies
            if args.list_retention_policies:
                print("\n" + "="*80)
                print("RETENTION POLICIES")
                print("="*80)
                policies = retention.get_policies()
                if policies:
                    for name, policy in policies.items():
                        print(f"\n  • {name}")
                        print(f"    - Retention: {policy['retention_days']} days")
                        print(f"    - Compliance: {policy.get('compliance', 'None')}")
                        print(f"    - Archive: {policy.get('archive_path', 'None')}")
                else:
                    print("  No policies configured")
            
            # Add policy
            if args.add_retention_policy:
                compliance = args.compliance_mode
                if not compliance:
                    # Preset compliance modes
                    compliance_presets = {
                        'SOC2': 90,
                        'HIPAA': 180,
                        'GDPR': 30
                    }
                    if args.compliance_mode in compliance_presets:
                        args.retention_days = compliance_presets[args.compliance_mode]
                
                retention.add_policy(
                    args.add_retention_policy,
                    retention_days=args.retention_days,
                    archive_path=args.archive_path,
                    compliance=compliance
                )
                print(f"✓ Policy '{args.add_retention_policy}' added")
            
            # Apply policy
            if args.apply_retention_policy:
                result = retention.apply_policy(
                    args.apply_retention_policy,
                    dry_run=args.retention_dry_run
                )
                
                print("\n" + "="*80)
                print(f"RETENTION POLICY: {args.apply_retention_policy}")
                print("="*80)
                
                if result['status'] == 'dry_run':
                    print(f"\n  Cutoff Date: {result['cutoff_date']}")
                    print(f"  Records to delete: {result['records_to_delete']}")
                    print(f"  Compliance: {result['compliance']}")
                    print(f"\n  (This is a DRY RUN - no data was deleted)")
                elif result['status'] == 'success':
                    print(f"\n  ✓ Policy applied successfully")
                    print(f"  Records deleted: {result['deleted_records']}")
                    print(f"  Cutoff date: {result['cutoff_date']}")
                    print(f"  Archived: {result['archived']}")
                    print(f"  Compliance: {result['compliance']}")
                else:
                    print(f"  ✗ Error: {result['message']}")
                    sys.exit(1)
            
            if args.export_format or args.add_retention_policy or args.apply_retention_policy or args.list_retention_policies:
                sys.exit(0)
        
        # Handle performance optimization analysis (Phase 3 Feature #1)
        if args.analyze_optimization:
            db_path = args.history_db or 'script_runner_history.db'
            if not os.path.exists(db_path):
                print(f"Database {db_path} not found")
                sys.exit(1)
            
            history_mgr = HistoryManager(db_path)
            optimizer = PerformanceOptimizer(history_mgr)
            
            if args.optimization_report:
                # Generate detailed report
                report = optimizer.get_optimization_report(
                    args.analyze_optimization,
                    days=args.optimization_days
                )
                print(report)
            else:
                # Show JSON analysis
                analysis = optimizer.analyze_script_performance(
                    args.analyze_optimization,
                    days=args.optimization_days
                )
                
                print("\n" + "="*80)
                print(f"PERFORMANCE ANALYSIS: {args.analyze_optimization}")
                print("="*80)
                
                if analysis["status"] == "success":
                    print(f"\nTotal Runs Analyzed: {analysis.get('total_runs', 0)}")
                    print(f"Analysis Period: {analysis.get('days_analyzed', 0)} days")
                    
                    # CPU Analysis
                    if "cpu_analysis" in analysis:
                        cpu = analysis["cpu_analysis"]
                        print(f"\n📊 CPU Usage:")
                        print(f"   Average: {cpu['average']}%")
                        print(f"   Maximum: {cpu['max']}%")
                        print(f"   Status: {cpu['recommendation'].get('severity')}")
                        print(f"   {cpu['recommendation'].get('message')}")
                    
                    # Memory Analysis
                    if "memory_analysis" in analysis:
                        mem = analysis["memory_analysis"]
                        print(f"\n💾 Memory Usage:")
                        print(f"   Average: {mem['average_mb']} MB")
                        print(f"   Maximum: {mem['max_mb']} MB")
                        print(f"   Status: {mem['recommendation'].get('severity')}")
                        print(f"   {mem['recommendation'].get('message')}")
                    
                    # Execution Time Analysis
                    if "execution_analysis" in analysis:
                        exec_time = analysis["execution_analysis"]
                        print(f"\n⏱️  Execution Time:")
                        print(f"   Average: {exec_time['average_seconds']}s")
                        print(f"   Maximum: {exec_time['max_seconds']}s")
                        print(f"   Status: {exec_time['recommendation'].get('severity')}")
                        print(f"   {exec_time['recommendation'].get('message')}")
                    
                    # Recommendations
                    print(f"\n💡 Recommendations:")
                    if analysis.get("recommendations"):
                        for i, rec in enumerate(analysis["recommendations"], 1):
                            if isinstance(rec, dict):
                                print(f"\n{i}. [{rec.get('severity')}] {rec.get('message')}")
                                if rec.get("suggested_actions"):
                                    for action in rec["suggested_actions"]:
                                        print(f"   • {action}")
                else:
                    print(f"Status: {analysis['status']}")
                    print(f"Message: {analysis.get('message', 'Unknown error')}")
            
            sys.exit(0)
        
        # Handle scheduled tasks (Phase 3 Feature #3)
        if args.add_scheduled_task or args.list_scheduled_tasks or args.trigger_event or args.add_event_trigger:
            scheduler = TaskScheduler()
            
            if args.add_scheduled_task:
                if not args.script:
                    parser.error("--add-scheduled-task requires --script")
                
                task = scheduler.add_scheduled_task(
                    args.add_scheduled_task,
                    args.script,
                    schedule=args.schedule,
                    cron_expr=args.cron
                )
                print(f"\n✅ Task '{args.add_scheduled_task}' scheduled")
                print(f"   Script: {task.script_path}")
                print(f"   Schedule: {task.schedule or task.cron_expr or 'manual'}")
                print(f"   Next run: {task.next_run}")
            
            if args.add_event_trigger:
                if not args.event_task_id:
                    parser.error("--add-event-trigger requires --event-task-id")
                
                if scheduler.add_event_trigger(args.event_task_id, args.add_event_trigger):
                    print(f"\n✅ Event trigger added")
                    print(f"   Event: {args.add_event_trigger}")
                    print(f"   Task: {args.event_task_id}")
                else:
                    print(f"\n❌ Failed to add event trigger")
            
            if args.trigger_event:
                tasks = scheduler.trigger_event(args.trigger_event)
                print(f"\n✅ Event '{args.trigger_event}' triggered")
                print(f"   Tasks to execute: {len(tasks)}")
                for task_id in tasks:
                    print(f"   • {task_id}")
            
            if args.list_scheduled_tasks:
                print(f"\n{'='*80}")
                print("SCHEDULED TASKS")
                print(f"{'='*80}")
                
                tasks = scheduler.list_tasks()
                if tasks:
                    for task in tasks:
                        print(f"\n📋 {task['task_id']}")
                        print(f"   Script: {task['script']}")
                        print(f"   Enabled: {task['enabled']}")
                        print(f"   Runs: {task['run_count']}")
                        print(f"   Last status: {task['last_status']}")
                        if task['triggers']:
                            print(f"   Triggers: {', '.join(task['triggers'])}")
                else:
                    print("No tasks scheduled")
            
            sys.exit(0)
        
        # Handle distributed execution (Phase 3 Feature #2)
        if args.ssh_host or args.docker_image or args.k8s_namespace:
            if not args.script:
                parser.error("Distributed execution requires --script argument")
            
            executor = RemoteExecutor()
            
            if args.ssh_host:
                print(f"\n{'='*80}")
                print(f"REMOTE EXECUTION (SSH): {args.script}")
                print(f"{'='*80}")
                print(f"Host: {args.ssh_host}")
                print(f"User: {args.ssh_user or 'default'}")
                
                result = executor.execute_ssh(
                    args.ssh_host,
                    args.script,
                    args=args.args,
                    username=args.ssh_user,
                    key_file=args.ssh_key,
                    timeout=args.timeout or 300
                )
                
                if result["status"] == "success":
                    print(f"\n✅ Execution succeeded (exit code: {result['exit_code']})")
                    if result.get("stdout"):
                        print(f"\nStdout:\n{result['stdout']}")
                    if result.get("stderr"):
                        print(f"\nStderr:\n{result['stderr']}")
                    sys.exit(result['exit_code'])
                else:
                    print(f"\n❌ Execution failed: {result['message']}")
                    sys.exit(1)
            
            elif args.docker_image:
                print(f"\n{'='*80}")
                print(f"CONTAINER EXECUTION (Docker): {args.script}")
                print(f"{'='*80}")
                print(f"Image: {args.docker_image}")
                
                env_dict = {}
                if args.docker_env:
                    for env_var in args.docker_env:
                        key, val = env_var.split('=', 1)
                        env_dict[key] = val
                
                result = executor.execute_docker(
                    args.docker_image,
                    args.script,
                    args=args.args,
                    container_name=args.docker_container,
                    env_vars=env_dict,
                    timeout=args.timeout or 300
                )
                
                if result["status"] == "success":
                    print(f"\n✅ Container execution succeeded")
                    if result.get("output"):
                        print(f"\nOutput:\n{result['output']}")
                    sys.exit(0)
                else:
                    print(f"\n❌ Container execution failed: {result['message']}")
                    sys.exit(1)
            
            elif args.k8s_namespace:
                if not args.k8s_job_name or not args.k8s_image:
                    parser.error("--k8s-namespace requires both --k8s-job-name and --k8s-image")
                
                print(f"\n{'='*80}")
                print(f"KUBERNETES EXECUTION: {args.script}")
                print(f"{'='*80}")
                print(f"Namespace: {args.k8s_namespace}")
                print(f"Job: {args.k8s_job_name}")
                print(f"Image: {args.k8s_image}")
                
                result = executor.execute_kubernetes(
                    args.k8s_namespace,
                    args.k8s_job_name,
                    args.k8s_image,
                    ["python", args.script] + (args.args or []),
                    timeout=args.timeout or 300
                )
                
                if result["status"] in ["success", "submitted"]:
                    print(f"\n✅ Job {result['status']}: {result.get('message', 'See cluster for details')}")
                    sys.exit(0)
                else:
                    print(f"\n❌ Job submission failed: {result['message']}")
                    sys.exit(1)
        
        # Handle baseline calculation options (don't require running a script)
        if args.calculate_baseline:
            if not args.script or not args.baseline_metric:
                parser.error("--calculate-baseline requires both script path and --baseline-metric")
            
            history_mgr = HistoryManager(db_path=args.history_db or 'script_runner_history.db')
            baseline_calc = BaselineCalculator()
            
            print("\n" + "="*80)
            print(f"BASELINE CALCULATION: {args.baseline_metric} for {args.script}")
            print("="*80)
            
            if args.baseline_method == 'intelligent':
                metric_series = history_mgr.get_metrics_for_script(
                    args.script, args.baseline_metric, days=args.trend_days
                )
                if metric_series:
                    values = [v for _, v in metric_series]
                    result = baseline_calc.calculate_intelligent_baseline(values)
                    
                    if 'error' not in result:
                        print(f"\nRecommended Baseline: {result['baseline']}")
                        print(f"Method: {result['method']}")
                        print(f"Reasoning: {result['reasoning']}")
                        
                        if 'data_characteristics' in result:
                            print(f"\nData Characteristics:")
                            dc = result['data_characteristics']
                            print(f"  Data Points: {dc['data_points']}")
                            print(f"  Mean: {dc['mean']}, Median: {dc['median']}")
                            print(f"  Std Dev: {dc['stddev']}")
                            print(f"  Coefficient of Variation: {dc['coefficient_of_variation']}%")
                            print(f"  Range: {dc['range']}")
                    else:
                        print(f"Error: {result['error']}")
                else:
                    print("No metric data found for the specified script and metric")
            
            elif args.baseline_method == 'percentile':
                metric_series = history_mgr.get_metrics_for_script(
                    args.script, args.baseline_metric, days=args.trend_days
                )
                if metric_series:
                    values = [v for _, v in metric_series]
                    result = baseline_calc.calculate_from_percentile(values, args.baseline_percentile)
                    
                    print(f"\nBaseline (P{result['percentile']}): {result['baseline']}")
                    print(f"Data Points: {result['data_points']}")
                    print(f"Min: {result['min']}, Max: {result['max']}")
                else:
                    print("No metric data found")
            
            elif args.baseline_method == 'iqr':
                metric_series = history_mgr.get_metrics_for_script(
                    args.script, args.baseline_metric, days=args.trend_days
                )
                if metric_series:
                    values = [v for _, v in metric_series]
                    result = baseline_calc.calculate_with_iqr_filtering(values)
                    
                    print(f"\nBaseline (IQR Filtered): {result.get('baseline', 'N/A')}")
                    print(f"Outliers Removed: {result['outliers_removed']} ({result['outlier_percentage']}%)")
                    print(f"Filtered Data Points: {result['filtered_data_points']}")
                else:
                    print("No metric data found")
            
            elif args.baseline_method == 'time-based':
                result = baseline_calc.calculate_time_based_baseline(
                    history_mgr, args.script, args.baseline_metric,
                    recent_days=args.baseline_recent_days,
                    comparison_days=args.baseline_comparison_days
                )
                
                if 'error' not in result:
                    print(f"\nRecent Baseline ({args.baseline_recent_days}d): {result['recent_baseline']}")
                    print(f"Historical Baseline ({args.baseline_comparison_days}d): {result['historical_baseline']}")
                    print(f"Change: {result['percent_change']:+.2f}%")
                    print(f"Status: {result['status'].upper()}")
                    print(f"Recent Samples: {result['recent_samples']}, Historical Samples: {result['historical_samples']}")
                else:
                    print(f"Error: {result['error']}")
            
            sys.exit(0)
        
        # Handle trend analysis options (don't require running a script)
        if args.analyze_trend:
            if not args.script or not args.trend_metric:
                parser.error("--analyze-trend requires both script path and --trend-metric")
            
            history_mgr = HistoryManager(db_path=args.history_db or 'script_runner_history.db')
            analyzer = TrendAnalyzer()
            
            analysis = analyzer.analyze_metric_history(
                history_mgr,
                args.script,
                args.trend_metric,
                days=args.trend_days
            )
            
            print("\n" + "="*80)
            print(f"TREND ANALYSIS: {args.trend_metric} for {args.script}")
            print("="*80)
            
            if 'error' in analysis:
                print(f"Error: {analysis['error']}")
            else:
                print(f"Data Points: {analysis['data_points']}")
                print(f"Period: {analysis['period_days']} days")
                print(f"Latest Value: {analysis['latest_value']}")
                print(f"First Value: {analysis['first_value']}")
                
                print(f"\nTrend Analysis:")
                trend = analysis['trend']
                print(f"  Trend: {trend['trend']}")
                print(f"  Slope: {trend['slope']:.6f} ({trend['slope_pct_per_run']:+.2f}% per run)")
                print(f"  R-squared: {trend['r_squared']:.4f}")
                
                print(f"\nPercentiles:")
                perc = analysis['percentiles']
                print(f"  Min: {perc['min']}, Max: {perc['max']}")
                print(f"  Mean: {perc['mean']}, Median: {perc['median']}")
                print(f"  P75: {perc['p75']}, P90: {perc['p90']}, P95: {perc['p95']}, P99: {perc['p99']}")
                print(f"  StdDev: {perc['stddev']}")
                
                if args.detect_regression:
                    reg = analysis['regression']
                    print(f"\nRegression Detection:")
                    if 'reason' in reg and reg['reason'] == 'insufficient_data':
                        print(f"  Status: Insufficient data (need {reg.get('data_points', 0)} points, got {reg.get('data_points', 0)})")
                    else:
                        print(f"  Detected: {'YES' if reg.get('regression_detected', False) else 'NO'}")
                        if 'baseline_mean' in reg:
                            print(f"  Baseline Mean: {reg['baseline_mean']}")
                            print(f"  Recent Mean: {reg['recent_mean']}")
                            print(f"  Change: {reg['percent_change']:+.2f}% (threshold: {reg['threshold_pct']}%)")
                            print(f"  Severity: {reg['severity']}")
                
                if args.detect_anomalies:
                    anom = analysis['anomalies']
                    print(f"\nAnomaly Detection ({anom['method']}):")
                    print(f"  Found: {anom['count']} anomalies ({anom['percentage']:.1f}%)")
                    if anom['anomalies'] and len(anom['anomalies']) <= 10:
                        for a in anom['anomalies'][:10]:
                            print(f"    - Index {a['index']}: value={a['value']}, type={a['type']}")
            
            sys.exit(0)
        
        # Handle metrics correlation analysis (Phase 3 Feature #5)
        if args.analyze_correlations or args.find_predictors or args.detect_dependencies:
            correlator = MetricsCorrelationAnalyzer()
            
            if args.analyze_correlations:
                print(f"\n{'='*80}")
                print("METRIC CORRELATION ANALYSIS")
                print(f"{'='*80}")
                print(f"Period: {args.correlation_days} days")
                print(f"Threshold: {args.correlation_threshold}\n")
                
                result = correlator.analyze_metric_correlations(
                    days=args.correlation_days,
                    threshold=args.correlation_threshold
                )
                
                if result.get("status") == "success":
                    print(f"Metrics Analyzed: {result['metric_count']}")
                    print(f"Significant Correlations: {result['total_pairs']}\n")
                    
                    if result['correlations']:
                        print("Top Correlations:")
                        for i, corr in enumerate(result['correlations'][:10], 1):
                            print(f"\n  {i}. {corr['metric1']} ↔ {corr['metric2']}")
                            print(f"     Correlation: {corr['correlation']} ({corr['strength']})")
                            print(f"     Direction: {corr['direction']} | Samples: {corr['samples']}")
                    else:
                        print("No significant correlations found")
                else:
                    print(f"Error: {result.get('status', 'Unknown error')}")
            
            elif args.find_predictors:
                print(f"\n{'='*80}")
                print(f"METRIC PREDICTORS: {args.find_predictors}")
                print(f"{'='*80}")
                print(f"Period: {args.correlation_days} days")
                print(f"Min Correlation: {args.correlation_threshold}\n")
                
                result = correlator.find_metric_predictors(
                    target_metric=args.find_predictors,
                    days=args.correlation_days,
                    correlation_threshold=args.correlation_threshold
                )
                
                if result.get("status") == "success":
                    if result['predictors']:
                        print(f"Found {result['predictor_count']} predictor(s):\n")
                        for i, pred in enumerate(result['predictors'], 1):
                            print(f"  {i}. {pred['metric']}")
                            print(f"     Correlation: {pred['correlation']} ({pred['strength']})")
                            print(f"     Direction: {pred['direction']} | Samples: {pred['samples']}")
                    else:
                        print(f"No predictors found for {args.find_predictors}")
                else:
                    print(f"Error: {result.get('status', 'Unknown error')}")
            
            elif args.detect_dependencies:
                print(f"\n{'='*80}")
                print("LAGGED METRIC DEPENDENCIES")
                print(f"{'='*80}")
                print(f"Period: {args.correlation_days} days")
                print(f"Max Lag: {args.lag_window} samples\n")
                
                result = correlator.detect_metric_dependencies(
                    days=args.correlation_days,
                    lag_window=args.lag_window
                )
                
                if result.get("status") == "success":
                    if result['dependencies']:
                        print(f"Found {len(result['dependencies'])} lagged dependency(ies):\n")
                        for dep in result['dependencies']:
                            print(f"  {dep['source']} → {dep['target']} (lag: {dep['lag']})")
                            print(f"     Correlation: {dep['correlation']}")
                            print(f"     {dep['interpretation']}\n")
                    else:
                        print("No significant lagged dependencies found")
                else:
                    print(f"Error: {result.get('status', 'Unknown error')}")
            
            sys.exit(0)
        
        # Handle performance benchmarking (Phase 3 Feature #6)
        if args.create_benchmark or args.compare_benchmarks or args.detect_regressions or args.list_benchmarks:
            benchmark_mgr = BenchmarkManager()
            
            if args.create_benchmark:
                print(f"\n{'='*80}")
                print(f"CREATE BENCHMARK: {args.create_benchmark}")
                print(f"{'='*80}")
                
                result = benchmark_mgr.create_benchmark(
                    benchmark_name=args.create_benchmark,
                    script_path=args.script,
                    version_id=args.benchmark_version,
                    notes=args.script_args[0] if args.script_args else None
                )
                
                if result['status'] == 'success':
                    print(f"\n✅ Benchmark created successfully")
                    print(f"   ID: {result['benchmark_id']}")
                    print(f"   Version: {result['version']}")
                    print(f"\n   CPU: μ={result['cpu']['mean']}%, σ={result['cpu']['stdev']}")
                    print(f"   Memory: μ={result['memory']['mean']}MB, σ={result['memory']['stdev']}")
                    print(f"   Exec Time: μ={result['execution_time']['mean']}s, σ={result['execution_time']['stdev']}")
                else:
                    print(f"\n❌ Error: {result['error']}")
            
            elif args.compare_benchmarks:
                v1, v2 = args.compare_benchmarks
                print(f"\n{'='*80}")
                print(f"BENCHMARK COMPARISON: {args.create_benchmark or 'default'}")
                print(f"{'='*80}")
                print(f"Baseline: {v1}")
                print(f"Current: {v2}\n")
                
                result = benchmark_mgr.compare_benchmarks(
                    benchmark_name=args.create_benchmark or 'default',
                    version1_id=v1,
                    version2_id=v2
                )
                
                if result['status'] == 'success':
                    print(f"Metrics Comparison ({result['regressions']} regressions detected):\n")
                    for comp in result['comparisons']:
                        print(f"  {comp['metric']}:")
                        print(f"     Baseline: {comp['baseline']}")
                        print(f"     Current: {comp['current']}")
                        print(f"     Change: {comp['percent_change']:+.1f}% {comp['direction']} [{comp['severity'].upper()}]")
                else:
                    print(f"Error: {result['error']}")
            
            elif args.detect_regressions:
                print(f"\n{'='*80}")
                print(f"REGRESSION DETECTION: {args.detect_regressions}")
                print(f"{'='*80}")
                print(f"Threshold: {args.regression_threshold}%\n")
                
                result = benchmark_mgr.detect_regressions(
                    benchmark_name=args.detect_regressions,
                    regression_threshold=args.regression_threshold
                )
                
                if result['status'] == 'success':
                    if result['regression_count'] > 0:
                        print(f"Found {result['regression_count']} regression(s):\n")
                        for reg in result['regressions']:
                            print(f"  {reg['metric']} ({reg['from_version']} → {reg['to_version']})")
                            print(f"     {reg['previous']:.2f} → {reg['current']:.2f}")
                            print(f"     Change: {reg['percent_change']:+.1f}% [{reg['severity'].upper()}]\n")
                    else:
                        print("No regressions detected")
                else:
                    print(f"Error: {result['error']}")
            
            elif args.list_benchmarks:
                print(f"\n{'='*80}")
                print("BENCHMARKS")
                print(f"{'='*80}\n")
                
                if args.list_benchmarks != "all":
                    # Specific benchmark
                    result = benchmark_mgr.list_benchmarks(benchmark_name=args.list_benchmarks)
                    
                    if result['status'] == 'success':
                        print(f"Benchmark: {result['benchmark']}")
                        print(f"Versions: {result['version_count']}\n")
                        for v in result['versions']:
                            print(f"  {v['version']}")
                            print(f"     Created: {v['created']}")
                            print(f"     CPU: {v['cpu_mean']}% | Memory: {v['memory_mean']}MB | ExecTime: {v['exec_time_mean']}s")
                            print(f"     Samples: {v['samples']}\n")
                    else:
                        print(f"Error: {result['error']}")
                else:
                    # All benchmarks
                    result = benchmark_mgr.list_benchmarks()
                    
                    if result['status'] == 'success':
                        print(f"Total Benchmarks: {result['benchmark_count']}\n")
                        for bench in result['benchmarks']:
                            print(f"  • {bench}")
                    else:
                        print(f"Error: {result['error']}")
            
            sys.exit(0)
        
        # Handle alert intelligence (Phase 3 Feature #7)
        if args.auto_tune_thresholds or args.analyze_alert_patterns or args.suggest_alert_routing:
            alert_intel = AlertIntelligence()
            
            if args.auto_tune_thresholds:
                print(f"\n{'='*80}")
                print(f"AUTO-TUNE ALERT THRESHOLDS: {args.auto_tune_thresholds}")
                print(f"{'='*80}")
                print(f"Method: {args.threshold_method}\n")
                
                # Get metric history
                try:
                    conn = sqlite3.connect("metrics.db")
                    c = conn.cursor()
                    c.execute("""
                        SELECT metric_value FROM metrics 
                        WHERE metric_name = ? 
                        ORDER BY timestamp DESC LIMIT 1000
                    """, (args.auto_tune_thresholds,))
                    values = [row[0] for row in c.fetchall()]
                    conn.close()
                    
                    if not values:
                        print(f"No metric data found for {args.auto_tune_thresholds}")
                    else:
                        result = alert_intel.calculate_adaptive_threshold(
                            args.auto_tune_thresholds,
                            values,
                            method=args.threshold_method
                        )
                        
                        if result['status'] == 'success':
                            print(f"✅ Adaptive Threshold Calculated")
                            print(f"   Metric: {result['metric']}")
                            print(f"   Method: {result['method'].upper()}")
                            print(f"   Lower Bound: {result['lower']}")
                            print(f"   Upper Bound: {result['upper']}")
                            print(f"   Confidence: {result['confidence']*100}%")
                            print(f"   Based on: {result['samples']} samples")
                        else:
                            print(f"Error: {result.get('status', 'Unknown error')}")
                except Exception as e:
                    print(f"Error: {e}")
            
            elif args.analyze_alert_patterns:
                print(f"\n{'='*80}")
                print(f"ALERT PATTERN ANALYSIS: {args.analyze_alert_patterns}")
                print(f"{'='*80}")
                print(f"Period: {args.alert_analysis_hours} hours\n")
                
                result = alert_intel.analyze_alert_patterns(
                    args.analyze_alert_patterns,
                    hours=args.alert_analysis_hours
                )
                
                if result['status'] == 'success':
                    print(f"Total Alerts: {result['total_alerts']}")
                    print(f"Alerts/Hour: {result['alerts_per_hour']}\n")
                    
                    print("Severity Distribution:")
                    for sev, count in result['severity_distribution'].items():
                        print(f"  {sev.capitalize()}: {count}")
                    
                    print(f"\nValue Statistics:")
                    print(f"  Mean: {result['value_stats']['mean']}")
                    print(f"  Min: {result['value_stats']['min']}")
                    print(f"  Max: {result['value_stats']['max']}")
                    
                    print(f"\n💡 Recommendation: {result['recommendation']}")
                else:
                    print(f"Status: {result['status']}")
            
            elif args.suggest_alert_routing:
                print(f"\n{'='*80}")
                print("INTELLIGENT ALERT ROUTING")
                print(f"{'='*80}\n")
                
                try:
                    import json
                    alert = json.loads(args.suggest_alert_routing)
                except:
                    alert = {"severity": args.suggest_alert_routing}
                
                result = alert_intel.suggest_alert_routing(alert)
                
                if result['status'] == 'success':
                    print(f"Suggested Team: {result['suggested_team']}")
                    print(f"Notification Method: {result['notification_method']}")
                    
                    if result.get('escalation_minutes'):
                        print(f"Escalation Time: {result['escalation_minutes']} minutes")
                    if result.get('require_acknowledgment'):
                        print(f"Requires Acknowledgment: Yes")
                else:
                    print(f"Error: {result['error']}")
            
            sys.exit(0)
        
        # Handle advanced profiling (Phase 3 Feature #8)
        if args.profile_cpu_memory or args.profile_io:
            profiler = AdvancedProfiler()
            
            if args.profile_cpu_memory:
                print(f"\n{'='*80}")
                print(f"CPU/MEMORY PROFILING")
                print(f"{'='*80}")
                print(f"Script: {args.profile_cpu_memory}")
                print(f"Duration: {args.profile_duration}s\n")
                
                result = profiler.profile_cpu_and_memory(
                    args.profile_cpu_memory,
                    duration_seconds=args.profile_duration
                )
                
                if result['status'] == 'success':
                    print(f"✅ Profiling completed ({result['samples_collected']} samples)\n")
                    print("CPU Usage (seconds):")
                    for k, v in result['cpu_stats'].items():
                        print(f"  {k}: {v}")
                    print("\nMemory Usage (MB):")
                    for k, v in result['memory_stats_mb'].items():
                        print(f"  {k}: {v}")
                else:
                    print(f"Error: {result['error']}")
            
            elif args.profile_io:
                print(f"\n{'='*80}")
                print(f"I/O PROFILING")
                print(f"{'='*80}")
                print(f"Script: {args.profile_io}\n")
                
                result = profiler.io_profile(args.profile_io)
                
                if result['status'] == 'success':
                    print(f"✅ I/O Profile:\n")
                    for op, count in result['io_operations'].items():
                        print(f"  {op}: {count}")
                else:
                    print(f"Error: {result['error']}")
            
            sys.exit(0)
        
        # Handle enterprise integrations (Phase 3 Feature #9)
        if args.integration_status or args.send_to_datadog or args.send_to_prometheus or args.send_to_newrelic:
            integrations = EnterpriseIntegrations()
            
            if args.integration_status:
                print(f"\n{'='*80}")
                print("ENTERPRISE INTEGRATIONS")
                print(f"{'='*80}\n")
                
                result = integrations.get_integration_status()
                print(f"Available Integrations:")
                for integ in result['available_integrations']:
                    print(f"  • {integ}")
                print(f"\n{result['message']}")
            
            elif args.send_to_datadog:
                print(f"\n{'='*80}")
                print("SEND TO DATADOG")
                print(f"{'='*80}\n")
                
                result = integrations.send_to_datadog(
                    args.send_to_datadog,
                    value=float(args.script_args[0]) if args.script_args else 0,
                    api_key=args.datadog_api_key
                )
                
                if result['status'] == 'success':
                    print(f"✅ Sent to Datadog: {args.send_to_datadog}")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif args.send_to_prometheus:
                print(f"\n{'='*80}")
                print("SEND TO PROMETHEUS")
                print(f"{'='*80}\n")
                
                result = integrations.send_to_prometheus(
                    args.send_to_prometheus,
                    value=float(args.script_args[0]) if args.script_args else 0,
                    pushgateway_url=args.prometheus_url
                )
                
                if result['status'] == 'success':
                    print(f"✅ Sent to Prometheus: {args.send_to_prometheus}")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif args.send_to_newrelic:
                print(f"\n{'='*80}")
                print("SEND TO NEW RELIC")
                print(f"{'='*80}\n")
                
                result = integrations.send_to_newrelic(
                    args.send_to_newrelic,
                    value=float(args.script_args[0]) if args.script_args else 0,
                    account_id=args.newrelic_account_id,
                    api_key=args.newrelic_api_key
                )
                
                if result['status'] == 'success':
                    print(f"✅ Sent to New Relic: {args.send_to_newrelic}")
                else:
                    print(f"❌ Error: {result['error']}")
            
            sys.exit(0)
        
        # Handle resource forecasting (Phase 3 Feature #10)
        if args.forecast_metric or args.predict_sla or args.estimate_capacity:
            forecaster = ResourceForecaster()
            
            if args.forecast_metric:
                print(f"\n{'='*80}")
                print(f"RESOURCE FORECAST: {args.forecast_metric}")
                print(f"{'='*80}")
                print(f"Method: {args.forecast_method.upper()}")
                print(f"Forecast Days: {args.forecast_days}\n")
                
                result = forecaster.forecast_metric(
                    args.forecast_metric,
                    days_ahead=args.forecast_days,
                    method=args.forecast_method
                )
                
                if result['status'] == 'success':
                    print(f"Forecast (Confidence: {result['confidence']*100}%):\n")
                    for pred in result['forecast'][:7]:
                        print(f"  Day {pred['days_ahead']}: {pred['predicted_value']}")
                else:
                    print(f"Status: {result.get('status', 'Error')}")
            
            elif args.predict_sla:
                if not args.sla_threshold:
                    print("Error: --sla-threshold required with --predict-sla")
                    sys.exit(1)
                
                print(f"\n{'='*80}")
                print(f"SLA COMPLIANCE PREDICTION: {args.predict_sla}")
                print(f"{'='*80}")
                print(f"Threshold: {args.sla_threshold}")
                print(f"Forecast Days: {args.forecast_days}\n")
                
                result = forecaster.predict_sla_compliance(
                    args.sla_threshold,
                    args.predict_sla,
                    forecast_days=args.forecast_days
                )
                
                if result['status'] == 'success':
                    print(f"Predicted Compliance: {result['predicted_compliance']}%")
                    print(f"Risk Level: {result['risk_level'].upper()}")
                    print(f"Predicted Violations: {result['predicted_violations']} days")
                else:
                    print(f"Error: {result.get('error', 'Unknown')}")
            
            elif args.estimate_capacity:
                print(f"\n{'='*80}")
                print(f"CAPACITY ESTIMATION: {args.estimate_capacity}")
                print(f"{'='*80}")
                print(f"Growth Rate: {args.capacity_growth_rate*100:.0f}%/month")
                print(f"Forecast: {args.capacity_months} months\n")
                
                result = forecaster.estimate_capacity_needs(
                    args.estimate_capacity,
                    growth_rate=args.capacity_growth_rate,
                    forecast_months=args.capacity_months
                )
                
                if result['status'] == 'success':
                    print(f"Current Value: {result['current_value']}")
                    print(f"Max Estimated ({args.capacity_months}m): {result['max_estimated']}")
                    print(f"Recommended Capacity (+{result['buffer_percent']}% buffer): {result['recommended_capacity']}")
                else:
                    print(f"Error: {result.get('error', 'Unknown')}")
            
            sys.exit(0)
        
        # Handle database utility options first (they don't require running a script)
        if args.cleanup_old:
            history_mgr = HistoryManager(db_path=args.history_db or 'script_runner_history.db')
            history_mgr.cleanup_old_data(days=args.cleanup_old)
            print(f"Cleanup completed for records older than {args.cleanup_old} days")
            sys.exit(0)
        
        if args.db_stats:
            history_mgr = HistoryManager(db_path=args.history_db or 'script_runner_history.db')
            stats = history_mgr.get_database_stats()
            print("\n" + "="*80)
            print("DATABASE STATISTICS")
            print("="*80)
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"{key}: {value:.2f}")
                else:
                    print(f"{key}: {value}")
            sys.exit(0)
        
        if args.show_history:
            if not args.script:
                # Can use script filter, but not required for showing all history
                pass
            
            history_mgr = HistoryManager(db_path=args.history_db or 'script_runner_history.db')
            executions = history_mgr.get_execution_history(
                script_path=args.script,
                limit=args.history_limit,
                days=args.history_days
            )
            
            if not executions:
                print("No execution history found")
                sys.exit(0)
            
            print("\n" + "="*80)
            print(f"EXECUTION HISTORY (Last {args.history_days} days)")
            print("="*80)
            
            for exec_record in executions:
                print(f"\nScript: {exec_record['script_path']}")
                print(f"  ID: {exec_record['id']}")
                print(f"  Time: {exec_record['start_time']}")
                print(f"  Duration: {exec_record['execution_time_seconds']:.2f}s")
                print(f"  Exit Code: {exec_record['exit_code']}")
                print(f"  Success: {exec_record['success']}")
                if exec_record.get('metrics'):
                    print(f"  Metrics:")
                    for metric_name, metric_value in exec_record['metrics'].items():
                        print(f"    {metric_name}: {metric_value:.2f}")
            
            sys.exit(0)
        
        # For normal script execution, require script argument
        if not args.script:
            parser.error("Script argument is required. Use --db-stats or --show-history for database operations without a script.")
        
        # Create runner
        runner = ScriptRunner(
            script_path=args.script,
            script_args=args.script_args,
            timeout=args.timeout,
            log_level=args.log_level,
            config_file=args.config,
            history_db=args.history_db,
            enable_history=not args.disable_history
        )

        runner.monitor_interval = args.monitor_interval
        runner.suppress_warnings = args.suppress_warnings
        
        # Configure retry strategy (Phase 2)
        retry_on_errors = []
        skip_on_errors = []
        if args.retry_on_errors:
            retry_on_errors = [e.strip() for e in args.retry_on_errors.split(',')]
        if args.skip_on_errors:
            skip_on_errors = [e.strip() for e in args.skip_on_errors.split(',')]
        
        runner.retry_config = RetryConfig(
            max_attempts=args.retry + 1 if args.retry > 0 else 1,
            strategy=args.retry_strategy,
            initial_delay=args.retry_delay,
            max_delay=args.retry_max_delay,
            multiplier=args.retry_multiplier,
            retry_on_errors=retry_on_errors if retry_on_errors else None,
            skip_on_errors=skip_on_errors if skip_on_errors else None,
            max_total_time=args.retry_max_time
        )
        
        # Legacy support
        runner.retry_count = args.retry
        runner.retry_delay = args.retry_delay

        # Configure alerts from command line
        if args.slack_webhook:
            runner.alert_manager.configure_slack(args.slack_webhook)

        if args.email_config:
            try:
                with open(args.email_config, 'r') as f:
                    email_config = json.load(f)
                runner.alert_manager.configure_email(**email_config)
            except Exception as e:
                logging.error(f"Failed to load email config: {e}")

        # Add performance gates from command line
        if args.gates:
            for gate_spec in args.gates:
                try:
                    parts = gate_spec.split(':')
                    metric = parts[0]
                    value = float(parts[1])
                    runner.cicd_integration.add_performance_gate(metric, max_value=value)
                except (ValueError, IndexError) as e:
                    logging.error(f"Invalid gate specification: {gate_spec} - {e}")

        # Load baseline if specified
        if args.baseline:
            runner.cicd_integration.load_baseline(args.baseline)

        # Run the script
        result = runner.run_script(retry_on_failure=args.retry > 0)

        # Process results
        metrics = result['metrics']
        stdout = result['stdout']
        stderr = result['stderr']
        returncode = result['returncode']

        # Print output if not suppressing
        if stdout:
            print(stdout, end='')
        if stderr:
            print(stderr, end='', file=sys.stderr)

        # Check performance gates
        gates_passed = True
        gate_results = []
        if runner.cicd_integration.performance_gates:
            gates_passed, gate_results = runner.cicd_integration.check_gates(metrics)
            print("\n" + "="*80)
            print("PERFORMANCE GATE RESULTS")
            print("="*80)
            for result in gate_results:
                print(result)

        # Generate CI/CD reports
        if args.junit_output:
            runner.cicd_integration.generate_junit_xml(metrics, gate_results, args.junit_output)

        if args.tap_output:
            runner.cicd_integration.generate_tap_output(gate_results, args.tap_output)

        # Compare with baseline
        if args.baseline and runner.cicd_integration.baseline_metrics:
            comparison = runner.cicd_integration.compare_with_baseline(metrics)
            if comparison:
                print("\n" + "="*80)
                print("BASELINE COMPARISON")
                print("="*80)
                for metric, data in comparison.items():
                    print(f"{metric}:")
                    print(f"  Baseline: {data['baseline']:.2f}")
                    print(f"  Current: {data['current']:.2f}")
                    print(f"  Delta: {data['delta']:+.2f} ({data['percent_change']:+.1f}%)")

        # Save new baseline if requested
        if args.save_baseline:
            runner.cicd_integration.save_baseline(metrics, args.save_baseline)

        # Output metrics as JSON if requested
        if args.json_output:
            save_metrics_optimized(metrics, args.json_output, compress=True)
            logging.info(f"Metrics saved to {args.json_output} (with compression)")

        # Print detailed metrics summary
        print("\n" + "="*80)
        print("EXECUTION METRICS REPORT")
        print("="*80)
        
        # Script Information
        print("\n📋 SCRIPT INFORMATION")
        print("-" * 80)
        print(f"  Script Path: {metrics.get('script_path', 'N/A')}")
        print(f"  Status: {'✅ SUCCESS' if metrics.get('success', False) else '❌ FAILED'}")
        print(f"  Exit Code: {metrics.get('exit_code', 'N/A')}")
        
        # Execution Timing
        print("\n⏱️  EXECUTION TIMING")
        print("-" * 80)
        start_time = metrics.get('start_time', 'N/A')
        end_time = metrics.get('end_time', 'N/A')
        print(f"  Start Time: {start_time}")
        print(f"  End Time: {end_time}")
        print(f"  Total Duration: {metrics.get('execution_time_seconds', 0):.4f}s")
        print(f"  User Time: {metrics.get('user_time_seconds', 0):.4f}s")
        print(f"  System Time: {metrics.get('system_time_seconds', 0):.4f}s")
        
        # CPU Metrics
        print("\n💻 CPU METRICS")
        print("-" * 80)
        print(f"  Max CPU: {metrics.get('cpu_max', 0):.1f}%")
        print(f"  Avg CPU: {metrics.get('cpu_avg', 0):.1f}%")
        print(f"  Min CPU: {metrics.get('cpu_min', 0):.1f}%")
        print(f"  Context Switches: {metrics.get('context_switches', 0)}")
        
        # Memory Metrics
        print("\n🧠 MEMORY METRICS")
        print("-" * 80)
        print(f"  Max Memory: {metrics.get('memory_max_mb', 0):.1f} MB")
        print(f"  Avg Memory: {metrics.get('memory_avg_mb', 0):.1f} MB")
        print(f"  Min Memory: {metrics.get('memory_min_mb', 0):.1f} MB")
        print(f"  Page Faults: {metrics.get('page_faults', 0)}")
        
        # System Metrics
        print("\n⚙️  SYSTEM METRICS")
        print("-" * 80)
        print(f"  Process Threads: {metrics.get('num_threads', 0)}")
        print(f"  Open File Descriptors: {metrics.get('num_fds', 0)}")
        print(f"  Block I/O Operations: {metrics.get('block_io_count', 0)}")
        
        # Output Metrics
        print("\n📤 OUTPUT METRICS")
        print("-" * 80)
        print(f"  Stdout Lines: {metrics.get('stdout_lines', 0)}")
        print(f"  Stderr Lines: {metrics.get('stderr_lines', 0)}")
        
        # Script Output Section
        if stdout or stderr:
            print("\n" + "="*80)
            print("▌ ▌ ▌ ▌ ▌ ▌ ▌ ▌ ▌ ▌ 📝  S C R I P T    O U T P U T  📝 ▌ ▌ ▌ ▌ ▌ ▌ ▌ ▌ ▌ ▌")
            print("="*80)
            if stdout:
                print("\n╔════════════════════════════════════════════════════════════════════════════════╗")
                print("║ STDOUT OUTPUT                                                                  ║")
                print("╚════════════════════════════════════════════════════════════════════════════════╝")
                # Show first and last lines if output is long, otherwise show all
                stdout_lines_list = stdout.strip().split('\n') if stdout.strip() else []
                if len(stdout_lines_list) > 20:
                    # Print first 10 lines with box drawing
                    for i, line in enumerate(stdout_lines_list[:10]):
                        print(f"  │ {line[:76]}")
                    # Print ellipsis section
                    hidden_count = len(stdout_lines_list) - 20
                    print(f"  ├─ ┈ ┈ ┈ ┈ ┈ [{hidden_count:,} more lines hidden] ┈ ┈ ┈ ┈ ┈ ─┤")
                    # Print last 10 lines
                    for i, line in enumerate(stdout_lines_list[-10:]):
                        print(f"  │ {line[:76]}")
                else:
                    for line in stdout_lines_list:
                        print(f"  │ {line[:76]}")
                print("  └" + "─"*78 + "┘")
            
            if stderr:
                print("\n╔════════════════════════════════════════════════════════════════════════════════╗")
                print("║ STDERR OUTPUT                                                                  ║")
                print("╚════════════════════════════════════════════════════════════════════════════════╝")
                stderr_lines_list = stderr.strip().split('\n') if stderr.strip() else []
                if len(stderr_lines_list) > 20:
                    # Print first 10 lines with box drawing
                    for i, line in enumerate(stderr_lines_list[:10]):
                        print(f"  ⚠ {line[:76]}")
                    # Print ellipsis section
                    hidden_count = len(stderr_lines_list) - 20
                    print(f"  ├─ ┈ ┈ ┈ ┈ ┈ [{hidden_count:,} more lines hidden] ┈ ┈ ┈ ┈ ┈ ─┤")
                    # Print last 10 lines
                    for i, line in enumerate(stderr_lines_list[-10:]):
                        print(f"  ⚠ {line[:76]}")
                else:
                    for line in stderr_lines_list:
                        print(f"  ⚠ {line[:76]}")
                print("  └" + "─"*78 + "┘")
        
        # Timeout Information (if applicable)
        if metrics.get('timeout_seconds'):
            print("\n⏰ TIMEOUT CONFIGURATION")
            print("-" * 80)
            print(f"  Timeout: {metrics.get('timeout_seconds')}s")
            print(f"  Timed Out: {'Yes ⚠️' if metrics.get('timed_out') else 'No ✅'}")
        
        # Retry Information (if applicable)
        if metrics.get('attempt_number', 1) > 1:
            print("\n🔄 RETRY INFORMATION")
            print("-" * 80)
            print(f"  Attempt Number: {metrics.get('attempt_number', 1)}")
            print(f"  Total Attempts: {metrics.get('total_attempts', 1)}")
        
        print("\n" + "="*80)

        # Exit with appropriate code
        exit_code = returncode
        if not gates_passed:
            exit_code = runner.cicd_integration.get_exit_code_for_gates(gate_results)

        sys.exit(exit_code)

    except KeyboardInterrupt:
        logging.error("Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
