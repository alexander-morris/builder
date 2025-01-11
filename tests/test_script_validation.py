"""Tests for script content validation in the sandbox environment."""
import os
import pytest
from pathlib import Path
import tempfile
from src.sandbox.environment import SandboxEnvironment

@pytest.fixture
def sandbox_env():
    """Create a temporary sandbox environment for testing."""
    with tempfile.TemporaryDirectory() as workspace:
        env = SandboxEnvironment(workspace_path=workspace)
        env.create_container()
        yield env
        env.cleanup()

def test_script_content_validation_ascii(sandbox_env):
    """Test validation of ASCII script content."""
    # Create a test script
    script_content = "#!/bin/bash\necho 'Hello, World!'\n"
    script_path = "test_script.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"Script content validation failed: {error}"

def test_script_content_validation_utf8(sandbox_env):
    """Test validation of UTF-8 script content with special characters."""
    # Create a test script with UTF-8 characters
    script_content = """#!/bin/bash
echo '¡Hola, mundo!'  # Spanish
echo '你好，世界！'  # Chinese
echo 'Привет, мир!'  # Russian
"""
    script_path = "test_utf8_script.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"UTF-8 script content validation failed: {error}"

def test_script_content_line_endings(sandbox_env):
    """Test handling of different line ending styles."""
    # Test content with different line endings
    unix_content = "line1\nline2\nline3"
    windows_content = "line1\r\nline2\r\nline3"
    script_path = "test_endings.txt"
    
    # Write with Unix endings
    sandbox_env.write_file(script_path, unix_content)
    
    # Should validate successfully against both Unix and Windows endings
    is_valid, error = sandbox_env.validate_script_content(script_path, unix_content)
    assert is_valid, f"Unix line ending validation failed: {error}"
    
    is_valid, error = sandbox_env.validate_script_content(script_path, windows_content)
    assert is_valid, f"Windows line ending validation failed: {error}"

def test_script_encoding_detection(sandbox_env):
    """Test script encoding detection."""
    # Test ASCII content
    ascii_content = "#!/bin/bash\necho 'Hello!'\n"
    ascii_path = "test_ascii.sh"
    sandbox_env.write_file(ascii_path, ascii_content)
    encoding, error = sandbox_env.get_script_encoding(ascii_path)
    assert encoding == "ascii", f"ASCII detection failed: {error}"
    
    # Test UTF-8 content
    utf8_content = "#!/bin/bash\necho '¡Hola!'\n"
    utf8_path = "test_utf8.sh"
    sandbox_env.write_file(utf8_path, utf8_content)
    encoding, error = sandbox_env.get_script_encoding(utf8_path)
    assert encoding == "utf-8", f"UTF-8 detection failed: {error}"

def test_content_mismatch_detection(sandbox_env):
    """Test detection of content mismatches."""
    script_path = "test_mismatch.sh"
    actual_content = "echo 'Hello'\n"
    expected_content = "echo 'World'\n"
    
    # Write actual content
    sandbox_env.write_file(script_path, actual_content)
    
    # Validate against different content
    is_valid, error = sandbox_env.validate_script_content(script_path, expected_content)
    assert not is_valid, "Validation should fail for mismatched content"
    assert "Content mismatch" in error

def test_invalid_file_handling(sandbox_env):
    """Test handling of invalid or non-existent files."""
    # Test non-existent file
    is_valid, error = sandbox_env.validate_script_content("nonexistent.sh", "content")
    assert not is_valid, "Validation should fail for non-existent file"
    assert "Failed to read script" in error
    
    # Test encoding detection for non-existent file
    encoding, error = sandbox_env.get_script_encoding("nonexistent.sh")
    assert encoding == "", "Encoding detection should fail for non-existent file"
    assert "Failed to read script" in error 