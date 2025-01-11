import os
import pytest
import tempfile
from pathlib import Path
import logging
from dotenv import load_dotenv

from src.sandbox.environment import SandboxEnvironment
from src.utils.filesystem import FileSystemManager
from src.api.claude_client import ClaudeClient
from src.utils.logging import setup_logger

# Load environment variables from .env file
logger = setup_logger(__name__)
logger.info("Loading environment variables from .env file")

# Get the absolute path to the .env file
env_path = Path(__file__).parent.parent / '.env'
logger.info(f"Loading .env file from: {env_path}")
load_dotenv(dotenv_path=env_path, verbose=True)

@pytest.fixture
def workspace_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def sandbox(workspace_dir):
    sandbox = SandboxEnvironment(workspace_dir)
    sandbox.create_container()
    yield sandbox
    sandbox.cleanup()

@pytest.fixture
def fs_manager(workspace_dir):
    return FileSystemManager(workspace_dir)

@pytest.fixture
def claude_client():
    # Check for valid API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    logger.info("Environment variables loaded:")
    for key, value in os.environ.items():
        if "API" in key or "KEY" in key:
            logger.info(f"{key}: {value[:8]}...")
        else:
            logger.info(f"{key}: {value}")
    
    if not api_key:
        logger.warning("⚠️ No Anthropic API key found in environment. Claude API tests will be skipped.")
        pytest.skip("No Anthropic API key provided")
    if api_key == "your_api_key_here":
        logger.warning("⚠️ Using placeholder API key. Please set your actual Anthropic API key in .env file.")
        pytest.skip("No valid Anthropic API key provided")
        
    logger.info(f"Using Anthropic API key: {api_key[:8]}...")
    return ClaudeClient(api_key)

def test_sandbox_creation(sandbox):
    """Test that sandbox container is created successfully."""
    assert sandbox.container is not None
    assert sandbox.container.status == "running"

def test_command_execution(sandbox):
    """Test command execution in sandbox."""
    result = sandbox.execute_command("echo 'test'")
    assert result["exit_code"] == 0
    assert "test" in result["output"]

def test_filesystem_operations(fs_manager):
    """Test filesystem operations within workspace."""
    # Create and verify directory
    fs_manager.create_directory("test_dir")
    contents = fs_manager.list_directory()
    assert "test_dir" in contents["directories"]
    
    # Create and verify file
    fs_manager.create_file("test_dir/test.txt", "Hello, World!")
    file_contents = fs_manager.read_file("test_dir/test.txt")
    assert file_contents == "Hello, World!"
    
    # Test path security
    with pytest.raises(ValueError):
        fs_manager.create_file("../outside.txt", "test")
    
    with pytest.raises(ValueError):
        fs_manager.read_file("../outside.txt")

def test_sandbox_isolation(sandbox):
    """Test that sandbox is properly isolated."""
    # Test filesystem isolation
    fs_tests = [
        ("touch /etc/new_file", "system files", 1),
        ("touch /root/test", "root directory", 1),
        ("touch /home/test", "home directory", 1),
        ("mkdir -p ../outside", "parent directory", 1),
        ("cat /etc/passwd", "sandbox user info", 0)
    ]
    for cmd, desc, expected_code in fs_tests:
        result = sandbox.execute_command(cmd)
        assert result["exit_code"] == expected_code, f"Unexpected result when accessing {desc}"
        if cmd == "cat /etc/passwd":
            # Verify that only sandbox user exists in passwd
            assert "sandbox_user:x:1000:1000:Sandbox User:/home/sandbox_user:/bin/sh" in result["output"]
            assert "root:" not in result["output"]
            assert len(result["output"].strip().split("\n")) == 1, "passwd should only contain sandbox user"
    
    # Test network isolation
    net_tests = [
        ("ping -c 1 8.8.8.8", "ping external host"),
        ("wget https://example.com", "download files"),
        ("curl https://example.com", "make HTTP requests"),
        ("nc -zv 8.8.8.8 53", "open network connections")
    ]
    for cmd, desc in net_tests:
        result = sandbox.execute_command(cmd)
        assert result["exit_code"] != 0, f"Should not be able to {desc}"
    
    # Test process isolation
    proc_tests = [
        ("ps aux", "view all processes"),
        ("kill 1", "kill system processes"),
        ("nohup sleep 1000 &", "run background processes"),
        ("sudo ls", "use sudo")
    ]
    for cmd, desc in proc_tests:
        result = sandbox.execute_command(cmd)
        assert result["exit_code"] != 0, f"Should not be able to {desc}"
    
    # Test resource limits
    # Memory limit test (try to allocate more memory than allowed)
    mem_test = '''python3 -c "
import array
a = array.array('b', [0] * (1024 * 1024 * 1024))  # Try to allocate 1GB
"'''
    result = sandbox.execute_command(mem_test)
    assert result["exit_code"] != 0, "Should not be able to exceed memory limit"
    
    # CPU limit test (try to spawn multiple CPU-intensive processes)
    cpu_test = '''python3 -c "
import multiprocessing
def work():
    while True:
        pass
processes = [multiprocessing.Process(target=work) for _ in range(4)]
for p in processes:
    p.start()
for p in processes:
    p.join()
"'''
    result = sandbox.execute_command(cpu_test)
    assert result["exit_code"] != 0, "Should not be able to exceed CPU limit"
    
    # Test user permissions
    user_tests = [
        ("id -u", "1000", "should run as UID 1000"),
        ("id -g", "1000", "should run as GID 1000"),
        ("umask", "0002", "should have restricted umask")
    ]
    for cmd, expected, msg in user_tests:
        result = sandbox.execute_command(cmd)
        assert result["exit_code"] == 0, f"Failed to check {msg}"
        assert expected in result["output"], msg
    
    # Test workspace boundaries
    workspace_tests = [
        ("touch ./allowed.txt", 0, "should allow writing in workspace"),
        ("touch /allowed.txt", 1, "should not allow writing in root"),
        ("mkdir ./allowed_dir", 0, "should allow creating directories in workspace"),
        ("ls -la /proc", 1, "should not allow accessing proc filesystem")
    ]
    for cmd, expected_code, msg in workspace_tests:
        result = sandbox.execute_command(cmd)
        assert result["exit_code"] == expected_code, msg

@pytest.mark.asyncio
async def test_claude_api(claude_client):
    """Test Claude API integration."""
    logger.info("Starting Claude API integration test")
    
    # Set system prompt
    system_prompt = "You are a helpful AI assistant."
    claude_client.set_system_prompt(system_prompt)
    
    # Send a test message
    response = await claude_client.send_message("Say 'hello' and nothing else.")
    assert response["role"] == "assistant", "Unexpected response role"
    assert "hello" in response["content"].lower(), "Expected 'hello' in response"
    
    # Test context updating
    workspace_state = {
        "files": ["test.txt"],
        "directories": ["test_dir"],
        "last_command_output": "test output"
    }
    claude_client.update_context(workspace_state)
    assert "test.txt" in claude_client.system_prompt, "Workspace file not found in system prompt"
    assert "test_dir" in claude_client.system_prompt, "Workspace directory not found in system prompt"
    
    logger.info("Claude API integration test completed successfully") 