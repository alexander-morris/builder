import os
import shutil
from pathlib import Path
from typing import List, Dict

class FileSystemManager:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        if not self.workspace_path.exists():
            self.workspace_path.mkdir(parents=True)
            
    def _ensure_path_in_workspace(self, path: Path) -> bool:
        """Check if a path is within the workspace directory."""
        try:
            return path.resolve().is_relative_to(self.workspace_path.resolve())
        except ValueError:
            return False
            
    def list_directory(self, relative_path: str = ".") -> Dict[str, List[str]]:
        """List contents of a directory within the workspace."""
        target_path = (self.workspace_path / relative_path).resolve()
        
        if not self._ensure_path_in_workspace(target_path):
            raise ValueError("Access denied: Path outside workspace")
            
        if not target_path.exists():
            raise FileNotFoundError(f"Directory not found: {relative_path}")
            
        files = []
        directories = []
        
        for item in target_path.iterdir():
            if item.is_file():
                files.append(item.name)
            elif item.is_dir():
                directories.append(item.name)
                
        return {
            "files": sorted(files),
            "directories": sorted(directories)
        }
        
    def create_file(self, relative_path: str, content: str) -> None:
        """Create a file within the workspace."""
        target_path = (self.workspace_path / relative_path).resolve()
        
        if not self._ensure_path_in_workspace(target_path):
            raise ValueError("Access denied: Path outside workspace")
            
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content)
        
    def read_file(self, relative_path: str) -> str:
        """Read a file from the workspace."""
        target_path = (self.workspace_path / relative_path).resolve()
        
        if not self._ensure_path_in_workspace(target_path):
            raise ValueError("Access denied: Path outside workspace")
            
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
            
        return target_path.read_text()
        
    def delete_path(self, relative_path: str) -> None:
        """Delete a file or directory within the workspace."""
        target_path = (self.workspace_path / relative_path).resolve()
        
        if not self._ensure_path_in_workspace(target_path):
            raise ValueError("Access denied: Path outside workspace")
            
        if not target_path.exists():
            raise FileNotFoundError(f"Path not found: {relative_path}")
            
        if target_path.is_file():
            target_path.unlink()
        else:
            shutil.rmtree(target_path)
            
    def create_directory(self, relative_path: str) -> None:
        """Create a directory within the workspace."""
        target_path = (self.workspace_path / relative_path).resolve()
        
        if not self._ensure_path_in_workspace(target_path):
            raise ValueError("Access denied: Path outside workspace")
            
        target_path.mkdir(parents=True, exist_ok=True) 