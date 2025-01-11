import os
import pytest
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from src.sandbox.environment import SandboxEnvironment
from src.api.claude_client import ClaudeClient

@pytest.fixture
def mock_claude_client():
    with patch("src.api.claude_client.ClaudeClient") as mock:
        mock.return_value.send_message = AsyncMock()
        yield mock.return_value

@pytest.fixture
def sandbox_env(mock_claude_client):
    with tempfile.TemporaryDirectory() as temp_dir:
        env = SandboxEnvironment(
            workspace_path=temp_dir,
            api_key="test_key"
        )
        env.claude = mock_claude_client
        yield env

@pytest.mark.asyncio
async def test_agent_express_development(sandbox_env, mock_claude_client):
    """Test that the agent can create an Express.js app in the sandbox."""
    # Mock agent's response to create Express app
    mock_claude_client.send_message.return_value = {
        "role": "assistant",
        "content": """I'll create a basic Express.js app:
        ```
        npm init -y
        npm install express
        ```
        
        Now I'll create the server file:
        ```
        echo 'const express = require("express");
        const app = express();
        const port = 3000;
        
        app.get("/", (req, res) => {
          res.send("Hello World from agent-created Express app!");
        });
        
        app.listen(port, () => {
          console.log(`Server running at http://localhost:${port}`);
        });' > server.js
        ```
        
        Let's start the server:
        ```
        node server.js &
        ```
        """
    }
    
    # Mock container creation and command execution
    await sandbox_env.create_container()
    with patch.object(sandbox_env, "execute_command") as mock_execute:
        mock_execute.return_value = {"exit_code": 0, "output": "Command succeeded"}
        
        # Request agent to create Express app
        response = await sandbox_env.execute_agent_task(
            "Create a basic Express.js app that serves 'Hello World'"
        )
        
        # Verify commands were executed
        assert mock_execute.call_count >= 3  # npm init, npm install, node server.js
        assert response["exit_code"] == 0

@pytest.mark.asyncio
async def test_agent_error_handling(sandbox_env, mock_claude_client):
    """Test that the agent handles errors appropriately."""
    # Mock agent's response
    mock_claude_client.send_message.return_value = {
        "role": "error",
        "content": "Failed to communicate with API"
    }
    
    # Create container
    await sandbox_env.create_container()
    
    # Execute task
    with pytest.raises(RuntimeError, match="Failed to communicate with API"):
        await sandbox_env.execute_agent_task("Invalid task")

@pytest.mark.asyncio
async def test_agent_context_updates(sandbox_env, mock_claude_client):
    """Test that the agent receives workspace context updates."""
    # Mock workspace state
    mock_state = {
        "files": ["package.json", "server.js"],
        "directories": ["node_modules"],
        "last_command_output": "npm install completed"
    }
    
    # Create container
    await sandbox_env.create_container()
    
    # Mock command execution to return workspace state
    with patch.object(sandbox_env, "execute_command") as mock_execute:
        mock_execute.return_value = {
            "exit_code": 0,
            "output": "package.json server.js node_modules/"
        }
        
        # Execute task
        response = await sandbox_env.execute_agent_task("Check workspace state")
        
        # Verify context was updated
        assert mock_claude_client.update_context.called
        context = mock_claude_client.update_context.call_args[0][0]
        assert "package.json" in context
        assert "server.js" in context
        assert "node_modules" in context 