"""
Python Script Runner - Enterprise-Grade Script Execution Engine

A comprehensive Python package for executing scripts with real-time monitoring,
alerting, analytics, and enterprise integrations.

This file provides package-level exports for convenience. The actual implementation
is in the runner.py module.

Quick Start:
    >>> from runner import ScriptRunner
    >>> runner = ScriptRunner("myscript.py")
    >>> result = runner.run_script()

See runner.py for full documentation.
"""

# Re-export from runner module for package-level convenience
try:
    from runner import (
        ScriptRunner,
        HistoryManager,
        AlertManager,
        CICDIntegration,
        PerformanceAnalyzer,
        AdvancedProfiler,
        EnterpriseIntegration,
        __version__,
        __author__,
        __license__,
    )
    
    __all__ = [
        "ScriptRunner",
        "HistoryManager",
        "AlertManager",
        "CICDIntegration",
        "PerformanceAnalyzer",
        "AdvancedProfiler",
        "EnterpriseIntegration",
        "__version__",
        "__author__",
        "__license__",
    ]
except ImportError:
    # Fallback if imported as a package before installation
    __version__ = "6.2.0"
    __author__ = "Python Script Runner Contributors"
    __license__ = "MIT"
    __all__ = []

