import os
import pytest
import pytest_asyncio
import shutil
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    workspace_dir = "./test_workspace_env"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)
    
    env = SandboxEnvironment(workspace_dir=workspace_dir)
    await env.create_container()
    yield env
    await env.cleanup()

@pytest.mark.asyncio
async def test_default_environment_variables(sandbox_env):
    """Test default environment variables are set correctly."""
    # Test NODE_ENV
    result = await sandbox_env.execute_command("echo $NODE_ENV")
    assert result["exit_code"] == 0
    assert result["output"] == "development"
    
    # Test USER
    result = await sandbox_env.execute_command("echo $USER")
    assert result["exit_code"] == 0
    assert result["output"] == "sandbox_user"

@pytest.mark.asyncio
async def test_custom_environment_variables(sandbox_env):
    """Test setting and reading custom environment variables."""
    # Set custom environment variable
    result = await sandbox_env.execute_command("export CUSTOM_VAR='test value'")
    assert result["exit_code"] == 0
    
    # Read custom environment variable
    result = await sandbox_env.execute_command("echo $CUSTOM_VAR")
    assert result["exit_code"] == 0
    assert result["output"] == "test value"

@pytest.mark.asyncio
async def test_environment_variable_persistence(sandbox_env):
    """Test environment variable persistence across commands."""
    # Set multiple variables
    result = await sandbox_env.execute_command("export VAR1='value1' VAR2='value2'")
    assert result["exit_code"] == 0
    
    # Verify variables persist
    result = await sandbox_env.execute_command("echo $VAR1,$VAR2")
    assert result["exit_code"] == 0
    assert result["output"] == "value1,value2"

@pytest.mark.asyncio
async def test_environment_variable_isolation(sandbox_env):
    """Test environment variable isolation between containers."""
    # Set variable in first container
    result = await sandbox_env.execute_command("export TEST_VAR='container1'")
    assert result["exit_code"] == 0
    
    # Create new container and verify variable is not present
    await sandbox_env.cleanup()
    await sandbox_env.create_container()
    result = await sandbox_env.execute_command("echo $TEST_VAR")
    assert result["exit_code"] == 0
    assert result["output"] == ""  # Variable should not exist in new container 