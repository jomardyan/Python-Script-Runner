"""
Python Script Runner v7.0 - ScriptRunner Enhancement with v7 Features

This module integrates all v7.0 features (workflows, tracing, security, costs)
seamlessly into the existing ScriptRunner class while maintaining 100% backward
compatibility.

Features:
- Workflow Engine integration
- OpenTelemetry distributed tracing
- Automated security scanning
- Dependency vulnerability scanning
- Secret detection
- Multi-cloud cost tracking
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import v7 features
try:
    from runners.workflows.workflow_engine import WorkflowEngine
    from runners.tracers.otel_manager import TracingManager
    from runners.scanners.code_analyzer import CodeAnalyzer
    from runners.scanners.dependency_scanner import DependencyVulnerabilityScanner
    from runners.security.secret_scanner import SecretScanner
    from runners.integrations.cloud_cost_tracker import CloudCostTracker
    V7_FEATURES_AVAILABLE = True
except ImportError as e:
    V7_FEATURES_AVAILABLE = False
    print(f"Warning: v7 features not fully available: {e}")


logger = logging.getLogger(__name__)


class V7ScriptRunnerEnhancer:
    """Enhances ScriptRunner with v7.0 features while maintaining backward compatibility"""
    
    def __init__(self, script_runner, config: Optional[Dict[str, Any]] = None):
        """Initialize enhancer with existing ScriptRunner instance
        
        Args:
            script_runner: Existing ScriptRunner instance
            config: Configuration dict for v7 features
        """
        self.runner = script_runner
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize v7 feature managers
        self.workflow_engine = None
        self.tracing_manager = None
        self.code_analyzer = None
        self.dependency_scanner = None
        self.secret_scanner = None
        self.cost_tracker = None
        
        # Feature flags
        self.enable_workflows = self.config.get('workflows', {}).get('enabled', False)
        self.enable_tracing = self.config.get('tracing', {}).get('enabled', False)
        self.enable_security = self.config.get('security', {}).get('enabled', False)
        self.enable_costs = self.config.get('costs', {}).get('enabled', False)
        
        self._initialize_features()
    
    def _initialize_features(self):
        """Initialize all enabled v7 features"""
        if not V7_FEATURES_AVAILABLE:
            self.logger.warning("v7 features not available")
            return
        
        try:
            # Initialize workflow engine
            if self.enable_workflows:
                self.workflow_engine = WorkflowEngine()
                self.logger.info("✓ Workflow Engine initialized")
            
            # Initialize tracing
            if self.enable_tracing:
                tracing_config = self.config.get('tracing', {})
                self.tracing_manager = TracingManager(
                    service_name=tracing_config.get('service_name', 'script_runner'),
                    exporter_type=tracing_config.get('exporter_type', 'jaeger'),
                    sampling_rate=tracing_config.get('sampling_rate', 0.1)
                )
                self.logger.info("✓ Tracing Manager initialized")
            
            # Initialize security scanning
            if self.enable_security:
                self.code_analyzer = CodeAnalyzer()
                self.dependency_scanner = DependencyVulnerabilityScanner()
                self.secret_scanner = SecretScanner()
                self.logger.info("✓ Security scanners initialized")
            
            # Initialize cost tracking
            if self.enable_costs:
                self.cost_tracker = CloudCostTracker()
                self.logger.info("✓ Cost tracker initialized")
        
        except Exception as e:
            self.logger.error(f"Error initializing v7 features: {e}")
    
    def pre_execution_security_scan(self, script_path: str) -> Dict[str, Any]:
        """Run pre-execution security scanning
        
        Args:
            script_path: Path to script to scan
            
        Returns:
            Dict with security findings
        """
        if not self.enable_security or not self.code_analyzer:
            return {'success': True, 'findings': []}
        
        try:
            # Scan the script for vulnerabilities
            result = self.code_analyzer.analyze(script_path)
            
            # Check for critical findings
            if result.critical_findings and self.config.get('security', {}).get('block_on_critical', False):
                self.logger.error(f"Critical security findings detected in {script_path}")
                return {
                    'success': False,
                    'findings': [f.to_dict() for f in result.critical_findings],
                    'blocked': True
                }
            
            return {
                'success': True,
                'findings': [f.to_dict() for f in result.findings],
                'critical_count': len(result.critical_findings)
            }
        except Exception as e:
            self.logger.error(f"Security scan error: {e}")
            return {'success': False, 'error': str(e)}
    
    def scan_dependencies(self, requirements_file: str = 'requirements.txt') -> Dict[str, Any]:
        """Scan project dependencies for vulnerabilities
        
        Args:
            requirements_file: Path to requirements.txt
            
        Returns:
            Dict with vulnerability findings
        """
        if not self.enable_security or not self.dependency_scanner:
            return {'success': True, 'vulnerabilities': []}
        
        if not os.path.exists(requirements_file):
            return {'success': False, 'error': f'{requirements_file} not found'}
        
        try:
            result = self.dependency_scanner.scan_requirements(requirements_file)
            return {
                'success': result.success,
                'vulnerability_count': len(result.vulnerabilities),
                'vulnerabilities': [v.to_dict() for v in result.vulnerabilities],
                'sbom': result.sbom if hasattr(result, 'sbom') else None
            }
        except Exception as e:
            self.logger.error(f"Dependency scan error: {e}")
            return {'success': False, 'error': str(e)}
    
    def scan_secrets(self, path: str = '.') -> Dict[str, Any]:
        """Scan for hardcoded secrets
        
        Args:
            path: Path to scan (file or directory)
            
        Returns:
            Dict with detected secrets
        """
        if not self.enable_security or not self.secret_scanner:
            return {'success': True, 'secrets': []}
        
        try:
            if os.path.isfile(path):
                result = self.secret_scanner.scan_file(path)
            else:
                result = self.secret_scanner.scan_directory(path)
            
            return {
                'success': result.success if hasattr(result, 'success') else True,
                'has_secrets': result.has_secrets if hasattr(result, 'has_secrets') else False,
                'secret_count': len(result.secrets) if hasattr(result, 'secrets') else 0,
                'secrets': [s.to_dict() for s in result.secrets] if hasattr(result, 'secrets') else []
            }
        except Exception as e:
            self.logger.error(f"Secret scan error: {e}")
            return {'success': False, 'error': str(e)}
    
    def start_tracing_span(self, span_name: str):
        """Start a distributed tracing span
        
        Args:
            span_name: Name of the span
            
        Returns:
            Context manager for the span
        """
        if self.tracing_manager:
            return self.tracing_manager.trace_span(span_name)
        else:
            # Return no-op context manager
            from contextlib import contextmanager
            @contextmanager
            def noop():
                yield None
            return noop()
    
    def start_cost_tracking(self):
        """Start cloud cost tracking"""
        if self.cost_tracker:
            self.cost_tracker.start_monitoring()
            self.logger.info("Cost tracking started")
    
    def stop_cost_tracking(self) -> Dict[str, Any]:
        """Stop cost tracking and get cost report
        
        Returns:
            Dict with cost analysis
        """
        if not self.cost_tracker:
            return {}
        
        try:
            report = self.cost_tracker.get_cost_report()
            return {
                'total_estimated_cost_usd': report.total_estimated_cost_usd if hasattr(report, 'total_estimated_cost_usd') else 0,
                'cost_by_provider': report.cost_by_provider if hasattr(report, 'cost_by_provider') else {},
                'cost_by_service': report.cost_by_service if hasattr(report, 'cost_by_service') else {}
            }
        except Exception as e:
            self.logger.error(f"Cost tracking error: {e}")
            return {}


def enhance_script_runner(runner, config: Optional[Dict[str, Any]] = None) -> V7ScriptRunnerEnhancer:
    """Enhance existing ScriptRunner instance with v7 features
    
    Args:
        runner: ScriptRunner instance
        config: Configuration dict for v7 features
        
    Returns:
        V7ScriptRunnerEnhancer instance
        
    Example:
        >>> from runner import ScriptRunner
        >>> runner = ScriptRunner('script.py')
        >>> v7_enhancer = enhance_script_runner(runner, {
        ...     'workflows': {'enabled': True},
        ...     'tracing': {'enabled': True, 'sampling_rate': 0.1},
        ...     'security': {'enabled': True, 'block_on_critical': True},
        ...     'costs': {'enabled': True}
        ... })
        >>> v7_enhancer.pre_execution_security_scan('script.py')
    """
    return V7ScriptRunnerEnhancer(runner, config)


def load_v7_config(config_file: str) -> Dict[str, Any]:
    """Load v7 feature configuration from YAML file
    
    Args:
        config_file: Path to config.yaml
        
    Returns:
        Configuration dict
    """
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed, using default config")
        return {}
    
    if not os.path.exists(config_file):
        logger.warning(f"Config file {config_file} not found")
        return {}
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}
