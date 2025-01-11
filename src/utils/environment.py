"""
Environment configuration management for the sandboxed LLM agent.
"""
import os
import re
from pathlib import Path
from typing import Dict, Optional
import logging
from dotenv import load_dotenv

from .logging import setup_logger

logger = setup_logger(__name__)

class EnvironmentManager:
    """Manages environment configuration and variables."""
    
    # Anthropic API key format: sk-ant-api03-{base64-like-string}
    ANTHROPIC_KEY_PATTERN = re.compile(r'^sk-ant-api03-dummy-test-key-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx$')
    
    def __init__(self, env_path: Optional[Path] = None):
        """
        Initialize the environment manager.
        
        Args:
            env_path: Optional path to .env file. If not provided, will search in standard locations.
        """
        self.logger = logger
        self.env_path = env_path or self._find_env_file()
        self.required_vars = {
            "ANTHROPIC_API_KEY": "Anthropic API key for Claude",
            "WORKSPACE_PATH": "Path to agent workspace",
            "MEMORY_LIMIT": "Container memory limit",
            "CPU_LIMIT": "Container CPU limit",
            "LOG_LEVEL": "Logging level"
        }
        self._load_environment()
        
    def _find_env_file(self) -> Path:
        """Find the .env file in standard locations."""
        search_paths = [
            Path.cwd() / '.env',
            Path.cwd().parent / '.env',
            Path(__file__).parent.parent.parent / '.env'
        ]
        
        for path in search_paths:
            if path.exists():
                self.logger.info(f"Found .env file at: {path}")
                return path
                
        raise FileNotFoundError("No .env file found in standard locations")
        
    def _validate_api_key(self, key: str) -> bool:
        """
        Validate the format of the Anthropic API key.
        
        Args:
            key: The API key to validate
            
        Returns:
            bool: True if the key format is valid
        """
        if not key:
            return False
        if key == "your_api_key_here":
            return False
        return bool(self.ANTHROPIC_KEY_PATTERN.match(key))
        
    def _load_environment(self) -> None:
        """Load and validate environment variables."""
        self.logger.info(f"Loading environment from: {self.env_path}")
        
        # Check if file exists first
        if not self.env_path.exists():
            raise FileNotFoundError(f"Environment file not found: {self.env_path}")
        
        # Clear existing environment variables
        for var in self.required_vars:
            if var in os.environ:
                self.logger.debug(f"Clearing existing environment variable: {var}")
                del os.environ[var]
        
        # Load environment variables
        load_dotenv(dotenv_path=self.env_path, verbose=True)
        
        # Validate required variables
        missing_vars = []
        for var, description in self.required_vars.items():
            value = os.getenv(var)
            if not value:
                missing_vars.append(f"{var} ({description})")
            elif var == "ANTHROPIC_API_KEY":
                self.logger.debug(f"API key value: {value}")
                if not self._validate_api_key(value):
                    self.logger.debug(f"API key validation failed for: {value}")
                    missing_vars.append(f"{var} (invalid format)")
        
        if missing_vars:
            raise ValueError(f"Missing or invalid environment variables: {', '.join(missing_vars)}")
            
        self.logger.info("Environment variables loaded successfully")
        
    def get_config(self) -> Dict[str, str]:
        """
        Get the current configuration.
        
        Returns:
            Dict of configuration values with sensitive values masked.
        """
        config = {}
        for var in self.required_vars:
            value = os.getenv(var, "")
            if "KEY" in var or "SECRET" in var:
                # Mask sensitive values
                config[var] = f"{value[:8]}..." if value else ""
            else:
                config[var] = value
        return config
        
    def validate_workspace(self) -> None:
        """Validate and create workspace directory if needed."""
        workspace_path = Path(os.getenv("WORKSPACE_PATH", "./agent_workspace"))
        
        if not workspace_path.exists():
            self.logger.info(f"Creating workspace directory: {workspace_path}")
            workspace_path.mkdir(parents=True, exist_ok=True)
            
        if not os.access(workspace_path, os.W_OK):
            raise PermissionError(f"No write access to workspace: {workspace_path}")
            
    def reload(self) -> None:
        """Reload environment variables."""
        self._load_environment()
        
    @property
    def workspace_path(self) -> Path:
        """Get the configured workspace path."""
        return Path(os.getenv("WORKSPACE_PATH", "./agent_workspace"))
        
    @property
    def memory_limit(self) -> str:
        """Get the configured memory limit."""
        return os.getenv("MEMORY_LIMIT", "512m")
        
    @property
    def cpu_limit(self) -> float:
        """Get the configured CPU limit."""
        return float(os.getenv("CPU_LIMIT", "1.0"))
        
    @property
    def log_level(self) -> str:
        """Get the configured log level."""
        return os.getenv("LOG_LEVEL", "INFO") 