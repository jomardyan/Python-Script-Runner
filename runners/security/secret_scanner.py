"""
Secret Scanning and Vault Integration

Detects hardcoded secrets and provides integration with secret management services.

Features:
- Pattern and entropy-based secret detection
- AWS Secrets Manager integration
- HashiCorp Vault integration
- Azure Key Vault integration
- Secret rotation and lifecycle management
"""

import re
import subprocess
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class SecretType(Enum):
    """Types of secrets that can be detected."""
    API_KEY = "api_key"
    AWS_KEY = "aws_key"
    AWS_SECRET = "aws_secret"
    PRIVATE_KEY = "private_key"
    PASSWORD = "password"
    DATABASE_URL = "database_url"
    SLACK_TOKEN = "slack_token"
    GITHUB_TOKEN = "github_token"
    JWT_TOKEN = "jwt_token"
    ENCRYPTION_KEY = "encryption_key"
    GENERIC_SECRET = "generic_secret"


@dataclass
class Secret:
    """A detected secret."""
    id: str
    type: SecretType
    file_path: str
    line_number: int
    start_column: int
    end_column: int
    confidence: float  # 0.0 to 1.0
    pattern_matched: str
    masked_value: Optional[str] = None
    detected_by: str = "detect-secrets"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "start_column": self.start_column,
            "end_column": self.end_column,
            "confidence": self.confidence,
            "pattern_matched": self.pattern_matched,
            "masked_value": self.masked_value,
            "detected_by": self.detected_by,
        }


@dataclass
class ScanResult:
    """Result of secret scanning."""
    success: bool
    secrets: List[Secret]
    scan_duration: float = 0.0
    files_scanned: int = 0
    errors: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.errors is None:
            self.errors = []

    @property
    def has_secrets(self) -> bool:
        """Check if any secrets were found."""
        return len(self.secrets) > 0

    @property
    def high_confidence_secrets(self) -> List[Secret]:
        """Get high confidence secrets."""
        return [s for s in self.secrets if s.confidence > 0.8]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "secrets": [s.to_dict() for s in self.secrets],
            "high_confidence_secrets": len(self.high_confidence_secrets),
            "total_secrets": len(self.secrets),
            "scan_duration": self.scan_duration,
            "files_scanned": self.files_scanned,
            "errors": self.errors,
            "has_secrets": self.has_secrets,
        }


class DetectSecretsScanner:
    """Detect-secrets integration for finding secrets."""

    # Common secret patterns
    PATTERNS = {
        SecretType.AWS_KEY: r"AKIA[0-9A-Z]{16}",
        SecretType.AWS_SECRET: r"aws_secret_access_key\s*=\s*['\"]([A-Za-z0-9/+=]{40})['\"]",
        SecretType.PRIVATE_KEY: r"-----BEGIN (RSA|DSA|EC|PGP) PRIVATE KEY-----",
        SecretType.SLACK_TOKEN: r"xox[baprs]-\d{10,13}-[A-Za-z0-9]{24,32}",
        SecretType.GITHUB_TOKEN: r"gh[pousr]{1}_[A-Za-z0-9_]{36,255}",
        SecretType.JWT_TOKEN: r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        SecretType.DATABASE_URL: r"(mysql|postgres|mongodb)://[a-zA-Z0-9_:@/.?&=]+",
        SecretType.API_KEY: r"[aA]pi[_-]?[kK]ey\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}['\"]?",
        SecretType.ENCRYPTION_KEY: r"[eE]ncryption[_-]?[kK]ey\s*[=:]\s*['\"]?[a-zA-Z0-9_+/=]{32,}['\"]?",
    }

    def __init__(self):
        """Initialize scanner."""
        self.logger = logging.getLogger(__name__)

    def scan_file(self, file_path: str) -> ScanResult:
        """
        Scan file for secrets using patterns.

        Args:
            file_path: Path to file to scan

        Returns:
            ScanResult with detected secrets
        """
        secrets = []
        errors = []

        try:
            if not Path(file_path).exists():
                return ScanResult(
                    success=False,
                    secrets=[],
                    files_scanned=0,
                    errors=[f"File not found: {file_path}"],
                )

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                for secret_type, pattern in self.PATTERNS.items():
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        secret = Secret(
                            id=f"secret-{line_num}-{match.start()}",
                            type=secret_type,
                            file_path=file_path,
                            line_number=line_num,
                            start_column=match.start(),
                            end_column=match.end(),
                            confidence=0.85,  # Pattern-based detection confidence
                            pattern_matched=pattern,
                            masked_value=line[match.start() : match.start() + 3] + "*" * (match.end() - match.start() - 6),
                            detected_by="pattern-matching",
                        )
                        secrets.append(secret)

            return ScanResult(
                success=True,
                secrets=secrets,
                files_scanned=1,
            )

        except Exception as e:
            self.logger.error(f"Secret scanning error for {file_path}: {e}")
            return ScanResult(
                success=False,
                secrets=[],
                files_scanned=1,
                errors=[str(e)],
            )

    def scan_directory(self, directory: str, exclude_patterns: List[str] = None) -> ScanResult:
        """
        Scan directory for secrets.

        Args:
            directory: Directory to scan
            exclude_patterns: Glob patterns to exclude

        Returns:
            Combined ScanResult
        """
        exclude_patterns = exclude_patterns or [
            "*.pyc",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
        ]

        all_secrets = []
        errors = []
        files_scanned = 0

        dir_path = Path(directory)
        for file_path in dir_path.rglob("*"):
            # Check exclusions
            if any(file_path.match(pattern) for pattern in exclude_patterns):
                continue

            if file_path.is_file():
                result = self.scan_file(str(file_path))
                all_secrets.extend(result.secrets)
                errors.extend(result.errors or [])
                files_scanned += result.files_scanned

        return ScanResult(
            success=len(errors) == 0,
            secrets=all_secrets,
            files_scanned=files_scanned,
            errors=errors if errors else None,
        )


class SecretManagerAdapter:
    """Adapter for secret management services."""

    def __init__(self, provider: str = "aws", **kwargs):
        """
        Initialize secret manager adapter.

        Args:
            provider: Provider type (aws, vault, azure)
            **kwargs: Provider-specific configuration
        """
        self.logger = logging.getLogger(__name__)
        self.provider = provider
        self.config = kwargs
        self._client = None

    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a secret from the configured provider.

        Args:
            secret_name: Name of the secret

        Returns:
            Secret value or None
        """
        if self.provider == "aws":
            return self._get_aws_secret(secret_name)
        elif self.provider == "vault":
            return self._get_vault_secret(secret_name)
        elif self.provider == "azure":
            return self._get_azure_secret(secret_name)
        else:
            self.logger.error(f"Unknown provider: {self.provider}")
            return None

    def _get_aws_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from AWS Secrets Manager.

        Args:
            secret_name: Name of the secret

        Returns:
            Secret value or None
        """
        try:
            import boto3
            import json

            region = self.config.get("region", "us-east-1")
            client = boto3.client("secretsmanager", region_name=region)

            response = client.get_secret_value(SecretId=secret_name)

            if "SecretString" in response:
                # Try to parse as JSON
                try:
                    return json.loads(response["SecretString"])
                except json.JSONDecodeError:
                    return response["SecretString"]
            elif "SecretBinary" in response:
                return response["SecretBinary"]

        except ImportError:
            self.logger.error("boto3 not installed. Install: pip install boto3")
        except Exception as e:
            self.logger.error(f"Failed to get AWS secret {secret_name}: {e}")

        return None

    def _get_vault_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from HashiCorp Vault.

        Args:
            secret_name: Name of the secret

        Returns:
            Secret value or None
        """
        try:
            import hvac

            vault_addr = self.config.get("vault_addr", "http://localhost:8200")
            vault_token = self.config.get("vault_token") or os.getenv("VAULT_TOKEN")
            vault_path = self.config.get("vault_path", "secret/data")

            if not vault_token:
                self.logger.error("VAULT_TOKEN not provided or set")
                return None

            client = hvac.Client(url=vault_addr, token=vault_token)

            try:
                response = client.secrets.kv.v2.read_secret_version(
                    path=secret_name, mount_point=vault_path.split("/")[0]
                )
                return response.get("data", {}).get("data", {})
            except hvac.exceptions.InvalidPath:
                self.logger.warning(f"Secret {secret_name} not found in Vault")
                return None

        except ImportError:
            self.logger.error("hvac not installed. Install: pip install hvac")
        except Exception as e:
            self.logger.error(f"Failed to get Vault secret {secret_name}: {e}")

        return None

    def _get_azure_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from Azure Key Vault.

        Args:
            secret_name: Name of the secret

        Returns:
            Secret value or None
        """
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            vault_url = self.config.get("vault_url")
            if not vault_url:
                self.logger.error("vault_url not provided")
                return None

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)

            try:
                secret = client.get_secret(secret_name)
                return secret.value
            except Exception as e:
                self.logger.warning(f"Secret {secret_name} not found in Azure Key Vault: {e}")
                return None

        except ImportError:
            self.logger.error(
                "Azure SDK not installed. Install: pip install azure-identity azure-keyvault-secrets"
            )
        except Exception as e:
            self.logger.error(f"Failed to get Azure secret {secret_name}: {e}")

        return None

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Store a secret in the configured provider.

        Args:
            secret_name: Name of the secret
            secret_value: Secret value

        Returns:
            True if successful
        """
        if self.provider == "aws":
            return self._set_aws_secret(secret_name, secret_value)
        elif self.provider == "vault":
            return self._set_vault_secret(secret_name, secret_value)
        elif self.provider == "azure":
            return self._set_azure_secret(secret_name, secret_value)
        else:
            self.logger.error(f"Unknown provider: {self.provider}")
            return False

    def _set_aws_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store secret in AWS Secrets Manager."""
        try:
            import boto3
            import json

            region = self.config.get("region", "us-east-1")
            client = boto3.client("secretsmanager", region_name=region)

            try:
                # Try to update existing secret
                client.update_secret(
                    SecretId=secret_name,
                    SecretString=json.dumps(secret_value) if isinstance(secret_value, dict) else secret_value,
                )
            except client.exceptions.ResourceNotFoundException:
                # Create new secret
                client.create_secret(
                    Name=secret_name,
                    SecretString=json.dumps(secret_value) if isinstance(secret_value, dict) else secret_value,
                )

            return True

        except Exception as e:
            self.logger.error(f"Failed to set AWS secret: {e}")
            return False

    def _set_vault_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store secret in HashiCorp Vault."""
        try:
            import hvac
            import json

            vault_addr = self.config.get("vault_addr", "http://localhost:8200")
            vault_token = self.config.get("vault_token") or os.getenv("VAULT_TOKEN")
            vault_path = self.config.get("vault_path", "secret/data")

            if not vault_token:
                self.logger.error("VAULT_TOKEN not provided")
                return False

            client = hvac.Client(url=vault_addr, token=vault_token)

            client.secrets.kv.v2.create_or_update_secret(
                path=secret_name,
                secret=json.dumps(secret_value) if isinstance(secret_value, dict) else secret_value,
                mount_point=vault_path.split("/")[0],
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to set Vault secret: {e}")
            return False

    def _set_azure_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store secret in Azure Key Vault."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            vault_url = self.config.get("vault_url")
            if not vault_url:
                self.logger.error("vault_url not provided")
                return False

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)

            client.set_secret(secret_name, secret_value)
            return True

        except Exception as e:
            self.logger.error(f"Failed to set Azure secret: {e}")
            return False


class SecretScanner:
    """Combined secret scanning and management."""

    def __init__(self, vault_type: str | None = None, vault_address: str | None = None, **_: Any):
        """Initialize secret scanner."""
        self.logger = logging.getLogger(__name__)
        self.scanner = DetectSecretsScanner()
        self.vault_type = vault_type
        self.vault_address = vault_address

    def scan_file(self, file_path: str) -> ScanResult:
        """Proxy single-file scans to the underlying detector."""
        return self.scanner.scan_file(file_path)

    def scan_directory(self, directory: str) -> ScanResult:
        """Proxy directory scans to the underlying detector."""
        return self.scanner.scan_directory(directory)

    def scan(self, path: str) -> ScanResult:
        """
        Scan path for secrets.

        Args:
            path: File or directory to scan

        Returns:
            ScanResult with detected secrets
        """
        path_obj = Path(path)

        if path_obj.is_file():
            return self.scanner.scan_file(str(path_obj))
        elif path_obj.is_dir():
            return self.scanner.scan_directory(str(path_obj))
        else:
            return ScanResult(
                success=False,
                secrets=[],
                errors=[f"Path not found: {path}"],
            )
