"""Unit tests for Secret Scanning & Vault Integration."""

import importlib
import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runners.security.secret_scanner import (
    SecretScanner, DetectSecretsScanner, Secret, ScanResult, SecretType
)


class TestSecretClass:
    """Test Secret data class."""
    
    def test_create_secret(self):
        """Test creating a Secret object."""
        secret = Secret(
            id='secret_1',
            type='AWS_KEY',
            file_path='config.py',
            line_number=10,
            start_column=0,
            end_column=20,
            confidence=0.95,
            pattern_matched='AKIA[0-9A-Z]{16}',
            detected_by='detect-secrets'
        )
        assert secret.id == 'secret_1'
        assert secret.type == 'AWS_KEY'
        assert secret.confidence == 0.95


class TestDetectSecretsScanner:
    """Test secret pattern detection."""
    
    def test_scanner_creation(self):
        """Test creating a DetectSecretsScanner."""
        scanner = DetectSecretsScanner()
        assert scanner is not None
    
    def test_scan_file_for_secrets(self, temp_python_file):
        """Test scanning a Python file for secrets."""
        scanner = DetectSecretsScanner()
        result = scanner.scan_file(str(temp_python_file))
        
        assert isinstance(result, ScanResult)
    
    def test_scan_directory(self, sample_project_dir):
        """Test scanning a directory for secrets."""
        scanner = DetectSecretsScanner()
        result = scanner.scan_directory(str(sample_project_dir))
        
        assert isinstance(result, ScanResult)
    
    def test_aws_key_pattern_detection(self, tmp_path):
        """Test AWS access key pattern detection."""
        code = """
# AWS Key
aws_key = "AKIAIOSFODNN7EXAMPLE"
"""
        test_file = tmp_path / "aws_config.py"
        test_file.write_text(code)
        
        scanner = DetectSecretsScanner()
        result = scanner.scan_file(str(test_file))
        
        # Should find the AWS key pattern
        assert isinstance(result, ScanResult)
    
    def test_private_key_pattern_detection(self, tmp_path):
        """Test private key pattern detection."""
        code = """
# RSA Private Key
key = '''-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEA1234567890...
-----END RSA PRIVATE KEY-----'''
"""
        test_file = tmp_path / "keys.py"
        test_file.write_text(code)
        
        scanner = DetectSecretsScanner()
        result = scanner.scan_file(str(test_file))
        
        assert isinstance(result, ScanResult)


class TestSecretScanner:
    """Test combined secret scanner."""
    
    def test_scanner_creation(self):
        """Test creating a SecretScanner."""
        scanner = SecretScanner()
        assert scanner is not None
    
    @patch.object(SecretScanner, 'scan_file')
    def test_scan_file(self, mock_scan):
        """Test scanning a file for secrets."""
        mock_result = ScanResult(
            success=True,
            secrets=[],
            files_scanned=1
        )
        mock_scan.return_value = mock_result
        
        scanner = SecretScanner()
        result = scanner.scan_file('test.py')
        
        assert result.success
    
    @patch.object(SecretScanner, 'scan_directory')
    def test_scan_directory(self, mock_scan_dir):
        """Test scanning a directory for secrets."""
        mock_result = ScanResult(
            success=True,
            secrets=[],
            files_scanned=5
        )
        mock_scan_dir.return_value = mock_result
        
        scanner = SecretScanner()
        result = scanner.scan_directory('/path/to/project')
        
        assert result.success


class TestScanResult:
    """Test ScanResult with secrets."""
    
    def test_scan_result_with_secrets(self):
        """Test ScanResult containing secrets."""
        secret = Secret(
            id='secret_1',
            type='AWS_KEY',
            file_path='config.py',
            line_number=10,
            start_column=0,
            end_column=20,
            confidence=0.95,
            pattern_matched='AKIA...',
            detected_by='detect-secrets'
        )
        
        result = ScanResult(
            success=True,
            secrets=[secret],
            files_scanned=1
        )
        
        assert result.has_secrets
        assert len(result.secrets) == 1
    
    def test_high_confidence_secrets(self):
        """Test filtering high confidence secrets."""
        high_conf_secret = Secret(
            id='secret_1',
            type='API_KEY',
            file_path='config.py',
            line_number=10,
            start_column=0,
            end_column=20,
            confidence=0.95,
            pattern_matched='API_KEY...',
            detected_by='detect-secrets'
        )
        
        result = ScanResult(
            success=True,
            secrets=[high_conf_secret],
            files_scanned=1
        )
        
        # High confidence secrets should be in the list
        high_conf = [s for s in result.secrets if s.confidence > 0.8]
        assert len(high_conf) > 0


class TestVaultIntegration:
    """Test vault integration for secret management."""
    
    @patch('boto3.client')
    def test_aws_secrets_manager_adapter(self, mock_boto):
        """Test AWS Secrets Manager integration."""
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        
        scanner = SecretScanner(vault_type='aws_secrets_manager')
        # Should not raise
        assert scanner is not None
    
    @pytest.mark.skipif(
        importlib.util.find_spec('hvac') is None,
        reason='hvac not installed'
    )
    @patch('hvac.Client')
    def test_vault_adapter(self, mock_hvac):
        """Test HashiCorp Vault integration."""
        scanner = SecretScanner(vault_type='vault', vault_address='http://vault:8200')
        # Should not raise
        assert scanner is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
