import os
import pytest
from pathlib import Path
from src.sandbox.environment import SandboxEnvironment

@pytest.fixture
def sandbox():
    """Create a sandbox environment for testing."""
    # Create a temporary workspace directory
    workspace = Path("agent_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Initialize sandbox
    sandbox = SandboxEnvironment(str(workspace))
    sandbox.create_container()
    
    yield sandbox
    
    # Cleanup
    sandbox.cleanup()
    if workspace.exists():
        for file in workspace.iterdir():
            file.unlink()
        workspace.rmdir()

def test_agent_script_creation(sandbox):
    """
    Test the full agent workflow of creating and executing a script.
    
    This test verifies that:
    1. A script can be created in the sandbox
    2. The script has correct permissions
    3. The script can be executed
    4. The output is correctly captured
    """
    # Create script file
    result = sandbox.execute_command('sh -c \'echo "#!/bin/sh" > test_script.sh\'')
    assert result['exit_code'] == 0, "Failed to create script header"
    
    result = sandbox.execute_command('sh -c \'echo "echo hello world" >> test_script.sh\'')
    assert result['exit_code'] == 0, "Failed to append script content"
    
    # Verify script was created
    result = sandbox.execute_command('cat test_script.sh')
    assert result['exit_code'] == 0, "Script file not created"
    assert "#!/bin/sh" in result['output'], "Script header not found"
    
    # Make script executable
    result = sandbox.execute_command('chmod +x test_script.sh')
    assert result['exit_code'] == 0, "Failed to make script executable"
    
    # Verify script exists and has correct permissions
    result = sandbox.execute_command('ls -l test_script.sh')
    assert result['exit_code'] == 0, "Script file not found"
    assert 'x' in result['output'], "Script is not executable"
    
    # Execute script and verify output
    result = sandbox.execute_command('./test_script.sh')
    assert result['exit_code'] == 0, "Script execution failed"
    assert "hello world" in result['output'], "Script output does not match expected"
    
    # Verify script execution was logged
    result = sandbox.execute_command('cat test_script.sh')
    assert result['exit_code'] == 0, "Cannot read script content"
    assert "#!/bin/sh" in result['output'], "Script content verification failed" 