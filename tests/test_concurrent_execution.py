"""Tests for concurrent script execution in the sandbox environment."""
import os
import pytest
import pytest_asyncio
import asyncio
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    # Create workspace directory with absolute path
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_workspace"))
    os.makedirs(workspace_dir, exist_ok=True)
    
    # Change to workspace directory
    original_cwd = os.getcwd()
    os.chdir(workspace_dir)
    
    env = SandboxEnvironment(workspace_dir=workspace_dir)
    await env.create_container()
    yield env
    
    # Clean up
    await env.cleanup()
    try:
        import shutil
        shutil.rmtree(workspace_dir)
    except:
        pass
    finally:
        os.chdir(original_cwd)

@pytest.mark.asyncio
async def test_concurrent_script_execution(sandbox_env):
    """Test running multiple scripts concurrently."""
    # Create test scripts
    script1 = """#!/bin/bash
echo "Script 1 starting"
sleep 2
echo "Script 1 done"
"""
    script2 = """#!/bin/bash
echo "Script 2 starting"
sleep 1
echo "Script 2 done"
"""
    
    await sandbox_env.write_file("script1.sh", script1)
    await sandbox_env.write_file("script2.sh", script2)
    
    # Run scripts concurrently
    start_time = asyncio.get_event_loop().time()
    results = await sandbox_env.execute_scripts_concurrently(["script1.sh", "script2.sh"])
    end_time = asyncio.get_event_loop().time()
    
    # Verify execution time (should be closer to 2s than 3s)
    assert end_time - start_time < 2.5, "Scripts did not run concurrently"
    
    # Verify both scripts completed successfully
    assert len(results) == 2, "Not all scripts completed"
    for result in results:
        assert result["exit_code"] == 0, f"Script failed: {result['error']}"
        assert "starting" in result["output"].lower(), "Script did not produce expected output"
        assert "done" in result["output"].lower(), "Script did not complete"

@pytest.mark.asyncio
async def test_concurrent_script_isolation(sandbox_env):
    """Test that concurrently running scripts are properly isolated."""
    # Create test scripts that try to interfere with each other
    script1 = """#!/bin/bash
echo "Script 1 writing to file"
echo "Script 1 data" > shared.txt
sleep 1
cat shared.txt
"""
    script2 = """#!/bin/bash
echo "Script 2 writing to file"
echo "Script 2 data" > shared.txt
sleep 1
cat shared.txt
"""
    
    await sandbox_env.write_file("script1.sh", script1)
    await sandbox_env.write_file("script2.sh", script2)
    
    # Run scripts concurrently
    results = await sandbox_env.execute_scripts_concurrently(["script1.sh", "script2.sh"])
    
    # Verify each script sees its own version of the file
    for result in results:
        assert "writing to file" in result["output"], "Script did not attempt to write"
        assert "data" in result["output"], "Script did not read data"
        # Each script should only see its own data
        assert not ("Script 1 data" in result["output"] and "Script 2 data" in result["output"]), \
            "Scripts were not properly isolated"

@pytest.mark.asyncio
async def test_concurrent_script_cleanup(sandbox_env):
    """Test cleanup after concurrent script execution."""
    # Create test scripts
    script1 = """#!/bin/bash
echo "Creating temp file 1"
touch temp1.txt
sleep 2
"""
    script2 = """#!/bin/bash
echo "Creating temp file 2"
touch temp2.txt
sleep 1
"""
    
    await sandbox_env.write_file("script1.sh", script1)
    await sandbox_env.write_file("script2.sh", script2)
    
    # Run scripts concurrently
    await sandbox_env.execute_scripts_concurrently(["script1.sh", "script2.sh"])
    
    # Verify temporary files are cleaned up
    result = await sandbox_env.execute_command("ls")
    assert "temp1.txt" not in result["output"], "Temporary file 1 not cleaned up"
    assert "temp2.txt" not in result["output"], "Temporary file 2 not cleaned up"

@pytest.mark.asyncio
async def test_concurrent_script_error_handling(sandbox_env):
    """Test error handling during concurrent script execution."""
    # Create test scripts
    script1 = """#!/bin/bash
echo "Script 1 running"
exit 1
"""
    script2 = """#!/bin/bash
echo "Script 2 running"
nonexistent_command
"""
    script3 = """#!/bin/bash
echo "Script 3 running"
exit 0
"""
    
    await sandbox_env.write_file("script1.sh", script1)
    await sandbox_env.write_file("script2.sh", script2)
    await sandbox_env.write_file("script3.sh", script3)
    
    # Run scripts concurrently
    results = await sandbox_env.execute_scripts_concurrently(["script1.sh", "script2.sh", "script3.sh"])
    
    # Verify error handling
    assert len(results) == 3, "Not all results were returned"
    
    # Count failures
    failures = sum(1 for r in results if r["exit_code"] != 0)
    assert failures == 2, "Expected exactly two scripts to fail"
    
    # Verify successful script completed
    success = next(r for r in results if r["exit_code"] == 0)
    assert "Script 3 running" in success["output"], "Successful script did not run correctly"

@pytest.mark.asyncio
async def test_concurrent_script_resource_limits(sandbox_env):
    """Test resource limits during concurrent script execution."""
    # Create test scripts that use resources
    memory_hog = """#!/bin/bash
# Attempt to allocate lots of memory
x=$(dd if=/dev/zero bs=1M count=1024 2>/dev/null)
echo "Memory allocated"
"""
    cpu_hog = """#!/bin/bash
# Attempt to use lots of CPU
for i in {1..1000000}; do echo "CPU intensive" > /dev/null; done
"""
    
    await sandbox_env.write_file("memory_hog.sh", memory_hog)
    await sandbox_env.write_file("cpu_hog.sh", cpu_hog)
    
    # Run scripts concurrently
    results = await sandbox_env.execute_scripts_concurrently(
        ["memory_hog.sh", "cpu_hog.sh"],
        resource_limits={
            "memory_mb": 100,
            "cpu_percent": 50
        }
    )
    
    # Verify resource limits were enforced
    for result in results:
        assert result["exit_code"] != 0, "Script should have been limited"
        assert "resource" in result["error"].lower(), "Resource limit not enforced" 