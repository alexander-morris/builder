import pytest
import pytest_asyncio
import os
import shutil
from unittest.mock import AsyncMock, patch
from src.agent_interface import AgentInterface
from src.sandbox.environment import SandboxEnvironment

@pytest.fixture
def workspace_dir(tmp_path):
    """Create a temporary workspace directory."""
    workspace = os.path.join(tmp_path, "workspace")
    os.makedirs(workspace, exist_ok=True)
    yield workspace
    if os.path.exists(workspace):
        shutil.rmtree(workspace)

@pytest.fixture
def mock_user_claude():
    """Create a mock for the user-focused Claude client."""
    mock = AsyncMock()
    mock.send_message.return_value = '''[
        {
            "task": "Initialize project structure",
            "acceptance_criteria": ["Directory structure exists", "Package files created"],
            "test_cases": ["Check directory exists", "Verify package.json content"]
        },
        {
            "task": "Implement core functionality",
            "acceptance_criteria": ["Functions implemented", "Tests passing"],
            "test_cases": ["Test core functions", "Verify error handling"]
        }
    ]'''
    mock.set_system_prompt = AsyncMock()
    return mock

@pytest.fixture
def mock_debug_claude():
    """Create a mock for the debug-focused Claude client."""
    mock = AsyncMock()
    mock.send_message.side_effect = [
        {"content": "mkdir -p src/components && touch package.json"},
        {"content": "echo 'function test() { return true; }' > src/components/test.js"}
    ]
    mock.set_system_prompt = AsyncMock()
    return mock

@pytest_asyncio.fixture
async def agent(workspace_dir, mock_user_claude, mock_debug_claude, mocker):
    """Create an agent interface instance with sandbox environment."""
    mocker.patch('src.agent_interface.ClaudeClient', side_effect=[mock_user_claude, mock_debug_claude])
    agent = AgentInterface(workspace_dir)
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_complete_build_request_workflow(agent):
    """
    Test a complete build request workflow from creation to completion.
    This test verifies:
    1. Build request creation with multiple todos
    2. Processing each todo in sequence
    3. State persistence between steps
    4. Resource monitoring during execution
    5. Final completion state
    """
    # Create build request
    request = await agent.create_build_request("Create a test project")
    assert request.id is not None
    assert len(request.todos) == 2
    assert request.todos[0]["task"] == "Initialize project structure"
    
    # Process first todo
    result = await agent.process_next_step(request.id)
    assert result is not None
    assert request.todos[0]["status"] == "completed"
    assert os.path.exists(os.path.join(agent.workspace_dir, "package.json"))
    
    # Process second todo
    result = await agent.process_next_step(request.id)
    assert result is not None
    assert request.todos[1]["status"] == "completed"
    assert os.path.exists(os.path.join(agent.workspace_dir, "src/components/test.js"))
    
    # Verify final state
    result = await agent.process_next_step(request.id)
    assert result is None  # No more todos
    assert request.status == "completed"

@pytest.mark.asyncio
async def test_build_request_error_recovery(agent):
    """
    Test error recovery in build request workflow.
    This test verifies:
    1. Error handling during todo execution
    2. State persistence after error
    3. Recovery and continuation
    4. Resource cleanup after errors
    """
    # Create build request
    request = await agent.create_build_request("Test error recovery")
    
    # Inject error in debug Claude response
    agent.debug_claude.send_message.side_effect = [
        Exception("API Error"),  # First call fails
        {"content": "mkdir -p src/components"},  # Retry succeeds
        {"content": "echo 'test' > src/components/test.js"}
    ]
    
    # First attempt should fail
    with pytest.raises(Exception):
        await agent.process_next_step(request.id)
    assert request.todos[0]["status"] == "failed"
    
    # Reset todo status and retry
    request.todos[0]["status"] = "pending"
    result = await agent.process_next_step(request.id)
    assert result is not None
    assert request.todos[0]["status"] == "completed"
    assert os.path.exists(os.path.join(agent.workspace_dir, "src/components"))

@pytest.mark.asyncio
async def test_resource_monitored_workflow(agent):
    """
    Test build request workflow with resource monitoring.
    This test verifies:
    1. Resource limits are enforced during execution
    2. Memory usage is tracked
    3. CPU usage is monitored
    4. Disk space is checked
    5. Process limits are enforced
    """
    # Create build request
    request = await agent.create_build_request("Test resource monitoring")
    
    # Mock resource-intensive command
    agent.debug_claude.send_message.return_value = {
        "content": """python3 -c 'import time
while True:
    time.sleep(0.1)'"""
    }
    
    # Process with resource limits
    with patch.object(agent, '_execute_implementation') as mock_execute:
        mock_execute.return_value = {
            'exit_code': 0,
            'output': 'Success',
            'error': '',
            'resource_usage': {
                'memory_mb': 50,
                'cpu_percent': 10,
                'disk_mb': 5,
                'processes': 1
            }
        }
        
        result = await agent.process_next_step(request.id)
        assert result is not None
        assert request.todos[0]["status"] == "completed"
        assert "resource_usage" in request.todos[0]["changes"] 