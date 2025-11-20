"""
Python Script Runner - Enhanced Modules for v7.0+

This package contains advanced runners and integrations:
- tracers: OpenTelemetry integration for distributed tracing
- scanners: Static code analysis and dependency scanning
- security: Secret detection and vault management
- integrations: CI/CD platform integrations (GitHub Actions, GitLab CI)
- templates: Script templates and scaffolding
- workflows: DAG-based workflow orchestration
"""

__version__ = "7.3.0"
__author__ = "Python Script Runner Contributors"

try:
    from runners.tracers import TracingManager
except ImportError:
    TracingManager = None

try:
    from runners.scanners import CodeAnalyzer, DependencyVulnerabilityScanner
except ImportError:
    CodeAnalyzer = None
    DependencyVulnerabilityScanner = None

try:
    from runners.security import SecretScanner, SecretManagerAdapter
except ImportError:
    SecretScanner = None
    SecretManagerAdapter = None

try:
    from runners.workflows import WorkflowEngine, WorkflowParser
except ImportError:
    WorkflowEngine = None
    WorkflowParser = None

__all__ = [
    "TracingManager",
    "CodeAnalyzer",
    "DependencyVulnerabilityScanner",
    "SecretScanner",
    "SecretManagerAdapter",
    "WorkflowEngine",
    "WorkflowParser",
]
