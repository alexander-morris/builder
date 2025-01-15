import os
import pytest
import pytest_asyncio
import logging
import shutil
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    # Create a fresh workspace for each test
    workspace_dir = "./test_workspace"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)
    
    env = SandboxEnvironment(workspace_dir=workspace_dir)
    await env.create_container()
    yield env
    await env.cleanup()

@pytest.mark.asyncio
async def test_file_operation_errors(sandbox_env):
    """Test error handling for file operations."""
    # Test non-existent file
    with pytest.raises(FileNotFoundError) as exc:
        await sandbox_env.read_file("nonexistent.txt")
    assert "File not found" in str(exc.value)
    
    # Test invalid file path
    with pytest.raises(ValueError) as exc:
        await sandbox_env.write_file("../outside.txt", "test")
    assert "Invalid path" in str(exc.value)
    
    # Test directory instead of file
    os.makedirs(os.path.join(sandbox_env.workspace, "test_dir"), exist_ok=True)
    with pytest.raises(IsADirectoryError) as exc:
        await sandbox_env.write_file("test_dir", "test")
    assert "Is a directory" in str(exc.value)

@pytest.mark.asyncio
async def test_command_execution_errors(sandbox_env):
    """Test error handling for command execution."""
    # Test invalid command
    result = await sandbox_env.execute_command("invalid_command")
    assert result["exit_code"] != 0
    assert "command not found" in result["output"].lower()
    
    # Test command with invalid arguments
    result = await sandbox_env.execute_command("ls --invalid-option")
    assert result["exit_code"] != 0
    assert "invalid option" in result["output"].lower()
    
    # Test command execution without container
    sandbox_env.container = None
    with pytest.raises(RuntimeError) as exc:
        await sandbox_env.execute_command("ls")
    assert "Container not initialized" in str(exc.value)

@pytest.mark.asyncio
async def test_permission_errors(sandbox_env):
    """Test error handling for permission-related operations."""
    # Test writing to read-only file
    await sandbox_env.write_file("readonly.txt", "initial content")
    await sandbox_env.execute_command("chmod 444 readonly.txt")
    
    result = await sandbox_env.execute_command("echo 'new content' > readonly.txt")
    assert result["exit_code"] != 0
    assert "permission denied" in result["output"].lower()
    
    # Test modifying system files
    result = await sandbox_env.execute_command("touch /etc/test")
    assert result["exit_code"] != 0
    assert "permission denied" in result["output"].lower()

@pytest.mark.asyncio
async def test_resource_limit_errors(sandbox_env):
    """Test error handling for resource limits."""
    # Test memory limit
    memory_test = '''python3 -c "
import array
a = array.array('b', [0] * (1024 * 1024 * 1024))  # Try to allocate 1GB
"'''
    result = await sandbox_env.execute_command(memory_test)
    assert result["exit_code"] != 0
    assert "resource" in result["output"].lower()
    
    # Test process limit
    process_test = '''python3 -c "
import multiprocessing
def work():
    while True:
        pass
processes = [multiprocessing.Process(target=work) for _ in range(10)]
for p in processes:
    p.start()
for p in processes:
    p.join()
"'''
    result = await sandbox_env.execute_command(process_test)
    assert result["exit_code"] != 0
    assert "resource" in result["output"].lower()

@pytest.mark.asyncio
async def test_logging_functionality(sandbox_env, caplog):
    """Test logging functionality."""
    # Test successful operation logging
    with caplog.at_level(logging.INFO):
        await sandbox_env.write_file("test.txt", "test content")
        assert any("Successfully wrote file" in record.message for record in caplog.records)
    
    # Test error logging
    with caplog.at_level(logging.ERROR):
        try:
            await sandbox_env.read_file("nonexistent.txt")
        except FileNotFoundError:
            pass
        assert any("Error reading file" in record.message for record in caplog.records)
    
    # Test command execution logging
    with caplog.at_level(logging.INFO):
        caplog.clear()
        test_command = "echo test"
        result = await sandbox_env.execute_command(test_command)
        assert any("Executing command" in record.message for record in caplog.records), \
            "Command execution should be logged"
    
    # Test error level logging for invalid command
    with caplog.at_level(logging.ERROR):
        caplog.clear()
        result = await sandbox_env.execute_command("invalid_command")
        assert any("Command failed" in record.message for record in caplog.records), \
            "Command failure should be logged"

@pytest.mark.asyncio
async def test_cleanup_error_handling(sandbox_env):
    """Test error handling during cleanup."""
    # Create a fresh workspace for this test
    workspace_dir = "./test_workspace_cleanup"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)
    sandbox_env.workspace = workspace_dir
    
    # Test cleanup with missing files
    test_dir = os.path.join(workspace_dir, "test_dir")
    os.makedirs(test_dir, exist_ok=True)
    await sandbox_env.write_file("test_dir/test.txt", "test")
    os.remove(os.path.join(workspace_dir, "test_dir/test.txt"))
    
    # Should not raise exception during cleanup
    await sandbox_env.cleanup()
    
    # Test cleanup with permission issues
    test_dir2 = os.path.join(workspace_dir, "test_dir2")
    os.makedirs(test_dir2, exist_ok=True)
    test_file = os.path.join(test_dir2, "test.txt")
    
    # Create the file first, then change permissions
    with open(test_file, 'w') as f:
        f.write("test")
    os.chmod(test_dir2, 0o444)  # Read-only
    
    # Should handle permission error gracefully
    await sandbox_env.cleanup()

@pytest.mark.asyncio
async def test_network_access_errors(sandbox_env):
    """Test error handling for network access attempts."""
    # Test outbound network access
    result = await sandbox_env.execute_command("curl http://example.com")
    assert result["exit_code"] != 0
    assert "network access denied" in result["output"].lower()
    
    # Test listening on ports
    result = await sandbox_env.execute_command("nc -l 8080")
    assert result["exit_code"] != 0
    assert "network access denied" in result["output"].lower()

@pytest.mark.asyncio
async def test_api_communication_errors(sandbox_env):
    """Test error handling for API communication."""
    # Test invalid API key
    sandbox_env.mock_api_key = None  # Set to None to trigger the error
    with pytest.raises(RuntimeError) as exc:
        await sandbox_env.execute_agent_task("test task")
    assert "Failed to communicate with API" in str(exc.value)
    
    # Test API timeout
    sandbox_env.mock_api_key = "valid_key"  # Restore a valid key
    with pytest.raises(TimeoutError) as exc:
        await sandbox_env.execute_agent_task("timeout test")
    assert "API request timed out" in str(exc.value)

@pytest.mark.asyncio
async def test_container_lifecycle_errors(sandbox_env):
    """Test error handling for container lifecycle operations."""
    # Test double container creation
    await sandbox_env.create_container()  # Should handle gracefully
    assert sandbox_env.container.status == "running"
    
    # Test cleanup of non-existent container
    sandbox_env.container = None
    await sandbox_env.cleanup()  # Should not raise exception
    
    # Test cleanup of stopped container
    container = await sandbox_env.create_container()
    container.status = "stopped"
    await sandbox_env.cleanup()  # Should handle gracefully

@pytest.mark.asyncio
async def test_concurrent_operations(sandbox_env):
    """Test error handling for concurrent operations."""
    # Test concurrent file operations
    async def write_file(content: str):
        await sandbox_env.write_file("concurrent.txt", content)
    
    # Run multiple writes concurrently
    import asyncio
    tasks = [
        write_file(f"content{i}")
        for i in range(5)
    ]
    
    # Should handle concurrent access without errors
    await asyncio.gather(*tasks)
    
    # Verify file content is from one of the operations
    content = await sandbox_env.read_file("concurrent.txt")
    assert content.startswith("content")
    
    # Test concurrent command execution
    async def run_command(cmd: str):
        return await sandbox_env.execute_command(cmd)
    
    # Run multiple commands concurrently
    tasks = [
        run_command(f"echo test{i}")
        for i in range(5)
    ]
    
    # Should handle concurrent execution without errors
    results = await asyncio.gather(*tasks)
    assert all(r["exit_code"] == 0 for r in results) 