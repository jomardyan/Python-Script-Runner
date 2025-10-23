"""
Security Management Module

Provides secret detection and vault management:
- Hardcoded secret detection
- Integration with AWS Secrets Manager, HashiCorp Vault, Azure Key Vault
- Pre-execution secret injection
"""

try:
    from runners.security.secret_scanner import SecretScanner
    from runners.security.vault_adapter import SecretManagerAdapter
    __all__ = ["SecretScanner", "SecretManagerAdapter"]
except ImportError:
    __all__ = []
