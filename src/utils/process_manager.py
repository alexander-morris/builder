"""
Process Manager for enforcing development workflow.
"""
import os
import re
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
import git

@dataclass
class Task:
    priority: int
    description: str
    status: str
    acceptance_criteria: List[str]
    next_steps: List[str]

class ProcessManager:
    def __init__(self, workspace_dir: str):
        """Initialize process manager with workspace directory."""
        self.workspace_dir = workspace_dir
        self.current_task: Optional[Task] = None
        self.repo = git.Repo(workspace_dir)
        self.log_watcher = None  # Will be initialized when needed
        
    def load_todo(self) -> List[Task]:
        """Load tasks from todo.md."""
        todo_path = os.path.join(self.workspace_dir, "todo.md")
        tasks = []
        
        with open(todo_path, 'r') as f:
            content = f.read()
            
        # Parse tasks using regex
        task_pattern = r'PRIORITY-(\d+):\s*([^\n]+)\nStatus:\s*([^\n]+)\nAcceptance Criteria:\n((?:\s*-[^\n]+\n)+)Next Steps:\n((?:\s*-[^\n]+\n)+)'
        matches = re.finditer(task_pattern, content, re.MULTILINE)
        
        for match in matches:
            priority = int(match.group(1))
            description = match.group(2).strip()
            status = match.group(3).strip()
            criteria = [c.strip()[2:] for c in match.group(4).strip().split('\n')]
            steps = [s.strip()[2:] for s in match.group(5).strip().split('\n')]
            
            tasks.append(Task(
                priority=priority,
                description=description,
                status=status,
                acceptance_criteria=criteria,
                next_steps=steps
            ))
            
        return sorted(tasks, key=lambda t: t.priority)
    
    def select_next_task(self) -> Optional[Task]:
        """Select highest priority non-completed task."""
        tasks = self.load_todo()
        for task in tasks:
            if task.status.lower() != "completed":
                self.current_task = task
                return task
        return None
    
    def update_task_status(self, task: Task, new_status: str, next_steps: List[str] = None):
        """Update task status in todo.md."""
        if next_steps is None:
            next_steps = task.next_steps
            
        todo_path = os.path.join(self.workspace_dir, "todo.md")
        with open(todo_path, 'r') as f:
            content = f.read()
            
        # Update status and next steps
        task_pattern = f'PRIORITY-{task.priority}:\\s*{re.escape(task.description)}\\nStatus:\\s*([^\\n]+)'
        new_content = re.sub(
            task_pattern,
            f'PRIORITY-{task.priority}: {task.description}\nStatus: {new_status}',
            content
        )
        
        # Update next steps if provided
        if next_steps:
            steps_pattern = 'Next Steps:\n(?:\s*-[^\n]+\n)+'
            new_steps = 'Next Steps:\n' + '\n'.join(f'  - {step}' for step in next_steps) + '\n'
            new_content = re.sub(steps_pattern, new_steps, new_content)
            
        with open(todo_path, 'w') as f:
            f.write(new_content)
            
        # Commit changes
        self.repo.index.add([todo_path])
        self.repo.index.commit(f"docs(todo): Update PRIORITY-{task.priority} status to {new_status}")
        
    def commit_changes(self, files: List[str], message: str):
        """Commit changes with semantic message."""
        if not message.startswith(('feat', 'fix', 'docs', 'test', 'refactor')):
            raise ValueError("Commit message must start with semantic prefix")
            
        if self.current_task:
            message = f"{message} [PRIORITY-{self.current_task.priority}]"
            
        self.repo.index.add(files)
        self.repo.index.commit(message)
        
    def verify_task_completion(self, task: Task) -> bool:
        """Verify all acceptance criteria are met."""
        # Run tests
        import pytest
        test_result = pytest.main(['--verbose'])
        if test_result != 0:
            return False
            
        # Check logs for errors
        if self.log_watcher and self.log_watcher.has_errors():
            return False
            
        return True
        
    def document_error(self, error: str, context: str):
        """Document error in todo.md if it's a new issue."""
        tasks = self.load_todo()
        error_description = f"Fix error: {error}"
        
        # Check if error is already documented
        for task in tasks:
            if error in task.description:
                return
                
        # Add new task for error
        todo_path = os.path.join(self.workspace_dir, "todo.md")
        with open(todo_path, 'a') as f:
            f.write(f"\nPRIORITY-{len(tasks) + 1}: {error_description}\n")
            f.write("Status: Not Started\n")
            f.write("Acceptance Criteria:\n")
            f.write("  - Error is resolved\n")
            f.write("  - Tests pass\n")
            f.write("  - No regression\n")
            f.write("Next Steps:\n")
            f.write("  - Analyze error context\n")
            f.write("  - Implement fix\n")
            f.write("  - Add tests\n")
            
        # Commit error documentation
        self.repo.index.add([todo_path])
        self.repo.index.commit(f"docs(todo): Add task for error - {error_description}") 