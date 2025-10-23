"""
FastAPI Dashboard Backend for Python Script Runner
Provides REST API and WebSocket for real-time metric updates
Enhanced with additional analytics, caching, and robustness features
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sys
from functools import lru_cache

from fastapi import FastAPI, WebSocket, Query, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for runner import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from runner import HistoryManager, TrendAnalyzer, BaselineCalculator
except ImportError as e:
    logger.error(f"Failed to import runner modules: {e}")
    raise

app = FastAPI(
    title="Python Script Runner Dashboard API",
    version="2.0.0",
    description="Real-time monitoring and analytics for Python script execution"
)

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
history_manager: Optional[HistoryManager] = None
trend_analyzer: Optional[TrendAnalyzer] = None
baseline_calculator: Optional[BaselineCalculator] = None
connected_clients: List[WebSocket] = []
metrics_cache: Dict[str, Any] = {}
cache_update_task: Optional[asyncio.Task] = None
cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 2


def init_managers(db_path: str = "script_runner_history.db"):
    """Initialize database managers with error handling"""
    global history_manager, trend_analyzer, baseline_calculator
    try:
        history_manager = HistoryManager(db_path)
        trend_analyzer = TrendAnalyzer()
        baseline_calculator = BaselineCalculator()
        logger.info(f"Initialized managers with database at {db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize managers: {e}")
        raise


async def broadcast_metrics(data: Dict[str, Any], retry_count: int = 3):
    """Broadcast metrics to all connected WebSocket clients with retry mechanism
    
    Features:
    - Exponential backoff retry for temporary failures
    - Proper error logging at ERROR level
    - Automatic cleanup of disconnected clients
    - Timeout handling with configurable retries
    
    Args:
        data: Metrics data to broadcast
        retry_count: Number of retry attempts for each client
    """
    disconnected = []
    broadcast_stats = {'success': 0, 'failed': 0, 'retried': 0}
    
    for client in connected_clients:
        success = False
        last_error = None
        
        for attempt in range(retry_count):
            try:
                await asyncio.wait_for(client.send_json(data), timeout=5.0)
                success = True
                broadcast_stats['success'] += 1
                break
                
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"WebSocket send timeout (attempt {attempt+1}/{retry_count})")
                broadcast_stats['retried'] += 1
                
                if attempt < retry_count - 1:
                    # Exponential backoff: 0.1s, 0.2s, 0.4s
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    
            except asyncio.CancelledError as e:
                logger.error(f"WebSocket send cancelled (attempt {attempt+1}/{retry_count})")
                last_error = e
                break
                
            except Exception as e:
                last_error = e
                logger.error(f"WebSocket send failed (attempt {attempt+1}/{retry_count}): {type(e).__name__}: {e}")
                broadcast_stats['retried'] += 1
                
                if attempt < retry_count - 1:
                    # Exponential backoff
                    await asyncio.sleep(0.1 * (2 ** attempt))
        
        if not success:
            broadcast_stats['failed'] += 1
            logger.error(f"WebSocket send permanently failed after {retry_count} attempts: {last_error}")
            disconnected.append(client)
    
    # Remove permanently disconnected clients
    for client in disconnected:
        try:
            connected_clients.remove(client)
            logger.info(f"Removed disconnected WebSocket client. Remaining: {len(connected_clients)}")
        except ValueError:
            pass
    
    # Log broadcast statistics
    if broadcast_stats['retried'] > 0 or broadcast_stats['failed'] > 0:
        logger.info(f"Broadcast stats - Success: {broadcast_stats['success']}, Retried: {broadcast_stats['retried']}, Failed: {broadcast_stats['failed']}")



def get_execution_statistics(limit: int = 1000) -> Dict[str, Any]:
    """Get comprehensive execution statistics with error handling"""
    if not history_manager:
        return {}
    
    try:
        conn = sqlite3.connect(history_manager.db_path, timeout=5.0)
        cursor = conn.cursor()
        
        # Get success/failure counts
        cursor.execute("""
            SELECT 
                COUNT(*) as total_executions,
                SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN exit_code != 0 THEN 1 ELSE 0 END) as failed
            FROM executions
            LIMIT ?
        """, (limit,))
        
        row = cursor.fetchone()
        stats = {
            "total_executions": row[0] or 0,
            "successful": row[1] or 0,
            "failed": row[2] or 0,
            "success_rate": (row[1] or 0) / (row[0] or 1) * 100 if row[0] else 0
        }
        
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        return {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0
        }


def get_performance_metrics(metric_name: str = "execution_time_seconds", days: int = 7) -> Dict[str, Any]:
    """Get performance metrics with aggregations"""
    if not history_manager:
        return {}
    
    try:
        conn = sqlite3.connect(history_manager.db_path, timeout=5.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                MIN(metric_value) as min_value,
                MAX(metric_value) as max_value,
                AVG(metric_value) as avg_value,
                COUNT(*) as count
            FROM metrics
            WHERE metric_name = ?
        """, (metric_name,))
        
        row = cursor.fetchone()
        if row and row[3] > 0:
            metrics = {
                "metric": metric_name,
                "min": round(row[0] or 0, 3),
                "max": round(row[1] or 0, 3),
                "avg": round(row[2] or 0, 3),
                "count": row[3]
            }
        else:
            metrics = {
                "metric": metric_name,
                "min": 0,
                "max": 0,
                "avg": 0,
                "count": 0
            }
        
        conn.close()
        return metrics
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {
            "metric": metric_name,
            "min": 0,
            "max": 0,
            "avg": 0,
            "count": 0
        }


async def update_metrics_cache():
    """Update metrics cache periodically with error handling"""
    global cache_timestamp
    while True:
        try:
            await asyncio.sleep(CACHE_TTL_SECONDS)
            if history_manager:
                try:
                    stats = history_manager.get_database_stats()
                    exec_stats = get_execution_statistics()
                    perf_metrics = get_performance_metrics()
                    
                    global metrics_cache
                    metrics_cache = {
                        **stats,
                        "execution_statistics": exec_stats,
                        "performance_metrics": perf_metrics,
                        "cached_at": datetime.now().isoformat()
                    }
                    cache_timestamp = datetime.now()
                    
                    if connected_clients:
                        await broadcast_metrics(metrics_cache)
                except Exception as e:
                    logger.error(f"Error updating metrics cache: {e}")
        except asyncio.CancelledError:
            logger.info("Metrics cache update task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in cache update: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Initialize managers on startup"""
    global cache_update_task
    try:
        # Use root database path by default
        from pathlib import Path
        db_path = str(Path(__file__).parent.parent.parent / "script_runner_history.db")
        init_managers(db_path)
        cache_update_task = asyncio.create_task(update_metrics_cache())
        logger.info("Dashboard startup complete")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global cache_update_task
    try:
        if cache_update_task:
            cache_update_task.cancel()
        # Close all WebSocket connections
        for client in list(connected_clients):
            try:
                await client.close()
            except Exception:
                pass
        logger.info("Dashboard shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metric streaming with error handling"""
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(connected_clients)}")
    
    try:
        while True:
            try:
                if metrics_cache:
                    await asyncio.wait_for(
                        websocket.send_json(metrics_cache),
                        timeout=5.0
                    )
                await asyncio.sleep(CACHE_TTL_SECONDS)
            except asyncio.TimeoutError:
                logger.warning("WebSocket send timeout, attempting to close")
                break
            except RuntimeError:
                logger.debug("WebSocket closed")
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            connected_clients.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(connected_clients)}")
        except ValueError:
            pass


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


@app.get("/api/health")
async def health():
    """Health check endpoint with database validation"""
    try:
        if not history_manager:
            return {
                "status": "degraded",
                "message": "Database not initialized",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0"
            }
        
        # Test database connection
        try:
            conn = sqlite3.connect(history_manager.db_path)
            conn.execute("SELECT 1")
            conn.close()
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "websocket_clients": len(connected_clients),
                "cache_ttl": CACHE_TTL_SECONDS,
                "version": "2.0.0"
            }
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            return {
                "status": "error",
                "message": "Database connection failed",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0"
            }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        }


@app.get("/api/scripts")
async def get_scripts():
    """Get list of all monitored scripts"""
    if not history_manager:
        logger.warning("History manager not initialized")
        return []
    
    try:
        conn = sqlite3.connect(history_manager.db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT script_path, COUNT(*) as execution_count,
                   MAX(created_at) as last_execution,
                   SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END) as successful_runs
            FROM executions
            GROUP BY script_path
            ORDER BY last_execution DESC
        """)
        scripts = []
        for row in cursor.fetchall():
            success_rate = (row[3] or 0) / row[1] * 100 if row[1] else 0
            scripts.append({
                "path": row[0],
                "execution_count": row[1],
                "successful_runs": row[3] or 0,
                "success_rate": round(success_rate, 2),
                "last_execution": row[2]
            })
        conn.close()
        return scripts if scripts else []
    except sqlite3.Error as e:
        logger.error(f"Database error fetching scripts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching scripts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/metrics/latest")
async def get_latest_metrics(
    script_path: Optional[str] = Query(None),
    limit: int = Query(100)
):
    """Get latest execution metrics with validation"""
    if not history_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    
    if limit < 1 or limit > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 10000"
        )
    
    try:
        metrics = history_manager.get_aggregated_metrics(script_path, limit)
        return metrics or {}
    except Exception as e:
        logger.error(f"Error getting latest metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/metrics/history")
async def get_metrics_history(
    script_path: Optional[str] = Query(None),
    metric_name: str = Query("execution_time_seconds"),
    days: int = Query(7),
    limit: int = Query(1000)
):
    """Get metric time-series data with validation"""
    if not history_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 365"
        )
    
    if limit < 1 or limit > 100000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100000"
        )
    
    try:
        conn = sqlite3.connect(history_manager.db_path, timeout=5.0)
        cursor = conn.cursor()
        
        # Simple query using just the metrics table
        cursor.execute("""
            SELECT metric_name, metric_value
            FROM metrics
            WHERE metric_name = ?
            ORDER BY id DESC
            LIMIT ?
        """, (metric_name, limit))
        
        data = []
        for row in cursor.fetchall():
            data.append({
                "metric_name": row[0],
                "value": row[1]
            })
        
        conn.close()
        return {
            "metric_name": metric_name,
            "script_path": script_path or "all",
            "days": days,
            "data_points": len(data),
            "data": data
        }
    except sqlite3.Error as e:
        logger.error(f"Database error fetching metrics history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching metrics history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/stats/database")
async def get_database_stats():
    """Get database statistics with error handling"""
    if not history_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    
    try:
        stats = history_manager.get_database_stats()
        return stats or {}
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/stats/execution")
async def get_execution_stats(limit: int = Query(1000)):
    """Get execution success/failure statistics"""
    if not history_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    
    if limit < 1 or limit > 100000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100000"
        )
    
    try:
        stats = get_execution_statistics(limit)
        return stats
    except Exception as e:
        logger.error(f"Error getting execution statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/stats/performance")
async def get_performance_stats(
    metric_name: str = Query("execution_time_seconds"),
    days: int = Query(7)
):
    """Get performance metrics with aggregations"""
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 365"
        )
    
    try:
        metrics = get_performance_metrics(metric_name, days)
        return metrics
    except Exception as e:
        logger.error(f"Error getting performance statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/executions")
async def get_executions(
    script_path: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    exit_code: Optional[int] = Query(None)
):
    """Get recent executions with error handling, validation, and filtering"""
    if not history_manager:
        logger.warning("History manager not initialized for executions")
        return []
    
    if limit < 1 or limit > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 10000"
        )
    
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset cannot be negative"
        )
    
    try:
        conn = sqlite3.connect(history_manager.db_path, timeout=5.0)
        cursor = conn.cursor()
        
        query = "SELECT id, script_path, exit_code, stdout_lines, stderr_lines, created_at FROM executions WHERE 1=1"
        params = []
        
        if script_path:
            query += " AND script_path = ?"
            params.append(script_path)
        
        if exit_code is not None:
            query += " AND exit_code = ?"
            params.append(exit_code)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        executions = []
        for row in cursor.fetchall():
            executions.append({
                "id": row[0],
                "script_path": row[1],
                "exit_code": row[2],
                "stdout_lines": row[3] or 0,
                "stderr_lines": row[4] or 0,
                "timestamp": row[5],
                "success": row[2] == 0
            })
        
        conn.close()
        return executions
    except sqlite3.Error as e:
        logger.error(f"Database error fetching executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/executions/failed")
async def get_failed_executions(limit: int = Query(50), offset: int = Query(0)):
    """Get failed executions"""
    if not history_manager:
        logger.warning("History manager not initialized for failed executions")
        return []
    
    if limit < 1 or limit > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 10000"
        )
    
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset cannot be negative"
        )
    
    try:
        conn = sqlite3.connect(history_manager.db_path, timeout=5.0)
        cursor = conn.cursor()
        
        query = "SELECT id, script_path, exit_code, stdout_lines, stderr_lines, created_at FROM executions WHERE exit_code != 0"
        params = []
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        executions = []
        for row in cursor.fetchall():
            executions.append({
                "id": row[0],
                "script_path": row[1],
                "exit_code": row[2],
                "stdout_lines": row[3] or 0,
                "stderr_lines": row[4] or 0,
                "timestamp": row[5],
                "success": False
            })
        
        conn.close()
        return executions
    except sqlite3.Error as e:
        logger.error(f"Database error fetching failed executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching failed executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/metrics/available")
async def get_available_metrics():
    """Get list of available metric names"""
    if not history_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    
    try:
        conn = sqlite3.connect(history_manager.db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT metric_name FROM metrics")
        metrics = [row[0] for row in cursor.fetchall()]
        conn.close()
        return {"available_metrics": metrics}
    except Exception as e:
        logger.error(f"Error getting available metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# v7.0 FEATURE INTEGRATION - WORKFLOWS
# ============================================================================

@app.post("/api/workflows/create")
async def create_workflow(workflow_def: Dict[str, Any]):
    """Create a new workflow from definition"""
    try:
        from runners.workflows.workflow_engine import WorkflowEngine
        
        engine = WorkflowEngine()
        workflow = engine.create_workflow_from_dict(workflow_def)
        
        return {
            "success": True,
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "task_count": len(workflow.tasks),
            "message": "Workflow created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/workflows/execute/{workflow_id}")
async def execute_workflow(workflow_id: str, background_tasks: BackgroundTasks):
    """Execute a workflow asynchronously"""
    try:
        from runners.workflows.workflow_engine import WorkflowEngine
        
        async def run_workflow():
            engine = WorkflowEngine()
            result = engine.run_workflow(workflow_id)
            await broadcast_metrics({
                "type": "workflow_completed",
                "workflow_id": workflow_id,
                "result": result
            })
        
        background_tasks.add_task(run_workflow)
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": "execution_started",
            "message": "Workflow execution initiated"
        }
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/workflows/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get workflow execution status"""
    try:
        from runners.workflows.workflow_engine import WorkflowEngine
        
        engine = WorkflowEngine()
        status = engine.get_workflow_status(workflow_id)
        return status
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# v7.0 FEATURE INTEGRATION - SECURITY ANALYSIS
# ============================================================================

@app.post("/api/security/analyze-code")
async def analyze_code(file_path: str = Query(...)):
    """Run code security analysis"""
    try:
        from runners.scanners.code_analyzer import CodeAnalyzer
        
        analyzer = CodeAnalyzer()
        result = analyzer.analyze(file_path)
        
        return {
            "success": result.success,
            "file_path": file_path,
            "findings": [f.to_dict() for f in result.findings],
            "finding_count": len(result.findings),
            "critical_count": len(result.critical_findings),
            "high_count": len(result.high_findings)
        }
    except Exception as e:
        logger.error(f"Error analyzing code: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/security/scan-dependencies")
async def scan_dependencies(requirements_file: str = Query(...)):
    """Scan dependencies for vulnerabilities"""
    try:
        from runners.scanners.dependency_scanner import DependencyVulnerabilityScanner
        
        scanner = DependencyVulnerabilityScanner()
        result = scanner.scan_requirements(requirements_file)
        
        return {
            "success": result.success,
            "requirements_file": requirements_file,
            "vulnerability_count": len(result.vulnerabilities),
            "critical_count": len([v for v in result.vulnerabilities if v.severity == 'CRITICAL']),
            "vulnerabilities": [v.to_dict() for v in result.vulnerabilities]
        }
    except Exception as e:
        logger.error(f"Error scanning dependencies: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/security/scan-secrets")
async def scan_secrets(file_path: str = Query(...)):
    """Scan for hardcoded secrets"""
    try:
        from runners.security.secret_scanner import SecretScanner
        
        scanner = SecretScanner()
        result = scanner.scan_file(file_path)
        
        return {
            "success": result.success,
            "file_path": file_path,
            "secrets_found": result.has_secrets,
            "secret_count": len(result.secrets),
            "secrets": [s.to_dict() for s in result.secrets]
        }
    except Exception as e:
        logger.error(f"Error scanning secrets: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# v7.0 FEATURE INTEGRATION - CLOUD COSTS
# ============================================================================

@app.post("/api/costs/estimate")
async def estimate_costs(resources: List[Dict[str, Any]]):
    """Estimate costs for resources"""
    try:
        from runners.integrations.cloud_cost_tracker import CloudCostTracker
        
        tracker = CloudCostTracker()
        
        for resource in resources:
            tracker.add_resource(
                resource_id=resource.get('resource_id', 'unknown'),
                resource_type=resource['resource_type'],
                provider=resource['provider'],
                metrics=resource.get('metrics', {})
            )
        
        result = tracker.get_result()
        
        return {
            "success": result.success,
            "total_cost_usd": result.total_estimated_cost_usd,
            "estimates": [e.to_dict() for e in result.cost_estimates]
        }
    except Exception as e:
        logger.error(f"Error estimating costs: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/costs/monthly-summary")
async def get_monthly_summary():
    """Get monthly cost summary"""
    try:
        if history_manager is None:
            raise RuntimeError("History manager not initialized")
        
        with history_manager.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT 
                    SUM(json_extract(metrics_json, '$.total_cost_usd')) as total,
                    COUNT(*) as count
                FROM executions
                WHERE date >= date('now', '-30 days')
            """)
            result = c.fetchone()
            
            return {
                "month": datetime.now().strftime('%Y-%m'),
                "total_cost_usd": result[0] or 0.0,
                "execution_count": result[1] or 0
            }
    except Exception as e:
        logger.error(f"Error getting monthly summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# v7.0 FEATURE INTEGRATION - TRACING
# ============================================================================

@app.get("/api/traces/execution/{execution_id}")
async def get_execution_traces(execution_id: str):
    """Get traces for an execution"""
    try:
        from runners.tracers.otel_manager import TracingManager
        
        manager = TracingManager()
        
        return {
            "execution_id": execution_id,
            "traces": [],
            "message": "Traces not yet collected - ensure OTEL_EXPORTER is configured"
        }
    except Exception as e:
        logger.error(f"Error retrieving traces: {e}")
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# FRONTEND
# ============================================================================

@app.get("/")
async def serve_frontend():
    """Serve frontend HTML"""
    try:
        frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
        if frontend_path.exists():
            return FileResponse(frontend_path)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Dashboard frontend not found"}
        )
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error serving frontend"
        )


def run(host: str = "0.0.0.0", port: int = 8000, db_path: str = None):
    """Run the dashboard server with error handling"""
    try:
        # Use root database by default (where runner saves data)
        if db_path is None:
            from pathlib import Path
            db_path = str(Path(__file__).parent.parent.parent / "script_runner_history.db")
        init_managers(db_path)
        logger.info(f"Starting dashboard on {host}:{port}")
        logger.info(f"Using database: {db_path}")
        uvicorn.run(app, host=host, port=port, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Python Script Runner Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--db", default="script_runner_history.db", help="Database path")
    parser.add_argument("--log-level", default="info", help="Logging level")
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(args.log_level.upper())
    
    run(args.host, args.port, args.db)
