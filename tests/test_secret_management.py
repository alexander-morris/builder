import os
import pytest
from pathlib import Path
from src.utils.secrets import SecretManager

@pytest.fixture
def secret_manager(tmp_path):
    """Create a SecretManager instance with a temporary keystore."""
    keystore_path = tmp_path / "keystore"
    return SecretManager(keystore_path=keystore_path)

def test_secret_storage(secret_manager):
    """Test storing and retrieving secrets."""
    # Store a secret
    secret_manager.store("API_KEY", "test-api-key-123")
    
    # Retrieve the secret
    assert secret_manager.get("API_KEY") == "test-api-key-123"
    
    # Secret should be encrypted in storage
    keystore = Path(secret_manager.keystore_path)
    assert keystore.exists()
    stored_content = keystore.read_bytes()
    assert b"test-api-key-123" not in stored_content

def test_secret_rotation(secret_manager):
    """Test rotating secrets."""
    # Store initial secret
    secret_manager.store("DB_PASSWORD", "old-password")
    
    # Rotate the secret
    secret_manager.rotate("DB_PASSWORD", "new-password")
    
    # Should get new password
    assert secret_manager.get("DB_PASSWORD") == "new-password"
    
    # Should keep rotation history
    history = secret_manager.get_rotation_history("DB_PASSWORD")
    assert len(history) == 2
    assert history[-1]["value"] == "new-password"

def test_secret_access_control(secret_manager):
    """Test secret access permissions."""
    secret_manager.store("PRIVATE_KEY", "ssh-key-123")
    
    # Set access control
    secret_manager.restrict_access("PRIVATE_KEY", ["admin"])
    
    # Should fail without proper role
    with pytest.raises(PermissionError):
        secret_manager.get("PRIVATE_KEY", role="user")
        
    # Should succeed with proper role
    assert secret_manager.get("PRIVATE_KEY", role="admin") == "ssh-key-123"

def test_secret_validation(secret_manager):
    """Test secret validation rules."""
    # Add validation rule
    secret_manager.add_validation_rule(
        "API_KEY",
        lambda x: len(x) >= 32,
        "API key must be at least 32 characters"
    )
    
    # Should fail validation
    with pytest.raises(ValueError, match="API key must be at least 32"):
        secret_manager.store("API_KEY", "short-key")
        
    # Should pass validation
    valid_key = "x" * 32
    secret_manager.store("API_KEY", valid_key)
    assert secret_manager.get("API_KEY") == valid_key

def test_secret_expiration(secret_manager):
    """Test secret expiration."""
    # Store secret with expiration
    secret_manager.store("TEMP_TOKEN", "temp-123", expires_in_seconds=1)
    
    # Should be available immediately
    assert secret_manager.get("TEMP_TOKEN") == "temp-123"
    
    # Wait for expiration
    import time
    time.sleep(1.1)
    
    # Should be expired
    with pytest.raises(KeyError, match="Secret TEMP_TOKEN has expired"):
        secret_manager.get("TEMP_TOKEN") 