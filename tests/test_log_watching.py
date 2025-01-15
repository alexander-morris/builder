"""Tests for log watching functionality in the sandbox environment."""
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
async def test_basic_log_watching(sandbox_env):
    """Test basic log watching functionality."""
    # Create a script that writes to a log file
    script = """#!/bin/bash
echo "Starting script" > test.log
sleep 0.1
echo "Error: Something went wrong" >> test.log
sleep 0.1
echo "Finishing script" >> test.log
"""
    await sandbox_env.write_file("test.sh", script)
    
    # Start log watching
    log_watcher = await sandbox_env.watch_log("test.log", error_patterns=["Error:"])
    try:
        # Execute script
        process = await asyncio.create_subprocess_exec(
            'bash',
            'test.sh',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()
        
        # Wait for log watcher to detect error
        error_found = await log_watcher.wait_for_error(timeout=1.0)
        assert error_found, "Log watcher did not detect error"
        assert "Error: Something went wrong" in log_watcher.error_context
    finally:
        await log_watcher.stop()

@pytest.mark.asyncio
async def test_log_rotation(sandbox_env):
    """Test log rotation handling."""
    # Create a script that rotates logs
    script = """#!/bin/bash
echo "Initial log" > test.log
sleep 0.1
mv test.log test.log.1
echo "New log file" > test.log
sleep 0.1
echo "Error in new log" >> test.log
"""
    await sandbox_env.write_file("test.sh", script)
    
    # Start log watching
    log_watcher = await sandbox_env.watch_log("test.log", error_patterns=["Error"])
    try:
        # Execute script
        process = await asyncio.create_subprocess_exec(
            'bash',
            'test.sh',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()
        
        # Wait for log watcher to detect error
        error_found = await log_watcher.wait_for_error(timeout=1.0)
        assert error_found, "Log watcher did not detect error after rotation"
        assert "Error in new log" in log_watcher.error_context
    finally:
        await log_watcher.stop()

@pytest.mark.asyncio
async def test_log_filtering(sandbox_env):
    """Test log filtering functionality."""
    # Create a script that writes different types of messages
    script = """#!/bin/bash
echo "INFO: Starting up" > test.log
sleep 0.1
echo "DEBUG: Processing data" >> test.log
sleep 0.1
echo "WARNING: Resource usage high" >> test.log
sleep 0.1
echo "ERROR: Operation failed" >> test.log
"""
    await sandbox_env.write_file("test.sh", script)
    
    # Start log watching with specific patterns
    log_watcher = await sandbox_env.watch_log(
        "test.log",
        error_patterns=["ERROR:"],
        warning_patterns=["WARNING:"],
        ignore_patterns=["DEBUG:"]
    )
    try:
        # Execute script
        process = await asyncio.create_subprocess_exec(
            'bash',
            'test.sh',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()
        
        # Wait for log watcher to detect error
        error_found = await log_watcher.wait_for_error(timeout=1.0)
        assert error_found, "Log watcher did not detect error"
        assert "ERROR: Operation failed" in log_watcher.error_context
        assert "WARNING: Resource usage high" in log_watcher.warning_context
        assert "DEBUG: Processing data" not in log_watcher.error_context
    finally:
        await log_watcher.stop() 