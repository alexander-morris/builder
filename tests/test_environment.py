import os
import pytest
from pathlib import Path
from src.utils.environment import EnvironmentManager

@pytest.fixture
def tmp_path():
    path = Path("test_workspace")
    path.mkdir(exist_ok=True)
    yield path
    if path.exists():
        import shutil
        shutil.rmtree(path)

def test_env_file_loading(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-key-not-real-xxxxx\n"
        "MEMORY_LIMIT=512m\n"
        "CPU_LIMIT=90\n"
        "LOG_LEVEL=DEBUG\n"
        "TEST_SECRET=test123\n"
    )
    
    env_manager = EnvironmentManager(env_file)
    assert os.getenv("ANTHROPIC_API_KEY") == "test-key-not-real-xxxxx"
    assert os.getenv("MEMORY_LIMIT") == "512m"
    assert os.getenv("CPU_LIMIT") == "90"
    assert os.getenv("LOG_LEVEL") == "DEBUG"
    assert os.getenv("TEST_SECRET") == "test123"

def test_custom_shell_config(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-key-not-real-xxxxx\n"
        "TEST_SECRET=test123\n"
    )
    
    env_manager = EnvironmentManager(env_file)
    shell_env = env_manager.get_shell_env()
    
    # Check that sensitive variables are not included
    assert "ANTHROPIC_API_KEY" not in shell_env
    assert "TEST_SECRET" not in shell_env
    
    # Check that standard variables are included
    assert "PATH" in shell_env
    assert "USER" in shell_env
    assert "HOME" in shell_env

def test_workspace_setup(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-key-not-real-xxxxx\n"
        "WORKSPACE_PATH=test_workspace\n"
    )
    
    env_manager = EnvironmentManager(env_file)
    env_manager.setup_workspace()
    
    workspace = Path("test_workspace")
    assert workspace.exists()
    assert workspace.is_dir()
    
    # Check standard directories
    assert (workspace / "src").exists()
    assert (workspace / "lib").exists()
    assert (workspace / "logs").exists()
    
    # Check permissions
    assert workspace.stat().st_mode & 0o777 == 0o755

def test_config_masking(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-key-not-real-xxxxx\n"
        "TEST_SECRET=test123\n"
        "PUBLIC_VAR=hello\n"
    )
    
    env_manager = EnvironmentManager(env_file)
    config = env_manager.get_config()
    
    # Check that sensitive values are masked
    assert config["ANTHROPIC_API_KEY"] == "********"
    assert config["TEST_SECRET"] == "********"
    
    # Check that non-sensitive values are visible
    assert config["PUBLIC_VAR"] == "hello"

def test_workspace_validation(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-key-not-real-xxxxx\n"
        "WORKSPACE_PATH=test_workspace\n"
    )
    
    env_manager = EnvironmentManager(env_file)
    env_manager.setup_workspace()
    
    # Should not raise any errors
    env_manager.validate_workspace()
    
    # Remove a required directory
    import shutil
    shutil.rmtree("test_workspace/src")
    
    # Should raise ValueError
    with pytest.raises(ValueError):
        env_manager.validate_workspace()

def test_cleanup(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=test-key-not-real-xxxxx\n"
        "WORKSPACE_PATH=test_workspace\n"
    )
    
    env_manager = EnvironmentManager(env_file)
    env_manager.setup_workspace()
    
    workspace = Path("test_workspace")
    assert workspace.exists()
    
    env_manager.cleanup()
    assert not workspace.exists()

def test_invalid_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("INVALID_FORMAT")
    
    with pytest.raises(ValueError, match="Missing required environment variables"):
        EnvironmentManager(env_file) 