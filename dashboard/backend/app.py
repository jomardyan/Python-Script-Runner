"""
FastAPI Dashboard Backend for Python Script Runner
Provides REST API and WebSocket for real-time metric updates
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

from fastapi import FastAPI, WebSocket, Query, HTTPException, status
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

app = FastAPI(title="Python Script Runner Dashboard API", version="1.0.0")

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


async def broadcast_metrics(data: Dict[str, Any]):
    """Broadcast metrics to all connected WebSocket clients with error handling"""
    disconnected = []
    for client in connected_clients:
        try:
            await asyncio.wait_for(client.send_json(data), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("WebSocket send timeout")
            disconnected.append(client)
        except Exception as e:
            logger.debug(f"Failed to send metrics to client: {e}")
            disconnected.append(client)
    
    # Remove disconnected clients
    for client in disconnected:
        try:
            connected_clients.remove(client)
        except ValueError:
            pass


@app.on_event("startup")
async def startup_event():
    """Initialize managers on startup"""
    global cache_update_task
    try:
        init_managers()
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


async def update_metrics_cache():
    """Update metrics cache periodically with error handling"""
    while True:
        try:
            await asyncio.sleep(2)  # Update every 2 seconds
            if history_manager:
                try:
                    stats = history_manager.get_database_stats()
                    global metrics_cache
                    metrics_cache = stats
                    if connected_clients:
                        await broadcast_metrics(stats)
                except Exception as e:
                    logger.error(f"Error updating metrics cache: {e}")
        except asyncio.CancelledError:
            logger.info("Metrics cache update task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in cache update: {e}")
            await asyncio.sleep(5)  # Wait before retrying


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metric streaming with error handling"""
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(connected_clients)}")
    
    try:
        while True:
            # Send cached metrics every 2 seconds
            try:
                if metrics_cache:
                    await asyncio.wait_for(
                        websocket.send_json(metrics_cache),
                        timeout=5.0
                    )
                await asyncio.sleep(2)
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
                "timestamp": datetime.now().isoformat()
            }
        
        # Test database connection
        try:
            conn = sqlite3.connect(history_manager.db_path)
            conn.execute("SELECT 1")
            conn.close()
            return {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "websocket_clients": len(connected_clients)
            }
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            return {
                "status": "error",
                "message": "Database connection failed",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
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
                   MAX(timestamp) as last_execution
            FROM executions
            GROUP BY script_path
            ORDER BY last_execution DESC
        """)
        scripts = []
        for row in cursor.fetchall():
            scripts.append({
                "path": row[0],
                "execution_count": row[1],
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
        
        query = """
            SELECT m.timestamp, m.value
            FROM metrics m
            JOIN executions e ON m.execution_id = e.id
            WHERE m.metric_name = ?
            AND m.timestamp >= datetime('now', ? || ' days')
        """
        params = [metric_name, -days]
        
        if script_path:
            query += " AND e.script_path = ?"
            params.append(script_path)
        
        query += " ORDER BY m.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        data = []
        for row in cursor.fetchall():
            data.append({
                "timestamp": row[0],
                "value": row[1]
            })
        
        conn.close()
        return {
            "metric_name": metric_name,
            "script_path": script_path or "all",
            "days": days,
            "data_points": len(data),
            "data": list(reversed(data))
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


@app.get("/api/executions")
async def get_executions(
    script_path: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """Get recent executions with error handling and validation"""
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
        
        query = "SELECT id, script_path, exit_code, stdout, stderr, timestamp FROM executions"
        params = []
        
        if script_path:
            query += " WHERE script_path = ?"
            params.append(script_path)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        executions = []
        for row in cursor.fetchall():
            executions.append({
                "id": row[0],
                "script_path": row[1],
                "exit_code": row[2],
                "stdout": row[3][:500] if row[3] else "",  # First 500 chars
                "stderr": row[4][:500] if row[4] else "",
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


def run(host: str = "0.0.0.0", port: int = 8000, db_path: str = "script_runner_history.db"):
    """Run the dashboard server with error handling"""
    try:
        init_managers(db_path)
        logger.info(f"Starting dashboard on {host}:{port}")
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
