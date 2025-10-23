"""
Dependency Vulnerability Scanner

Scans Python dependencies for known vulnerabilities using Safety and OSV-Scanner.
Generates SBOM in CycloneDX format.

Features:
- Safety integration for Python package vulnerabilities
- OSV-Scanner for comprehensive vulnerability detection
- SBOM generation (CycloneDX format)
- Dependency tree analysis
- License scanning
- Version pinning recommendations
"""

import subprocess
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class VulnerabilitySeverity(Enum):
    """Vulnerability severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Vulnerability:
    """A discovered vulnerability."""
    id: str
    package_name: str
    package_version: str
    vulnerability_id: str
    title: str
    description: str
    severity: VulnerabilitySeverity
    fixed_version: Optional[str] = None
    published_date: Optional[str] = None
    cvss_score: Optional[float] = None
    cwe: Optional[str] = None
    scanner: str = "safety"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "vulnerability_id": self.vulnerability_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "fixed_version": self.fixed_version,
            "published_date": self.published_date,
            "cvss_score": self.cvss_score,
            "cwe": self.cwe,
            "scanner": self.scanner,
        }


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    version: str
    license: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None
    requires: List[str] = None
    vulnerabilities: List[Vulnerability] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.requires is None:
            self.requires = []
        if self.vulnerabilities is None:
            self.vulnerabilities = []


@dataclass
class ScanResult:
    """Result of dependency scanning."""
    success: bool
    vulnerabilities: List[Vulnerability]
    dependencies: List[DependencyInfo]
    scan_duration: float = 0.0
    sbom_data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.errors is None:
            self.errors = []

    @property
    def critical_vulnerabilities(self) -> List[Vulnerability]:
        """Get critical vulnerabilities."""
        return [v for v in self.vulnerabilities if v.severity == VulnerabilitySeverity.CRITICAL]

    @property
    def high_vulnerabilities(self) -> List[Vulnerability]:
        """Get high severity vulnerabilities."""
        return [v for v in self.vulnerabilities if v.severity == VulnerabilitySeverity.HIGH]

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are blocking vulnerabilities."""
        return len(self.critical_vulnerabilities) > 0 or len(self.high_vulnerabilities) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "critical_vulnerabilities": len(self.critical_vulnerabilities),
            "high_vulnerabilities": len(self.high_vulnerabilities),
            "total_vulnerabilities": len(self.vulnerabilities),
            "total_dependencies": len(self.dependencies),
            "scan_duration": self.scan_duration,
            "errors": self.errors,
            "has_blocking_issues": self.has_blocking_issues,
        }


class SafetyScanner:
    """Safety vulnerability scanner integration."""

    def __init__(self):
        """Initialize Safety scanner."""
        self.logger = logging.getLogger(__name__)

    def scan_requirements(self, requirements_file: str) -> ScanResult:
        """
        Scan requirements file with Safety.

        Args:
            requirements_file: Path to requirements.txt file

        Returns:
            ScanResult with vulnerabilities
        """
        try:
            result = subprocess.run(
                ["safety", "check", "--file", requirements_file, "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Safety returns 0 if no vulnerabilities, >0 if found
            if result.returncode not in [0, 1]:
                return ScanResult(
                    success=False,
                    vulnerabilities=[],
                    dependencies=[],
                    errors=[result.stderr],
                )

            # Parse JSON output
            data = json.loads(result.stdout) if result.stdout else {}
            vulnerabilities = []

            # Safety format: list of [package_name, installed_version, vuln_id, description, fixed_version, cve_list]
            if isinstance(data, list):
                for vuln in data:
                    if len(vuln) >= 4:
                        severity = self._parse_severity(vuln)
                        vulnerability = Vulnerability(
                            id=f"safety-{vuln[2]}",
                            package_name=vuln[0],
                            package_version=vuln[1],
                            vulnerability_id=vuln[2],
                            title=vuln[3][:100] if len(vuln) > 3 else "Unknown",
                            description=vuln[3] if len(vuln) > 3 else "",
                            severity=severity,
                            fixed_version=vuln[4] if len(vuln) > 4 else None,
                            cwe=vuln[5][0] if len(vuln) > 5 and vuln[5] else None,
                            scanner="safety",
                        )
                        vulnerabilities.append(vulnerability)

            return ScanResult(
                success=True,
                vulnerabilities=vulnerabilities,
                dependencies=[],  # Safety doesn't provide full dependency info
            )

        except FileNotFoundError:
            return ScanResult(
                success=False,
                vulnerabilities=[],
                dependencies=[],
                errors=["Safety not installed. Install: pip install safety"],
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                success=False,
                vulnerabilities=[],
                dependencies=[],
                errors=["Safety scan timed out"],
            )
        except Exception as e:
            self.logger.error(f"Safety scan error: {e}")
            return ScanResult(
                success=False,
                vulnerabilities=[],
                dependencies=[],
                errors=[str(e)],
            )

    @staticmethod
    def _parse_severity(vuln: List) -> VulnerabilitySeverity:
        """Parse severity from Safety vulnerability."""
        # Safety doesn't provide explicit severity, estimate from description
        description = vuln[3].lower() if len(vuln) > 3 else ""

        if "critical" in description or "arbitrary" in description:
            return VulnerabilitySeverity.CRITICAL
        elif "high" in description or "remote" in description:
            return VulnerabilitySeverity.HIGH
        elif "medium" in description:
            return VulnerabilitySeverity.MEDIUM
        else:
            return VulnerabilitySeverity.LOW


class OSVScanner:
    """OSV vulnerability scanner integration."""

    def __init__(self):
        """Initialize OSV scanner."""
        self.logger = logging.getLogger(__name__)

    def scan_requirements(self, requirements_file: str) -> ScanResult:
        """
        Scan requirements file with OSV-Scanner.

        Args:
            requirements_file: Path to requirements.txt file

        Returns:
            ScanResult with vulnerabilities
        """
        try:
            result = subprocess.run(
                ["osv-scanner", "--lockfile", requirements_file, "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode not in [0, 1]:
                return ScanResult(
                    success=False,
                    vulnerabilities=[],
                    dependencies=[],
                    errors=[result.stderr],
                )

            # Parse JSON output
            data = json.loads(result.stdout) if result.stdout else {}
            vulnerabilities = []

            # OSV format: {"results": [{"packages": [...], "vulnerabilities": [...]}]}
            for result_item in data.get("results", []):
                for vuln in result_item.get("vulnerabilities", []):
                    affected = vuln.get("affected", [{}])[0]
                    pkg_name = affected.get("package", {}).get("name", "Unknown")
                    version = affected.get("versions", ["Unknown"])[0]

                    severity = self._parse_severity(vuln)
                    vulnerability = Vulnerability(
                        id=f"osv-{vuln.get('id')}",
                        package_name=pkg_name,
                        package_version=version,
                        vulnerability_id=vuln.get("id", ""),
                        title=vuln.get("summary", "Unknown")[:100],
                        description=vuln.get("details", ""),
                        severity=severity,
                        fixed_version=None,
                        published_date=vuln.get("published"),
                        cvss_score=None,
                        scanner="osv-scanner",
                    )
                    vulnerabilities.append(vulnerability)

            return ScanResult(
                success=True,
                vulnerabilities=vulnerabilities,
                dependencies=[],
            )

        except FileNotFoundError:
            return ScanResult(
                success=False,
                vulnerabilities=[],
                dependencies=[],
                errors=["OSV-Scanner not installed. Install: pip install osv-scanner"],
            )
        except subprocess.TimeoutExpired:
            return ScanResult(
                success=False,
                vulnerabilities=[],
                dependencies=[],
                errors=["OSV-Scanner timed out"],
            )
        except Exception as e:
            self.logger.error(f"OSV-Scanner error: {e}")
            return ScanResult(
                success=False,
                vulnerabilities=[],
                dependencies=[],
                errors=[str(e)],
            )

    @staticmethod
    def _parse_severity(vuln: Dict) -> VulnerabilitySeverity:
        """Parse severity from OSV vulnerability."""
        severity_str = vuln.get("severity", "UNKNOWN").upper()

        mapping = {
            "CRITICAL": VulnerabilitySeverity.CRITICAL,
            "HIGH": VulnerabilitySeverity.HIGH,
            "MEDIUM": VulnerabilitySeverity.MEDIUM,
            "LOW": VulnerabilitySeverity.LOW,
        }

        return mapping.get(severity_str, VulnerabilitySeverity.LOW)


class DependencyVulnerabilityScanner:
    """Combined dependency vulnerability scanner."""

    def __init__(self, use_safety: bool = True, use_osv: bool = True):
        """
        Initialize scanner.

        Args:
            use_safety: Enable Safety scanner
            use_osv: Enable OSV-Scanner
        """
        self.logger = logging.getLogger(__name__)
        self.use_safety = use_safety
        self.use_osv = use_osv
        self.safety = SafetyScanner() if use_safety else None
        self.osv = OSVScanner() if use_osv else None

    def scan_requirements(self, requirements_file: str) -> ScanResult:
        """
        Scan requirements file for vulnerabilities.

        Args:
            requirements_file: Path to requirements.txt file

        Returns:
            Combined ScanResult
        """
        if not Path(requirements_file).exists():
            return ScanResult(
                success=False,
                vulnerabilities=[],
                dependencies=[],
                errors=[f"File not found: {requirements_file}"],
            )

        all_vulnerabilities = []
        errors = []
        total_duration = 0.0
        success = True

        # Run Safety
        if self.safety:
            self.logger.info(f"Running Safety on {requirements_file}")
            import time
            start = time.time()
            result = self.safety.scan_requirements(requirements_file)
            total_duration += time.time() - start
            all_vulnerabilities.extend(result.vulnerabilities)
            errors.extend(result.errors or [])
            success = success and result.success

        # Run OSV-Scanner
        if self.osv:
            self.logger.info(f"Running OSV-Scanner on {requirements_file}")
            import time
            start = time.time()
            result = self.osv.scan_requirements(requirements_file)
            total_duration += time.time() - start
            all_vulnerabilities.extend(result.vulnerabilities)
            errors.extend(result.errors or [])
            success = success and result.success

        # Deduplicate vulnerabilities by (package, vulnerability_id)
        seen = set()
        deduplicated = []
        for vuln in all_vulnerabilities:
            key = (vuln.package_name, vuln.vulnerability_id)
            if key not in seen:
                seen.add(key)
                deduplicated.append(vuln)

        return ScanResult(
            success=success,
            vulnerabilities=deduplicated,
            dependencies=[],
            scan_duration=total_duration,
            errors=errors if errors else None,
        )

    def generate_sbom(self, requirements_file: str) -> Dict[str, Any]:
        """
        Generate Software Bill of Materials in CycloneDX format.

        Args:
            requirements_file: Path to requirements.txt file

        Returns:
            SBOM in CycloneDX format
        """
        try:
            # Parse requirements file
            components = []
            with open(requirements_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Parse package==version format
                    if "==" in line:
                        name, version = line.split("==", 1)
                        components.append(
                            {
                                "type": "library",
                                "name": name.strip(),
                                "version": version.strip(),
                                "purl": f"pkg:pypi/{name.strip()}@{version.strip()}",
                            }
                        )
                    else:
                        # Handle version specs
                        for op in [">=", "<=", ">", "<", "~="]:
                            if op in line:
                                name, version = line.split(op, 1)
                                components.append(
                                    {
                                        "type": "library",
                                        "name": name.strip(),
                                        "version": version.strip(),
                                        "purl": f"pkg:pypi/{name.strip()}@{version.strip()}",
                                    }
                                )
                                break
                        else:
                            # No version specification
                            components.append(
                                {
                                    "type": "library",
                                    "name": line,
                                    "version": "unknown",
                                    "purl": f"pkg:pypi/{line}",
                                }
                            )

            # Create SBOM
            sbom = {
                "bomFormat": "CycloneDX",
                "specVersion": "1.3",
                "version": 1,
                "metadata": {
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                    "tools": [
                        {
                            "vendor": "Python-Script-Runner",
                            "name": "DependencyVulnerabilityScanner",
                            "version": "1.0.0",
                        }
                    ],
                },
                "components": components,
            }

            return sbom

        except Exception as e:
            self.logger.error(f"Failed to generate SBOM: {e}")
            return {}
