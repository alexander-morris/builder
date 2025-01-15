"""Tests for script output validation in the sandbox environment."""
import os
import pytest
import pytest_asyncio
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
async def test_basic_output_validation(sandbox_env):
    """Test basic script output validation."""
    # Create test script
    script = """#!/bin/bash
echo "Hello, World!"
"""
    await sandbox_env.write_file("test.sh", script)
    
    # Define expected output
    expected = {
        'output': 'Hello, World!\n',
        'error': '',
        'exit_code': 0
    }
    
    # Validate script output
    result = await sandbox_env.validate_script_output("test.sh", expected)
    assert result[0], f"Output validation failed: {result[1]}"

@pytest.mark.asyncio
async def test_error_stream_validation(sandbox_env):
    """Test error stream validation."""
    # Create test script
    script = """#!/bin/bash
echo "Standard output"
echo "Error message" >&2
"""
    await sandbox_env.write_file("test.sh", script)
    
    # Define expected output
    expected = {
        'output': 'Standard output\n',
        'error': 'Error message\n',
        'exit_code': 0
    }
    
    # Validate script output
    result = await sandbox_env.validate_script_output("test.sh", expected)
    assert result[0], f"Output validation failed: {result[1]}"

@pytest.mark.asyncio
async def test_exit_code_validation(sandbox_env):
    """Test exit code validation."""
    # Create test script
    script = """#!/bin/bash
echo "About to exit"
exit 42
"""
    await sandbox_env.write_file("test.sh", script)
    
    # Define expected output
    expected = {
        'output': 'About to exit\n',
        'error': '',
        'exit_code': 42
    }
    
    # Validate script output
    result = await sandbox_env.validate_script_output("test.sh", expected)
    assert result[0], f"Output validation failed: {result[1]}" 