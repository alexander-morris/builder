import os
import pytest
import pytest_asyncio
import shutil
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    workspace_dir = "./test_workspace_security"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)
    
    env = SandboxEnvironment(workspace_dir=workspace_dir)
    await env.create_container()
    yield env
    await env.cleanup()

@pytest.mark.asyncio
async def test_filesystem_boundaries(sandbox_env):
    """Test file system access limitations."""
    # Test access to sensitive directories
    sensitive_paths = [
        ("/etc/passwd", "read system files"),
        ("/etc/shadow", "read sensitive files"),
        ("/root/.bashrc", "access root home"),
        ("/var/log/syslog", "read system logs"),
        ("../outside.txt", "access parent directory"),
        ("/proc/cpuinfo", "access proc filesystem")
    ]
    
    for path, desc in sensitive_paths:
        result = await sandbox_env.execute_command(f"cat {path}")
        assert result["exit_code"] != 0, f"Should not be able to {desc}"
        assert "permission denied" in result["output"].lower() or "no such file" in result["output"].lower()
    
    # Test write attempts to system directories
    write_attempts = [
        ("touch /etc/new_file", "write to /etc"),
        ("mkdir /var/new_dir", "create system directory"),
        ("echo 'test' > /root/test", "write to root home"),
        ("touch ../test", "write outside workspace")
    ]
    
    for cmd, desc in write_attempts:
        result = await sandbox_env.execute_command(cmd)
        assert result["exit_code"] != 0, f"Should not be able to {desc}"
        assert "permission denied" in result["output"].lower()

@pytest.mark.asyncio
async def test_process_isolation(sandbox_env):
    """Test process isolation and restrictions."""
    # Test process visibility
    result = await sandbox_env.execute_command("ps aux")
    assert result["exit_code"] != 0, "Should not be able to view all processes"
    
    # Test process control
    control_attempts = [
        ("kill -9 1", "kill system processes"),
        ("systemctl restart sshd", "control system services"),
        ("sudo ls", "use sudo"),
        ("su root", "switch to root user")
    ]
    
    for cmd, desc in control_attempts:
        result = await sandbox_env.execute_command(cmd)
        assert result["exit_code"] != 0, f"Should not be able to {desc}"
        assert any(msg in result["output"].lower() for msg in ["permission denied", "command not found"])
    
    # Test process creation limits
    result = await sandbox_env.execute_command(":(){ :|:& };:")  # Fork bomb
    assert result["exit_code"] != 0, "Should prevent fork bombs"

@pytest.mark.asyncio
async def test_network_restrictions(sandbox_env):
    """Test network access restrictions."""
    # Test outbound connections
    network_attempts = [
        ("curl https://example.com", "make HTTP requests"),
        ("wget https://example.com", "download files"),
        ("ping -c 1 8.8.8.8", "ping external hosts"),
        ("nc -zv 8.8.8.8 53", "open arbitrary connections"),
        ("telnet example.com 80", "use telnet")
    ]
    
    for cmd, desc in network_attempts:
        result = await sandbox_env.execute_command(cmd)
        assert result["exit_code"] != 0, f"Should not be able to {desc}"
        assert "network access denied" in result["output"].lower()
    
    # Test listening ports
    result = await sandbox_env.execute_command("nc -l 8080")
    assert result["exit_code"] != 0, "Should not be able to listen on ports"

@pytest.mark.asyncio
async def test_resource_constraints(sandbox_env):
    """Test resource usage constraints."""
    # Test memory limits
    memory_script = """
import array
# Try to allocate 1GB
arr = array.array('i', [0] * (1024 * 1024 * 256))
"""
    await sandbox_env.write_file("memory_test.py", memory_script)
    result = await sandbox_env.execute_command("python3 memory_test.py")
    assert result["exit_code"] != 0, "Should enforce memory limits"
    assert "MemoryError" in result["output"]
    
    # Test CPU limits
    cpu_script = "while true; do true; done"
    result = await sandbox_env.execute_command(f"timeout 2s bash -c '{cpu_script}'")
    assert result["exit_code"] != 0, "Should enforce CPU limits"
    
    # Test disk space limits
    result = await sandbox_env.execute_command("dd if=/dev/zero of=large_file bs=1M count=1024")  # Try 1GB
    assert result["exit_code"] != 0, "Should enforce disk space limits"
    assert "no space left" in result["output"].lower()

@pytest.mark.asyncio
async def test_user_permissions(sandbox_env):
    """Test user permission restrictions."""
    # Verify running as non-root user
    result = await sandbox_env.execute_command("id")
    assert result["exit_code"] == 0
    assert "root" not in result["output"]
    
    # Test setuid/setgid restrictions
    result = await sandbox_env.execute_command("chmod u+s test_file")
    assert result["exit_code"] != 0, "Should not allow setuid"
    
    result = await sandbox_env.execute_command("chmod g+s test_file")
    assert result["exit_code"] != 0, "Should not allow setgid"
    
    # Test file creation permissions
    await sandbox_env.write_file("test_file", "test content")
    result = await sandbox_env.execute_command("stat -c %a test_file")
    assert result["exit_code"] == 0
    assert int(result["output"]) <= 0o666, "Files should not be created with excessive permissions" 