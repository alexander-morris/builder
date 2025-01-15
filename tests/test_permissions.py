import os
import pytest
import pytest_asyncio
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    env = SandboxEnvironment(workspace_dir="./test_workspace")
    await env.create_container()
    yield env
    await env.cleanup()

@pytest.mark.asyncio
async def test_file_permission_bits(sandbox_env):
    """Test file permission bit handling."""
    # Create test files with different permissions
    test_files = [
        ("readonly.txt", "0444", "read-only file"),
        ("writeonly.txt", "0222", "write-only file"),
        ("executable.sh", "0755", "executable script"),
        ("private.txt", "0600", "private file")
    ]
    
    for filename, mode, desc in test_files:
        # Create file
        await sandbox_env.write_file(filename, f"Test content for {desc}")
        # Set permissions
        result = await sandbox_env.execute_command(f"chmod {mode} {filename}")
        assert result["exit_code"] == 0, f"Failed to set permissions for {desc}"
        
        # Verify permissions
        result = await sandbox_env.execute_command(f"stat -c %a {filename}")
        assert result["exit_code"] == 0, f"Failed to get permissions for {desc}"
        assert result["output"].strip() == mode[-3:], f"Incorrect permissions for {desc}"

@pytest.mark.asyncio
async def test_directory_permission_inheritance(sandbox_env):
    """Test directory permission inheritance."""
    # Create test directory with specific permissions
    result = await sandbox_env.execute_command("mkdir -p test_dir && chmod 0755 test_dir")
    assert result["exit_code"] == 0, "Failed to create test directory"
    
    # Create file in directory
    await sandbox_env.write_file("test_dir/test.txt", "Test content")
    
    # Verify inherited permissions
    result = await sandbox_env.execute_command("stat -c %a test_dir/test.txt")
    assert result["exit_code"] == 0, "Failed to get file permissions"
    assert result["output"].strip() == "644", "File did not inherit default permissions"

@pytest.mark.asyncio
async def test_umask_effects(sandbox_env):
    """Test effects of umask on file creation."""
    # Set umask and create files
    test_cases = [
        ("0022", "644"),  # Standard umask
        ("0077", "600"),  # Private files
        ("0002", "664"),  # Group writable
    ]
    
    for umask, expected_mode in test_cases:
        # Set umask
        result = await sandbox_env.execute_command(f"umask {umask}")
        assert result["exit_code"] == 0, f"Failed to set umask {umask}"
        
        # Create test file
        test_file = f"test_umask_{umask}.txt"
        await sandbox_env.write_file(test_file, "Test content")
        
        # Verify permissions
        result = await sandbox_env.execute_command(f"stat -c %a {test_file}")
        assert result["exit_code"] == 0, f"Failed to get permissions for umask {umask}"
        assert result["output"].strip() == expected_mode, f"Incorrect permissions for umask {umask}"

@pytest.mark.asyncio
async def test_permission_boundaries(sandbox_env):
    """Test permission boundaries and restrictions."""
    # Test restricted operations
    restricted_ops = [
        ("chmod 777 /etc/passwd", "system file modification"),
        ("chown root:root test.txt", "ownership change"),
        ("chmod +s test.txt", "setuid bit setting"),
        ("chmod +t /tmp", "sticky bit setting on system dir"),
    ]
    
    for cmd, desc in restricted_ops:
        result = await sandbox_env.execute_command(cmd)
        assert result["exit_code"] != 0, f"Should not allow {desc}"
        assert "permission denied" in result["output"].lower(), f"Should get permission denied for {desc}"

@pytest.mark.asyncio
async def test_special_permissions(sandbox_env):
    """Test special permission bits (setuid, setgid, sticky)."""
    # Create test files
    test_files = [
        ("setuid_test", "4755", "setuid"),
        ("setgid_test", "2755", "setgid"),
        ("sticky_test", "1755", "sticky"),
    ]
    
    for filename, mode, desc in test_files:
        # Create file
        await sandbox_env.write_file(filename, f"Test content for {desc}")
        # Attempt to set special permissions
        result = await sandbox_env.execute_command(f"chmod {mode} {filename}")
        assert result["exit_code"] != 0, f"Should not allow setting {desc} bit"
        
        # Verify permissions remained standard
        result = await sandbox_env.execute_command(f"stat -c %a {filename}")
        assert result["exit_code"] == 0, f"Failed to get permissions for {desc} test"
        assert result["output"].strip() == "644", f"Permissions should remain standard for {desc} test" 