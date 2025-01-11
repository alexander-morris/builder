import os
import base64

class SimpleSandbox:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        print(f"[Mock] Initialized sandbox in {workspace_path}")
        
    def create_container(self):
        print("[Mock] Created sandbox container")
        
    def execute_command(self, command: str):
        print(f"[Mock] Executing command: {command}")
        return {
            "exit_code": 0,
            "output": f"Mock output for: {command}"
        }
        
    def write_file(self, path: str, content: str):
        """Write file content to the actual filesystem for demo purposes."""
        full_path = os.path.join(self.workspace_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return {"exit_code": 0, "output": f"Wrote file: {path}"}
        
    def cleanup(self):
        print("[Mock] Cleaned up sandbox") 