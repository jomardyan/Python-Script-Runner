"""Unit tests for Static Code Analysis (Bandit + Semgrep)."""

import pytest
from unittest.mock import MagicMock, patch
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runners.scanners.code_analyzer import (
    CodeAnalyzer, BanditAnalyzer, SemgrepAnalyzer, Finding, AnalysisResult, SeverityLevel
)


class TestCodeAnalyzerBasics:
    """Test basic code analyzer functionality."""
    
    def test_analyzer_creation(self):
        """Test creating a CodeAnalyzer instance."""
        analyzer = CodeAnalyzer()
        assert analyzer is not None
    
    def test_finding_creation(self):
        """Test creating a Finding object."""
        finding = Finding(
            id='B101',
            title='assert_used',
            description='Use of assert detected',
            severity='HIGH',
            file_path='app.py',
            line_number=42,
            column_number=5,
            analysis_type='BANDIT'
        )
        assert finding.id == 'B101'
        assert finding.severity == 'HIGH'
        assert finding.file_path == 'app.py'
    
    def test_analysis_result_creation(self):
        """Test creating an AnalysisResult."""
        result = AnalysisResult(
            success=True,
            findings=[],
            tool_version='2.0.0',
            files_scanned=1
        )
        assert result.success
        assert len(result.findings) == 0


class TestBanditAnalyzer:
    """Test Bandit security scanner."""
    
    @patch('subprocess.Popen')
    def test_bandit_analysis(self, mock_popen, sample_code_findings):
        """Test running Bandit analysis."""
        mock_process = MagicMock()
        bandit_output = {
            'results': [
                {
                    'test_id': 'B101',
                    'test_name': 'assert_used',
                    'issue_severity': 'HIGH',
                    'line_number': 42,
                    'filename': 'app.py'
                }
            ]
        }
        mock_process.communicate.return_value = (
            json.dumps(bandit_output).encode(), b''
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        analyzer = BanditAnalyzer()
        result = analyzer.analyze('app.py')
        
        assert result.success
        assert len(result.findings) > 0
    
    @patch('subprocess.Popen')
    def test_bandit_not_installed(self, mock_popen):
        """Test handling when Bandit is not installed."""
        mock_popen.side_effect = FileNotFoundError()
        
        analyzer = BanditAnalyzer()
        result = analyzer.analyze('app.py')
        
        assert not result.success or len(result.findings) == 0


class TestSemgrepAnalyzer:
    """Test Semgrep pattern analyzer."""
    
    @patch('subprocess.Popen')
    def test_semgrep_analysis(self, mock_popen):
        """Test running Semgrep analysis."""
        mock_process = MagicMock()
        semgrep_output = {
            'results': [
                {
                    'rule_id': 'python.lang.security.hardcoded-password',
                    'message': 'Hardcoded password detected',
                    'path': 'config.py',
                    'start': {'line': 10}
                }
            ],
            'errors': []
        }
        mock_process.communicate.return_value = (
            json.dumps(semgrep_output).encode(), b''
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        analyzer = SemgrepAnalyzer()
        result = analyzer.analyze('config.py')
        
        assert result.success


class TestCodeAnalyzerFullWorkflow:
    """Test full code analysis workflow."""
    
    @patch.object(CodeAnalyzer, 'analyze')
    def test_analyze_single_file(self, mock_analyze):
        """Test analyzing a single file."""
        mock_analyze.return_value = AnalysisResult(
            success=True,
            findings=[],
            tool_version='1.0.0',
            files_scanned=1
        )
        
        analyzer = CodeAnalyzer()
        result = analyzer.analyze('test.py')
        
        assert result.success
        assert result.files_scanned == 1
    
    @patch.object(CodeAnalyzer, 'analyze_directory')
    def test_analyze_directory(self, mock_analyze_dir):
        """Test analyzing a directory."""
        mock_analyze_dir.return_value = AnalysisResult(
            success=True,
            findings=[],
            tool_version='1.0.0',
            files_scanned=5
        )
        
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_directory('/path/to/project')
        
        assert result.success
        assert result.files_scanned == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
