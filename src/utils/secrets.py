import os
import json
import time
from pathlib import Path
from typing import Dict, List, Callable, Any
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode

class SecretManager:
    """Manages secure storage and access of secrets."""
    
    def __init__(self, keystore_path: Path):
        """Initialize the secret manager with a keystore location."""
        self.keystore_path = keystore_path
        self.keystore_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate encryption key if not exists
        key_file = self.keystore_path.parent / ".key"
        if not key_file.exists():
            key = Fernet.generate_key()
            key_file.write_bytes(key)
        
        # Initialize encryption
        self.fernet = Fernet(key_file.read_bytes())
        
        # Initialize storage
        self.secrets: Dict[str, Dict] = {}
        self.validation_rules: Dict[str, tuple[Callable, str]] = {}
        self.access_controls: Dict[str, List[str]] = {}
        
        # Load existing secrets
        if self.keystore_path.exists():
            encrypted_data = self.keystore_path.read_bytes()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            self.secrets = json.loads(decrypted_data)
    
    def store(self, key: str, value: str, expires_in_seconds: int = None) -> None:
        """Store a secret value."""
        # Validate if rules exist
        if key in self.validation_rules:
            validator, message = self.validation_rules[key]
            if not validator(value):
                raise ValueError(message)
        
        # Create secret entry
        secret_data = {
            "value": value,
            "created_at": time.time(),
            "expires_at": time.time() + expires_in_seconds if expires_in_seconds else None,
            "rotation_history": []
        }
        
        # If secret exists, move it to rotation history
        if key in self.secrets:
            old_secret = self.secrets[key]
            old_secret["rotated_at"] = time.time()
            secret_data["rotation_history"] = (
                old_secret.get("rotation_history", []) + [old_secret]
            )
        
        self.secrets[key] = secret_data
        self._save_secrets()
    
    def get(self, key: str, role: str = None) -> str:
        """Retrieve a secret value."""
        if key not in self.secrets:
            raise KeyError(f"Secret {key} not found")
            
        # Check access control
        if key in self.access_controls and role not in self.access_controls[key]:
            raise PermissionError(f"Role {role} does not have access to {key}")
            
        secret_data = self.secrets[key]
        
        # Check expiration
        if secret_data["expires_at"] and time.time() > secret_data["expires_at"]:
            raise KeyError(f"Secret {key} has expired")
            
        return secret_data["value"]
    
    def rotate(self, key: str, new_value: str) -> None:
        """Rotate a secret to a new value."""
        if key not in self.secrets:
            raise KeyError(f"Secret {key} not found")
            
        self.store(key, new_value)
    
    def get_rotation_history(self, key: str) -> List[Dict]:
        """Get the rotation history of a secret."""
        if key not in self.secrets:
            raise KeyError(f"Secret {key} not found")
            
        current = self.secrets[key].copy()
        current.pop("rotation_history", None)
        
        history = self.secrets[key].get("rotation_history", [])
        return history + [current]
    
    def restrict_access(self, key: str, roles: List[str]) -> None:
        """Restrict access to a secret to specific roles."""
        self.access_controls[key] = roles
    
    def add_validation_rule(self, key: str, validator: Callable[[str], bool], message: str) -> None:
        """Add a validation rule for a secret."""
        self.validation_rules[key] = (validator, message)
    
    def _save_secrets(self) -> None:
        """Save secrets to encrypted storage."""
        data = json.dumps(self.secrets).encode()
        encrypted_data = self.fernet.encrypt(data)
        self.keystore_path.write_bytes(encrypted_data) 