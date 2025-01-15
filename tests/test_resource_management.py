import os
import pytest
import pytest_asyncio
import shutil
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    workspace_dir = "./test_workspace_resources"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)
    
    env = SandboxEnvironment(workspace_dir=workspace_dir)
    await env.create_container()
    yield env
    await env.cleanup()

@pytest.mark.asyncio
async def test_memory_limits(sandbox_env):
    """Test memory limit enforcement."""
    # Test memory-intensive Python script
    memory_script = """
import array
# Try to allocate a large array (1GB)
arr = array.array('i', [0] * (1024 * 1024 * 256))  # 1GB (256M integers)
"""
    await sandbox_env.write_file("memory_test.py", memory_script)
    result = await sandbox_env.execute_command(
        "python3 memory_test.py",
        resource_limits={"memory_mb": 100}  # 100MB limit
    )
    assert result["exit_code"] != 0
    assert "Memory limit exceeded" in result["output"]

@pytest.mark.asyncio
async def test_cpu_limits(sandbox_env):
    """Test CPU usage limit enforcement."""
    # Test CPU-intensive script
    cpu_script = """
while True:
    pass  # Infinite loop to consume CPU
"""
    await sandbox_env.write_file("cpu_test.py", cpu_script)
    result = await sandbox_env.execute_command(
        "python3 cpu_test.py",
        resource_limits={"cpu_percent": 90}  # 90% CPU limit
    )
    assert result["exit_code"] != 0
    assert "CPU limit exceeded" in result["output"]

@pytest.mark.asyncio
async def test_disk_space_limits(sandbox_env):
    """Test disk space limit enforcement."""
    # Try to create a large file
    large_file_cmd = "dd if=/dev/zero of=large_file bs=1M count=1024"  # Try to create 1GB file
    result = await sandbox_env.execute_command(large_file_cmd)
    assert result["exit_code"] != 0
    assert "No space left on device" in result["output"]

@pytest.mark.asyncio
async def test_process_limits(sandbox_env):
    """Test process creation limits."""
    # Test script that creates multiple processes
    fork_script = """
import os
for _ in range(1000):  # Try to create 1000 processes
    os.fork()
"""
    await sandbox_env.write_file("fork_test.py", fork_script)
    result = await sandbox_env.execute_command(
        "python3 fork_test.py",
        resource_limits={"max_processes": 10}  # 10 processes limit
    )
    assert result["exit_code"] != 0
    assert "Process limit exceeded" in result["output"]

@pytest.mark.asyncio
async def test_file_descriptor_limits(sandbox_env):
    """Test file descriptor limit enforcement."""
    # Test script that opens many files
    fd_script = """
files = []
for i in range(2000):  # Try to open 2000 files
    files.append(open(f'file_{i}', 'w'))
"""
    await sandbox_env.write_file("fd_test.py", fd_script)
    result = await sandbox_env.execute_command(
        "python3 fd_test.py",
        resource_limits={"max_files": 100}  # 100 files limit
    )
    assert result["exit_code"] != 0
    assert "Too many open files" in result["output"]

@pytest.mark.asyncio
async def test_network_bandwidth_limits(sandbox_env):
    """Test network bandwidth limit enforcement."""
    # Test downloading a large file
    result = await sandbox_env.execute_command("curl -O https://example.com/large_file")
    assert result["exit_code"] != 0
    assert "network access denied" in result["output"]

@pytest.mark.asyncio
async def test_concurrent_resource_usage(sandbox_env):
    """Test resource limits under concurrent operations."""
    # Create multiple CPU-intensive processes
    cpu_script = "while true; do true; done"
    results = []
    for _ in range(4):  # Try to run 4 CPU-intensive processes
        result = await sandbox_env.execute_command(f"bash -c '{cpu_script}' &")
        results.append(result)
    
    # Check that at least some processes were killed or limited
    assert any(result["exit_code"] != 0 for result in results) 

@pytest.mark.asyncio
async def test_combined_resource_limits(sandbox_env):
    """Test multiple resource limits together."""
    # Test script that uses multiple resources
    combined_script = """
import array
import multiprocessing

# Allocate memory
arr = array.array('i', [0] * (1024 * 1024 * 50))  # 200MB

# Create some processes
def work():
    while True:
        pass

processes = []
for _ in range(5):
    p = multiprocessing.Process(target=work)
    p.start()
    processes.append(p)

for p in processes:
    p.join()
"""
    await sandbox_env.write_file("combined_test.py", combined_script)
    result = await sandbox_env.execute_command(
        "python3 combined_test.py",
        resource_limits={
            "memory_mb": 100,
            "cpu_percent": 90,
            "max_processes": 3
        }
    )
    assert result["exit_code"] != 0
    assert any(msg in result["output"] for msg in [
        "Memory limit exceeded",
        "CPU limit exceeded",
        "Process limit exceeded"
    ])

@pytest.mark.asyncio
async def test_resource_limit_cleanup(sandbox_env):
    """Test that resources are properly cleaned up after limits are exceeded."""
    # Test script that exceeds limits
    script = """
import time
while True:
    time.sleep(0.1)
"""
    await sandbox_env.write_file("cleanup_test.py", script)
    
    # Run with tight CPU limit
    result = await sandbox_env.execute_command(
        "python3 cleanup_test.py",
        resource_limits={"cpu_percent": 10}
    )
    assert result["exit_code"] != 0
    
    # Verify no lingering processes
    import psutil
    current_proc = psutil.Process()
    children = current_proc.children(recursive=True)
    python_procs = [p for p in children if "python" in p.name().lower()]
    assert len(python_procs) == 0, "No lingering Python processes should exist" 