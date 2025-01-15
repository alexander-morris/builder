import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from src.agent_interface import AgentInterface, BuildRequest
import os
import shutil

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
    mock.send_message.return_value = '[{"task": "Test task", "acceptance_criteria": ["Criteria 1"], "test_cases": ["Test case 1"]}]'
    mock.set_system_prompt = AsyncMock()
    return mock

@pytest.fixture
def mock_debug_claude():
    """Create a mock for the debug-focused Claude client."""
    mock = AsyncMock()
    mock.send_message.return_value = {"content": "Test debug response"}
    mock.set_system_prompt = AsyncMock()
    return mock

@pytest_asyncio.fixture
async def agent(workspace_dir, mock_user_claude, mock_debug_claude, mocker):
    """Create an agent interface instance."""
    mocker.patch('src.agent_interface.ClaudeClient', side_effect=[mock_user_claude, mock_debug_claude])
    agent = AgentInterface(workspace_dir)
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_create_build_request(agent):
    """Test creating a new build request."""
    request = await agent.create_build_request("Test project")
    assert request.id is not None
    assert len(request.todos) == 1
    assert request.todos[0]["task"] == "Test task"

@pytest.mark.asyncio
async def test_process_next_step(agent):
    """Test processing the next step in a build request."""
    request = await agent.create_build_request("Test project")
    result = await agent.process_next_step(request.id)
    assert result == "Test debug response"

@pytest.mark.asyncio
async def test_execute_implementation(agent):
    """Test executing implementation from debug Claude."""
    request = await agent.create_build_request("Test project")
    await agent.process_next_step(request.id)
    assert request.todos[0]["status"] == "completed"

@pytest.mark.asyncio
async def test_log_handoff(agent):
    """Test logging task handoffs."""
    request = await agent.create_build_request("Test project")
    await agent.process_next_step(request.id)
    assert request.todos[0]["changes"] is not None

@pytest.mark.asyncio
async def test_error_handling(agent):
    """Test error handling in process_next_step."""
    request = await agent.create_build_request("Test project")
    request.todos[0]["task"] = None
    with pytest.raises(ValueError):
        await agent.process_next_step(request.id)
    assert request.todos[0]["status"] == "failed"

@pytest.mark.asyncio
async def test_invalid_todo_format(agent):
    """Test handling invalid todo format."""
    request = await agent.create_build_request("Test project")
    request.todos[0]["acceptance_criteria"] = None
    with pytest.raises(ValueError):
        await agent.process_next_step(request.id)
    assert request.todos[0]["status"] == "failed"

@pytest.mark.asyncio
async def test_missing_required_fields(agent):
    """Test handling todos with missing required fields."""
    request = await agent.create_build_request("Test project")
    del request.todos[0]["test_cases"]
    with pytest.raises(ValueError):
        await agent.process_next_step(request.id)
    assert request.todos[0]["status"] == "failed"

@pytest.mark.asyncio
async def test_completed_request(agent):
    """Test handling a completed request."""
    request = await agent.create_build_request("Test project")
    request.todos[0]["status"] = "completed"
    result = await agent.process_next_step(request.id)
    assert result is None 