"""Tests for script output validation in the sandbox environment."""
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

@pytest.mark.asyncio
async def test_basic_output_validation(sandbox_env):
    """Test basic output validation."""
    # Create a test script
    script = """#!/bin/bash
echo "Hello, World!"
"""
    script_path = os.path.join(sandbox_env.workspace, "test.sh")
    await sandbox_env.write_file("test.sh", script)
    os.chmod(script_path, 0o755)

    # Define expected output
    expected = {
        "output": "Hello, World!\n",
        "error": "",
        "exit_code": 0
    }

    # Validate output
    success, error = await sandbox_env.validate_script_output(script_path, expected)
    assert success, f"Output validation failed: {error}"

@pytest.mark.asyncio
async def test_error_stream_validation(sandbox_env):
    """Test error stream validation."""
    # Create a test script that writes to stderr
    script = """#!/bin/bash
echo "Error message" >&2
"""
    script_path = os.path.join(sandbox_env.workspace, "test.sh")
    await sandbox_env.write_file("test.sh", script)
    os.chmod(script_path, 0o755)

    # Define expected output
    expected = {
        "output": "",
        "error": "Error message\n",
        "exit_code": 0
    }

    # Validate output
    success, error = await sandbox_env.validate_script_output(script_path, expected)
    assert success, f"Output validation failed: {error}"

@pytest.mark.asyncio
async def test_exit_code_validation(sandbox_env):
    """Test exit code validation."""
    # Create a test script that exits with non-zero code
    script = """#!/bin/bash
exit 1
"""
    script_path = os.path.join(sandbox_env.workspace, "test.sh")
    await sandbox_env.write_file("test.sh", script)
    os.chmod(script_path, 0o755)

    # Define expected output
    expected = {
        "output": "",
        "error": "",
        "exit_code": 1
    }

    # Validate output
    success, error = await sandbox_env.validate_script_output(script_path, expected)
    assert success, f"Output validation failed: {error}"

@pytest.mark.asyncio
async def test_pattern_matching(sandbox_env):
    """Test pattern matching in output validation."""
    # Create a test script with dynamic output
    script = """#!/bin/bash
echo "Process started at: $(date)"
echo "Processing..."
echo "Process completed at: $(date)"
"""
    script_path = os.path.join(sandbox_env.workspace, "test.sh")
    await sandbox_env.write_file("test.sh", script)
    os.chmod(script_path, 0o755)

    # Define expected output with patterns
    expected = {
        "output_pattern": r"Process started at: .+\nProcessing\.\.\.\nProcess completed at: .+\n",
        "error": "",
        "exit_code": 0
    }

    # Validate output
    success, error = await sandbox_env.validate_script_output(script_path, expected)
    assert success, f"Output validation failed: {error}" 