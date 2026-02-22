"""
Static Code Analysis Integration

Integrate Bandit and Semgrep for security scanning before execution.
Detects security vulnerabilities, best practice violations, and code quality issues.

Features:
- Bandit integration for Python security issues
- Semgrep for pattern-based code analysis
- SARIF format export
- Severity-based filtering and blocking
- Configuration-based rules
"""

import json
import subprocess
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class SeverityLevel(Enum):
    """Severity levels for findings."""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisType(Enum):
    """Types of code analysis."""
    BANDIT = "bandit"
    SEMGREP = "semgrep"


@dataclass
class Finding:
    """A code analysis finding."""
    id: str
    title: str
    description: str
    severity: SeverityLevel
    file_path: str
    line_number: int
    column_number: int = 0
    analysis_type: AnalysisType = AnalysisType.BANDIT
    rule_id: Optional[str] = None
    cve: Optional[str] = None
    recommendation: Optional[str] = None
    code_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "analysis_type": self.analysis_type.value,
            "rule_id": self.rule_id,
            "cve": self.cve,
            "recommendation": self.recommendation,
            "code_snippet": self.code_snippet,
        }


@dataclass
class AnalysisResult:
    """Result of code analysis."""
    success: bool
    findings: List[Finding]
    tool_version: str = ""
    scan_duration: float = 0.0
    files_scanned: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.errors is None:
            self.errors = []

    @property
    def critical_findings(self) -> List[Finding]:
        """Get critical findings."""
        return [f for f in self.findings if f.severity == SeverityLevel.CRITICAL]

    @property
    def high_findings(self) -> List[Finding]:
        """Get high severity findings."""
        return [f for f in self.findings if f.severity == SeverityLevel.HIGH]

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are critical or high findings."""
        return len(self.critical_findings) > 0 or len(self.high_findings) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "findings": [f.to_dict() for f in self.findings],
            "critical_findings": len(self.critical_findings),
            "high_findings": len(self.high_findings),
            "total_findings": len(self.findings),
            "tool_version": self.tool_version,
            "scan_duration": self.scan_duration,
            "files_scanned": self.files_scanned,
            "errors": self.errors,
            "has_blocking_issues": self.has_blocking_issues,
        }

    def to_sarif(self) -> Dict[str, Any]:
        """Convert to SARIF format."""
        return {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Python-Script-Runner-Scanner",
                            "version": self.tool_version,
                        }
                    },
                    "results": [
                        {
                            "ruleId": f.rule_id or f.id,
                            "message": {"text": f.description},
                            "level": self._severity_to_level(f.severity),
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": f.file_path},
                                        "region": {
                                            "startLine": f.line_number,
                                            "startColumn": f.column_number,
                                        },
                                    }
                                }
                            ],
                        }
                        for f in self.findings
                    ],
                }
            ],
        }

    @staticmethod
    def _severity_to_level(severity: SeverityLevel) -> str:
        """Convert severity to SARIF level."""
        mapping = {
            SeverityLevel.INFO: "note",
            SeverityLevel.WARNING: "warning",
            SeverityLevel.HIGH: "error",
            SeverityLevel.CRITICAL: "error",
        }
        return mapping.get(severity, "note")


class BanditAnalyzer:
    """Bandit security scanner integration."""

    def __init__(self):
        """Initialize Bandit analyzer."""
        self.logger = logging.getLogger(__name__)

    def analyze(self, file_path: str) -> AnalysisResult:
        """
        Run Bandit analysis on file.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            AnalysisResult with findings
        """
        try:
            process = subprocess.Popen(
                ["bandit", "-f", "json", file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(timeout=300)

            if process.returncode not in [0, 1]:
                return AnalysisResult(
                    success=False,
                    findings=[],
                    errors=[stderr],
                )

            # Parse JSON output
            data = json.loads(stdout)
            findings = []

            for issue in data.get("results", []):
                severity = self._parse_severity(issue.get("severity", "MEDIUM"))
                finding = Finding(
                    id=f"bandit-{issue.get('test_id')}",
                    title=issue.get("test_name", "Unknown"),
                    description=issue.get("issue_text", ""),
                    severity=severity,
                    file_path=issue.get("filename", ""),
                    line_number=issue.get("line_number", 0),
                    analysis_type=AnalysisType.BANDIT,
                    rule_id=issue.get("test_id"),
                    recommendation=f"See: {issue.get('issue_url', '')}",
                )
                findings.append(finding)

            return AnalysisResult(
                success=True,
                findings=findings,
                tool_version=data.get("metrics", {}).get("_totals", {}).get("loc", "unknown"),
                files_scanned=1,
            )

        except FileNotFoundError:
            return AnalysisResult(
                success=False,
                findings=[],
                errors=["Bandit not installed. Install: pip install bandit"],
            )
        except subprocess.TimeoutExpired:
            return AnalysisResult(
                success=False,
                findings=[],
                errors=["Bandit analysis timed out"],
            )
        except Exception as e:
            self.logger.error(f"Bandit analysis error: {e}")
            return AnalysisResult(
                success=False,
                findings=[],
                errors=[str(e)],
            )

    @staticmethod
    def _parse_severity(severity_str: str) -> SeverityLevel:
        """Parse Bandit severity string."""
        mapping = {
            "LOW": SeverityLevel.INFO,
            "MEDIUM": SeverityLevel.WARNING,
            "HIGH": SeverityLevel.HIGH,
            "CRITICAL": SeverityLevel.CRITICAL,
        }
        return mapping.get(severity_str.upper(), SeverityLevel.WARNING)


class SemgrepAnalyzer:
    """Semgrep pattern-based code analyzer."""

    def __init__(self, rules: Optional[str] = None):
        """
        Initialize Semgrep analyzer.

        Args:
            rules: Semgrep rules (auto, p/security-audit, etc.)
        """
        self.logger = logging.getLogger(__name__)
        self.rules = rules or "p/security-audit"

    def analyze(self, file_path: str) -> AnalysisResult:
        """
        Run Semgrep analysis on file.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            AnalysisResult with findings
        """
        try:
            process = subprocess.Popen(
                ["semgrep", "--json", "--config", self.rules, file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(timeout=300)

            # Semgrep returns 0 if no findings, >0 if findings
            if process.returncode not in [0, 1]:
                return AnalysisResult(
                    success=False,
                    findings=[],
                    errors=[stderr],
                )

            # Parse JSON output
            data = json.loads(stdout)
            findings = []

            for result_item in data.get("results", []):
                severity = self._parse_severity(result_item.get("extra", {}).get("severity", "WARNING"))
                finding = Finding(
                    id=f"semgrep-{result_item.get('check_id')}",
                    title=result_item.get("check_id", "Unknown"),
                    description=result_item.get("extra", {}).get("message", ""),
                    severity=severity,
                    file_path=result_item.get("path", ""),
                    line_number=result_item.get("start", {}).get("line", 0),
                    column_number=result_item.get("start", {}).get("col", 0),
                    analysis_type=AnalysisType.SEMGREP,
                    rule_id=result_item.get("check_id"),
                )
                findings.append(finding)

            return AnalysisResult(
                success=True,
                findings=findings,
                files_scanned=1,
            )

        except FileNotFoundError:
            return AnalysisResult(
                success=False,
                findings=[],
                errors=["Semgrep not installed. Install: pip install semgrep"],
            )
        except subprocess.TimeoutExpired:
            return AnalysisResult(
                success=False,
                findings=[],
                errors=["Semgrep analysis timed out"],
            )
        except Exception as e:
            self.logger.error(f"Semgrep analysis error: {e}")
            return AnalysisResult(
                success=False,
                findings=[],
                errors=[str(e)],
            )

    @staticmethod
    def _parse_severity(severity_str: str) -> SeverityLevel:
        """Parse Semgrep severity string."""
        mapping = {
            "INFO": SeverityLevel.INFO,
            "WARNING": SeverityLevel.WARNING,
            "ERROR": SeverityLevel.HIGH,
            "CRITICAL": SeverityLevel.CRITICAL,
        }
        return mapping.get(severity_str.upper(), SeverityLevel.WARNING)


class CodeAnalyzer:
    """Combined code analyzer using multiple tools."""

    def __init__(self, use_bandit: bool = True, use_semgrep: bool = True):
        """
        Initialize code analyzer.

        Args:
            use_bandit: Enable Bandit analysis
            use_semgrep: Enable Semgrep analysis
        """
        self.logger = logging.getLogger(__name__)
        self.use_bandit = use_bandit
        self.use_semgrep = use_semgrep
        self.bandit = BanditAnalyzer() if use_bandit else None
        self.semgrep = SemgrepAnalyzer() if use_semgrep else None

    def analyze(self, file_path: str) -> AnalysisResult:
        """
        Run code analysis on file.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Combined AnalysisResult
        """
        if not Path(file_path).exists():
            return AnalysisResult(
                success=False,
                findings=[],
                errors=[f"File not found: {file_path}"],
            )

        all_findings = []
        errors = []
        total_duration = 0.0
        success = True

        # Run Bandit
        if self.bandit:
            self.logger.info(f"Running Bandit on {file_path}")
            start = __import__("time").time()
            result = self.bandit.analyze(file_path)
            total_duration += __import__("time").time() - start
            all_findings.extend(result.findings)
            errors.extend(result.errors)
            success = success and result.success

        # Run Semgrep
        if self.semgrep:
            self.logger.info(f"Running Semgrep on {file_path}")
            start = __import__("time").time()
            result = self.semgrep.analyze(file_path)
            total_duration += __import__("time").time() - start
            all_findings.extend(result.findings)
            errors.extend(result.errors)
            success = success and result.success

        # Deduplicate findings by (file, line, title)
        seen = set()
        deduplicated = []
        for finding in all_findings:
            key = (finding.file_path, finding.line_number, finding.title)
            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)

        return AnalysisResult(
            success=success,
            findings=deduplicated,
            scan_duration=total_duration,
            files_scanned=1,
            errors=errors if errors else None,
        )

    def analyze_directory(self, directory: str) -> AnalysisResult:
        """
        Analyze all Python files in directory.

        Args:
            directory: Directory path to analyze

        Returns:
            Combined AnalysisResult
        """
        dir_path = Path(directory)
        all_findings = []
        errors = []
        total_duration = 0.0
        files_scanned = 0

        for py_file in dir_path.rglob("*.py"):
            self.logger.debug(f"Analyzing {py_file}")
            result = self.analyze(str(py_file))
            all_findings.extend(result.findings)
            errors.extend(result.errors or [])
            total_duration += result.scan_duration
            files_scanned += 1

        return AnalysisResult(
            success=len(errors) == 0,
            findings=all_findings,
            scan_duration=total_duration,
            files_scanned=files_scanned,
            errors=errors if errors else None,
        )
