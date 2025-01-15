import os
import pytest
import pytest_asyncio
import shutil
from src.sandbox.environment import SandboxEnvironment

@pytest_asyncio.fixture
async def sandbox_env():
    """Create a sandbox environment for testing."""
    # Create a fresh workspace for each test
    workspace_dir = "./test_workspace_git"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    os.makedirs(workspace_dir, exist_ok=True)
    
    env = SandboxEnvironment(workspace_dir=workspace_dir)
    await env.create_container()
    yield env
    await env.cleanup()

@pytest.mark.asyncio
async def test_git_init(sandbox_env):
    """Test Git repository initialization."""
    # Initialize Git repository
    result = await sandbox_env.execute_command("git init")
    assert result["exit_code"] == 0
    assert "Initialized empty Git repository" in result["output"]
    
    # Verify .git directory exists
    result = await sandbox_env.execute_command("ls -la .git")
    assert result["exit_code"] == 0
    assert "HEAD" in result["output"]
    assert "config" in result["output"]

@pytest.mark.asyncio
async def test_git_config(sandbox_env):
    """Test Git configuration."""
    # Set Git user configuration
    result = await sandbox_env.execute_command('git config --global user.email "test@example.com"')
    assert result["exit_code"] == 0
    
    result = await sandbox_env.execute_command('git config --global user.name "Test User"')
    assert result["exit_code"] == 0
    
    # Verify configuration
    result = await sandbox_env.execute_command("git config --get user.email")
    assert result["exit_code"] == 0
    assert "test@example.com" in result["output"]

@pytest.mark.asyncio
async def test_git_basic_operations(sandbox_env):
    """Test basic Git operations."""
    # Initialize repository
    await sandbox_env.execute_command("git init")
    await sandbox_env.execute_command('git config --global user.email "test@example.com"')
    await sandbox_env.execute_command('git config --global user.name "Test User"')
    
    # Create and add a file
    await sandbox_env.write_file("test.txt", "test content")
    result = await sandbox_env.execute_command("git add test.txt")
    assert result["exit_code"] == 0
    
    # Check status
    result = await sandbox_env.execute_command("git status")
    assert result["exit_code"] == 0
    assert "new file:   test.txt" in result["output"]
    
    # Commit changes
    result = await sandbox_env.execute_command('git commit -m "Initial commit"')
    assert result["exit_code"] == 0
    assert "Initial commit" in result["output"]

@pytest.mark.asyncio
async def test_git_branch_operations(sandbox_env):
    """Test Git branch operations."""
    # Set up repository with initial commit
    await sandbox_env.execute_command("git init")
    await sandbox_env.execute_command('git config --global user.email "test@example.com"')
    await sandbox_env.execute_command('git config --global user.name "Test User"')
    await sandbox_env.write_file("test.txt", "test content")
    await sandbox_env.execute_command("git add test.txt")
    await sandbox_env.execute_command('git commit -m "Initial commit"')
    
    # Create and switch to new branch
    result = await sandbox_env.execute_command("git checkout -b feature")
    assert result["exit_code"] == 0
    assert "Switched to a new branch 'feature'" in result["output"]
    
    # Make changes in new branch
    await sandbox_env.write_file("feature.txt", "feature content")
    await sandbox_env.execute_command("git add feature.txt")
    await sandbox_env.execute_command('git commit -m "Add feature"')
    
    # Switch back to main branch
    result = await sandbox_env.execute_command("git checkout main")
    assert result["exit_code"] == 0
    
    # Verify feature.txt doesn't exist in main branch
    result = await sandbox_env.execute_command("ls feature.txt")
    assert result["exit_code"] != 0

@pytest.mark.asyncio
async def test_git_remote_operations(sandbox_env):
    """Test Git remote operations."""
    # Initialize repository
    await sandbox_env.execute_command("git init")
    await sandbox_env.execute_command('git config --global user.email "test@example.com"')
    await sandbox_env.execute_command('git config --global user.name "Test User"')
    
    # Add remote
    result = await sandbox_env.execute_command("git remote add origin https://github.com/test/repo.git")
    assert result["exit_code"] == 0
    
    # Verify remote
    result = await sandbox_env.execute_command("git remote -v")
    assert result["exit_code"] == 0
    assert "origin" in result["output"]
    assert "https://github.com/test/repo.git" in result["output"]
    
    # Test fetch (should fail due to non-existent remote)
    result = await sandbox_env.execute_command("git fetch origin")
    assert result["exit_code"] != 0
    assert "could not resolve host: github.com" in result["output"].lower()

@pytest.mark.asyncio
async def test_git_error_handling(sandbox_env):
    """Test Git error handling."""
    # Test command in non-git directory
    result = await sandbox_env.execute_command("git status")
    assert result["exit_code"] != 0
    assert "not a git repository" in result["output"].lower()
    
    # Test invalid remote URL
    await sandbox_env.execute_command("git init")
    result = await sandbox_env.execute_command("git remote add origin invalid://url")
    assert result["exit_code"] != 0
    
    # Test commit without user config
    await sandbox_env.write_file("test.txt", "test content")
    await sandbox_env.execute_command("git add test.txt")
    result = await sandbox_env.execute_command('git commit -m "test"')
    assert result["exit_code"] != 0
    assert "please tell me who you are" in result["output"].lower()

@pytest.mark.asyncio
async def test_git_ssh_key_handling(sandbox_env):
    """Test Git SSH key handling."""
    # Test SSH key generation
    result = await sandbox_env.execute_command('ssh-keygen -t rsa -N "" -f /tmp/id_rsa')
    assert result["exit_code"] == 0
    
    # Verify key files exist
    result = await sandbox_env.execute_command("ls -la /tmp/id_rsa*")
    assert result["exit_code"] == 0
    assert "id_rsa" in result["output"]
    assert "id_rsa.pub" in result["output"]
    
    # Test SSH config
    ssh_config = """Host github.com
    IdentityFile /tmp/id_rsa
    UserKnownHostsFile /tmp/known_hosts
    StrictHostKeyChecking no
"""
    await sandbox_env.write_file("/tmp/ssh_config", ssh_config)
    
    # Test SSH connection (should fail due to key not being registered)
    result = await sandbox_env.execute_command("GIT_SSH_COMMAND='ssh -F /tmp/ssh_config' git ls-remote git@github.com:test/repo.git")
    assert result["exit_code"] != 0
    assert "permission denied" in result["output"].lower() 