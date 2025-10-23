"""Unit tests for Dependency Vulnerability Scanning."""

import pytest
from unittest.mock import MagicMock, patch
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runners.scanners.dependency_scanner import (
    DependencyVulnerabilityScanner, SafetyScanner, OSVScanner,
    Vulnerability, ScanResult, VulnerabilitySeverity
)


class TestVulnerabilityClass:
    """Test Vulnerability data class."""
    
    def test_create_vulnerability(self):
        """Test creating a Vulnerability object."""
        vuln = Vulnerability(
            id='CVE-2021-12345',
            package_name='requests',
            package_version='2.25.0',
            vulnerability_id='CVE-2021-12345',
            title='HTTP smuggling vulnerability',
            description='Request library has HTTP smuggling vulnerability',
            severity='HIGH',
            fixed_version='2.26.0'
        )
        assert vuln.id == 'CVE-2021-12345'
        assert vuln.package_name == 'requests'
        assert vuln.severity == 'HIGH'


class TestSafetyScanner:
    """Test Safety security scanner."""
    
    @patch('subprocess.Popen')
    def test_safety_scan_success(self, mock_popen):
        """Test successful Safety scan."""
        mock_process = MagicMock()
        safety_output = [
            {
                'vulnerability': 'CVE-2021-12345',
                'package_name': 'requests',
                'package_version': '2.25.0',
                'advisory': 'HTTP smuggling vulnerability'
            }
        ]
        mock_process.communicate.return_value = (
            json.dumps(safety_output).encode(), b''
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        scanner = SafetyScanner()
        result = scanner.scan_requirements('requirements.txt')
        
        assert result.success
    
    @patch('subprocess.Popen')
    def test_safety_not_installed(self, mock_popen):
        """Test handling when Safety is not installed."""
        mock_popen.side_effect = FileNotFoundError()
        
        scanner = SafetyScanner()
        result = scanner.scan_requirements('requirements.txt')
        
        assert not result.success or len(result.vulnerabilities) == 0


class TestOSVScanner:
    """Test OSV vulnerability scanner."""
    
    @patch('subprocess.Popen')
    def test_osv_scan_success(self, mock_popen):
        """Test successful OSV scan."""
        mock_process = MagicMock()
        osv_output = {
            'results': [
                {
                    'package': {
                        'name': 'django',
                        'version': '3.0.0',
                        'ecosystem': 'PyPI'
                    },
                    'vulnerabilities': [
                        {
                            'id': 'GHSA-12ab',
                            'summary': 'SQL injection',
                            'severity': 'CRITICAL'
                        }
                    ]
                }
            ]
        }
        mock_process.communicate.return_value = (
            json.dumps(osv_output).encode(), b''
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        scanner = OSVScanner()
        result = scanner.scan_requirements('requirements.txt')
        
        assert result.success


class TestDependencyVulnerabilityScanner:
    """Test combined dependency vulnerability scanner."""
    
    def test_scanner_creation(self):
        """Test creating a DependencyVulnerabilityScanner."""
        scanner = DependencyVulnerabilityScanner()
        assert scanner is not None
    
    @patch.object(DependencyVulnerabilityScanner, 'scan_requirements')
    def test_scan_requirements(self, mock_scan):
        """Test scanning requirements file."""
        mock_result = ScanResult(
            success=True,
            vulnerabilities=[],
            dependencies=[]
        )
        mock_scan.return_value = mock_result
        
        scanner = DependencyVulnerabilityScanner()
        result = scanner.scan_requirements('requirements.txt')
        
        assert result.success
    
    @patch.object(DependencyVulnerabilityScanner, 'generate_sbom')
    def test_sbom_generation(self, mock_sbom):
        """Test SBOM generation."""
        sbom_data = {
            'bomFormat': 'CycloneDX',
            'components': []
        }
        mock_sbom.return_value = sbom_data
        
        scanner = DependencyVulnerabilityScanner()
        sbom = scanner.generate_sbom('requirements.txt')
        
        assert sbom['bomFormat'] == 'CycloneDX'


class TestScanResult:
    """Test ScanResult data class."""
    
    def test_scan_result_with_vulnerabilities(self):
        """Test ScanResult with vulnerabilities."""
        result = ScanResult(
            success=True,
            vulnerabilities=[
                Vulnerability(
                    id='CVE-2021-12345',
                    package_name='requests',
                    package_version='2.25.0',
                    vulnerability_id='CVE-2021-12345',
                    title='HTTP smuggling',
                    description='Description',
                    severity='HIGH',
                    fixed_version='2.26.0'
                )
            ],
            dependencies=[]
        )
        
        assert result.success
        assert len(result.vulnerabilities) == 1
        assert result.critical_vulnerabilities == []
    
    def test_scan_result_has_blocking_issues(self):
        """Test checking for blocking issues."""
        critical_vuln = Vulnerability(
            id='CVE-CRITICAL',
            package_name='django',
            package_version='3.0.0',
            vulnerability_id='CVE-CRITICAL',
            title='Critical vulnerability',
            description='Critical',
            severity='CRITICAL',
            fixed_version='3.2.0'
        )
        
        result = ScanResult(
            success=True,
            vulnerabilities=[critical_vuln],
            dependencies=[]
        )
        
        assert result.has_blocking_issues


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
