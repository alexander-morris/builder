import os
import pytest
import pytest_asyncio
import shutil
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    workspace_dir = "./test_workspace_fs"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)
    
    env = SandboxEnvironment(workspace_dir=workspace_dir)
    await env.create_container()
    yield env
    await env.cleanup()

@pytest.mark.asyncio
async def test_file_write_permissions(sandbox_env):
    """Test file write permissions."""
    # Test basic file creation
    await sandbox_env.write_file("test.txt", "test content")
    result = await sandbox_env.execute_command("cat test.txt")
    assert result["exit_code"] == 0
    assert result["output"] == "test content"
    
    # Test file permissions
    result = await sandbox_env.execute_command("stat -c %a test.txt")
    assert result["exit_code"] == 0
    assert int(result["output"]) == 420  # 0o644
    
    # Test write to read-only file
    await sandbox_env.execute_command("chmod 444 test.txt")
    result = await sandbox_env.execute_command("echo 'new content' > test.txt")
    assert result["exit_code"] != 0
    assert "permission denied" in result["output"].lower()

@pytest.mark.asyncio
async def test_directory_access(sandbox_env):
    """Test directory access and permissions."""
    # Test directory creation
    result = await sandbox_env.execute_command("mkdir testdir")
    assert result["exit_code"] == 0
    
    # Test directory permissions
    result = await sandbox_env.execute_command("stat -c %a testdir")
    assert result["exit_code"] == 0
    assert int(result["output"]) == 493  # 0o755
    
    # Test file creation in directory
    await sandbox_env.write_file("testdir/file.txt", "test")
    result = await sandbox_env.execute_command("cat testdir/file.txt")
    assert result["exit_code"] == 0
    assert result["output"] == "test"

@pytest.mark.asyncio
async def test_workspace_paths(sandbox_env):
    """Test workspace path handling."""
    # Test absolute path rejection
    with pytest.raises(ValueError):
        await sandbox_env.write_file("/absolute/path", "test")
    
    # Test parent directory traversal
    with pytest.raises(ValueError):
        await sandbox_env.write_file("../outside.txt", "test")
    
    # Test nested directory creation
    await sandbox_env.write_file("dir1/dir2/file.txt", "test")
    result = await sandbox_env.execute_command("cat dir1/dir2/file.txt")
    assert result["exit_code"] == 0
    assert result["output"] == "test"

@pytest.mark.asyncio
async def test_volume_mounting(sandbox_env):
    """Test volume mounting and isolation."""
    # Test workspace isolation
    result = await sandbox_env.execute_command("touch test_file")
    assert result["exit_code"] == 0
    
    # Verify file exists in workspace
    assert os.path.exists(os.path.join(sandbox_env.workspace, "test_file"))
    
    # Test workspace boundaries
    result = await sandbox_env.execute_command("touch /test_file")
    assert result["exit_code"] != 0
    error_msg = result["output"].lower()
    assert any(msg in error_msg for msg in ["permission denied", "read-only file system"]) 