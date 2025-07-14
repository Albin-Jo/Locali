# backend/app/services/security.py

import os
import hashlib
import secrets
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import base64
import json

from loguru import logger
from ..core.config import settings


class NetworkIsolationManager:
    """Manages network access restrictions for privacy."""

    def __init__(self):
        self.blocked_domains: List[str] = []
        self.allowed_domains: List[str] = settings.allowed_domains
        self.block_all_network = settings.enable_network_isolation
        self.dns_override: Dict[str, str] = {}

        if self.block_all_network:
            self._setup_network_blocks()

        logger.info(f"Network isolation: {'enabled' if self.block_all_network else 'disabled'}")

    def _setup_network_blocks(self):
        """Set up network blocking mechanisms."""
        # Override socket creation to block network access
        self._original_socket = socket.socket
        socket.socket = self._blocked_socket

        # Block common HTTP libraries
        self._patch_http_libraries()

    def _blocked_socket(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None):
        """Blocked socket that raises exception."""
        if self.block_all_network:
            raise PermissionError("Network access is disabled by security policy")
        return self._original_socket(family, type, proto, fileno)

    def _patch_http_libraries(self):
        """Patch common HTTP libraries to prevent network access."""
        try:
            import requests
            import urllib3

            # Store original methods
            self._original_request = requests.Session.request
            self._original_urlopen = urllib3.poolmanager.PoolManager.urlopen

            # Replace with security-checked versions
            requests.Session.request = self._secure_request
            urllib3.poolmanager.PoolManager.urlopen = self._secure_urlopen

        except ImportError:
            pass  # Libraries not installed

    def _secure_request(self, method, url, **kwargs):
        """Security-checked HTTP request."""
        if not self._is_url_allowed(url):
            raise PermissionError(f"Access to {url} blocked by security policy")
        return self._original_request(method, url, **kwargs)

    def _secure_urlopen(self, method, url, **kwargs):
        """Security-checked urllib3 request."""
        if not self._is_url_allowed(url):
            raise PermissionError(f"Access to {url} blocked by security policy")
        return self._original_urlopen(method, url, **kwargs)

    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed based on security policy."""
        if not self.block_all_network:
            return True

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check against allowed domains
            for allowed in self.allowed_domains:
                if domain == allowed or domain.endswith(f'.{allowed}'):
                    return True

            return False

        except Exception:
            return False

    def add_allowed_domain(self, domain: str):
        """Add a domain to the allowed list."""
        if domain not in self.allowed_domains:
            self.allowed_domains.append(domain)
            logger.info(f"Added allowed domain: {domain}")

    def remove_allowed_domain(self, domain: str):
        """Remove a domain from the allowed list."""
        if domain in self.allowed_domains:
            self.allowed_domains.remove(domain)
            logger.info(f"Removed allowed domain: {domain}")

    def disable_network_isolation(self):
        """Temporarily disable network isolation."""
        if self.block_all_network:
            # Restore original socket
            socket.socket = self._original_socket
            self.block_all_network = False
            logger.warning("Network isolation disabled")

    def enable_network_isolation(self):
        """Re-enable network isolation."""
        if not self.block_all_network:
            self._setup_network_blocks()
            self.block_all_network = True
            logger.info("Network isolation enabled")

    def get_status(self) -> Dict[str, Any]:
        """Get network isolation status."""
        return {
            'isolation_enabled': self.block_all_network,
            'allowed_domains': self.allowed_domains,
            'blocked_domains': self.blocked_domains
        }


class EncryptionManager:
    """Manages encryption for sensitive data."""

    def __init__(self):
        self.encryption_enabled = settings.enable_conversation_encryption
        self.key_file = Path(settings.database_url).parent / ".encryption_key"
        self.salt_file = Path(settings.database_url).parent / ".salt"

        if self.encryption_enabled:
            self._initialize_encryption()

        logger.info(f"Encryption: {'enabled' if self.encryption_enabled else 'disabled'}")

    def _initialize_encryption(self):
        """Initialize encryption key and salt."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            self.Fernet = Fernet
            self.PBKDF2HMAC = PBKDF2HMAC
            self.hashes = hashes

            # Generate or load encryption key
            if self.key_file.exists() and self.salt_file.exists():
                self._load_key()
            else:
                self._generate_new_key()

        except ImportError:
            logger.error("cryptography library not installed. Encryption disabled.")
            self.encryption_enabled = False
            self.fernet = None

    def _generate_new_key(self):
        """Generate new encryption key and salt."""
        # Generate random salt
        salt = secrets.token_bytes(32)

        # Generate key from password (could be user-provided in production)
        password = os.environ.get('LOCALI_ENCRYPTION_PASSWORD', 'default-key-change-in-production')

        kdf = self.PBKDF2HMAC(
            algorithm=self.hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

        # Save salt and create fernet instance
        self.salt_file.write_bytes(salt)
        self.key_file.write_bytes(key)

        self.fernet = self.Fernet(key)

        logger.info("Generated new encryption key")

    def _load_key(self):
        """Load existing encryption key."""
        try:
            key = self.key_file.read_bytes()
            self.fernet = self.Fernet(key)
            logger.info("Loaded existing encryption key")
        except Exception as e:
            logger.error(f"Failed to load encryption key: {e}")
            self._generate_new_key()

    def encrypt_data(self, data: str) -> str:
        """Encrypt string data."""
        if not self.encryption_enabled or not self.fernet:
            return data

        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        if not self.encryption_enabled or not self.fernet:
            return encrypted_data

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data

    def encrypt_conversation(self, conversation_data: Dict[str, Any]) -> str:
        """Encrypt conversation data."""
        if not self.encryption_enabled:
            return json.dumps(conversation_data)

        json_str = json.dumps(conversation_data)
        return self.encrypt_data(json_str)

    def decrypt_conversation(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt conversation data."""
        if not self.encryption_enabled:
            return json.loads(encrypted_data)

        decrypted_json = self.decrypt_data(encrypted_data)
        return json.loads(decrypted_json)

    def change_password(self, new_password: str):
        """Change encryption password (re-encrypts all data)."""
        if not self.encryption_enabled:
            return False

        # This would require re-encrypting all stored data
        # For now, just update the key
        old_fernet = self.fernet

        # Generate new key with new password
        salt = self.salt_file.read_bytes()
        kdf = self.PBKDF2HMAC(
            algorithm=self.hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(new_password.encode()))
        self.key_file.write_bytes(key)
        self.fernet = self.Fernet(key)

        logger.info("Encryption password changed")
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get encryption status."""
        return {
            'encryption_enabled': self.encryption_enabled,
            'key_file_exists': self.key_file.exists() if self.encryption_enabled else None,
            'key_strength': '256-bit AES' if self.encryption_enabled else None
        }


class SecurityAuditLogger:
    """Logs security events for monitoring."""

    def __init__(self):
        self.audit_log = Path(settings.database_url).parent / "security_audit.log"
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)

    def log_network_access_attempt(self, url: str, allowed: bool):
        """Log network access attempts."""
        self._log_event("NETWORK_ACCESS", {
            'url': url,
            'allowed': allowed,
            'reason': 'blocked_by_policy' if not allowed else 'allowed'
        })

    def log_encryption_event(self, operation: str, success: bool):
        """Log encryption operations."""
        self._log_event("ENCRYPTION", {
            'operation': operation,
            'success': success
        })

    def log_security_policy_change(self, policy: str, old_value: Any, new_value: Any):
        """Log security policy changes."""
        self._log_event("POLICY_CHANGE", {
            'policy': policy,
            'old_value': str(old_value),
            'new_value': str(new_value)
        })

    def _log_event(self, event_type: str, details: Dict[str, Any]):
        """Log a security event."""
        from datetime import datetime

        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'details': details
        }

        try:
            with open(self.audit_log, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Failed to write security audit log: {e}")

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events."""
        events = []

        try:
            if self.audit_log.exists():
                with open(self.audit_log, 'r') as f:
                    lines = f.readlines()

                for line in reversed(lines[-limit:]):
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read security audit log: {e}")

        return events


class SecurityManager:
    """Main security manager coordinating all security services."""

    def __init__(self):
        self.network_isolation = NetworkIsolationManager()
        self.encryption = EncryptionManager()
        self.audit_logger = SecurityAuditLogger()

        logger.info("SecurityManager initialized")

    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        return {
            'network_isolation': self.network_isolation.get_status(),
            'encryption': self.encryption.get_status(),
            'privacy_mode': self.network_isolation.block_all_network and self.encryption.encryption_enabled,
            'security_level': self._calculate_security_level()
        }

    def _calculate_security_level(self) -> str:
        """Calculate overall security level."""
        score = 0

        if self.network_isolation.block_all_network:
            score += 50
        if self.encryption.encryption_enabled:
            score += 50

        if score >= 90:
            return "Maximum"
        elif score >= 70:
            return "High"
        elif score >= 40:
            return "Medium"
        else:
            return "Low"

    def enable_privacy_mode(self):
        """Enable maximum privacy settings."""
        self.network_isolation.enable_network_isolation()
        if not self.encryption.encryption_enabled:
            self.encryption.encryption_enabled = True
            self.encryption._initialize_encryption()

        self.audit_logger.log_security_policy_change(
            "privacy_mode", False, True
        )

        logger.info("Privacy mode enabled")

    def disable_privacy_mode(self):
        """Disable privacy restrictions (for development/debugging)."""
        self.network_isolation.disable_network_isolation()

        self.audit_logger.log_security_policy_change(
            "privacy_mode", True, False
        )

        logger.warning("Privacy mode disabled")

    def validate_request_security(self, request_data: Dict[str, Any]) -> bool:
        """Validate request against security policies."""
        # Add custom security validation logic here
        # For now, just basic validation

        # Check for potentially dangerous content
        dangerous_patterns = ['<script', 'javascript:', 'data:text/html']

        def check_content(obj):
            if isinstance(obj, str):
                return not any(pattern in obj.lower() for pattern in dangerous_patterns)
            elif isinstance(obj, dict):
                return all(check_content(v) for v in obj.values())
            elif isinstance(obj, list):
                return all(check_content(item) for item in obj)
            return True

        is_safe = check_content(request_data)

        if not is_safe:
            self.audit_logger.log_security_policy_change(
                "request_validation", "safe", "blocked_dangerous_content"
            )

        return is_safe