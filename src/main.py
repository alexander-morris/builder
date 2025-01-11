import os
import asyncio
from pathlib import Path
from typing import Optional, Dict

from api.claude_client import ClaudeClient
from sandbox.environment import SandboxEnvironment
from utils.filesystem import FileSystemManager

class LLMAgent:
    def __init__(
        self,
        workspace_path: str,
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None
    ):
        self.workspace_path = Path(workspace_path)
        self.sandbox = SandboxEnvironment(workspace_path)
        self.fs_manager = FileSystemManager(workspace_path)
        self.claude = ClaudeClient(api_key)
        
        if system_prompt:
            self.claude.set_system_prompt(system_prompt)
            
    async def initialize(self) -> None:
        """Initialize the sandbox environment."""
        self.sandbox.create_container()
        workspace_state = self.fs_manager.list_directory()
        self.claude.update_context(workspace_state)
        
    async def execute_task(self, task_description: str) -> Dict[str, str]:
        """Execute a task using the LLM agent."""
        response = await self.claude.send_message(task_description)
        
        if response["role"] == "error":
            return response
            
        # Update context with current workspace state
        workspace_state = self.fs_manager.list_directory()
        self.claude.update_context(workspace_state)
        
        return response
        
    def cleanup(self) -> None:
        """Clean up resources."""
        self.sandbox.cleanup()

async def main():
    # Example usage
    workspace_path = Path("agent_workspace")
    
    system_prompt = """You are an AI agent with access to a sandboxed development environment.
    You can read and write files, execute commands, and manage the workspace directory.
    All operations must be performed within the designated workspace for security.
    """
    
    agent = LLMAgent(
        workspace_path=str(workspace_path),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        system_prompt=system_prompt
    )
    
    try:
        await agent.initialize()
        
        # Example task
        result = await agent.execute_task(
            "Create a simple Python script that prints 'Hello, World!' and run it."
        )
        print(f"Task result: {result}")
        
    finally:
        agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 