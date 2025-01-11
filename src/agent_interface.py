"""
Build Agent interface for managing build requests and Claude sessions.
"""

from dataclasses import dataclass, asdict
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from src.api.claude_client import ClaudeClient
from src.sandbox.environment import SimpleSandbox

@dataclass
class BuildRequest:
    id: str
    description: str
    status: str  # pending, in_progress, completed, failed
    todos: List[Dict]
    created_at: str
    updated_at: str
    logs: List[Dict[str, str]]  # Add logs field

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if 'logs' not in data:
            data['logs'] = []  # Initialize logs for older requests
        return cls(**data)

class AgentInterface:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.requests_file = os.path.join(workspace_dir, "build_requests.json")
        
        # Initialize two Claude clients with different roles
        self.user_claude = ClaudeClient()
        self.debug_claude = ClaudeClient()
        
        # Set different system prompts for each role
        self.user_claude.set_system_prompt("""
        You are a helpful assistant focused on understanding user requirements and managing the build process.
        Your role is to:
        1. Help users describe what they want to build
        2. Break down requirements into clear steps
        3. Provide status updates and explain progress
        4. Answer questions about the build process
        
        When generating todos, format them as a list of dictionaries with 'task' and 'status' keys.
        Each task should be specific and actionable.
        """)
        
        self.debug_claude.set_system_prompt("""
        You are a technical debugging assistant focused on solving code and build issues.
        Your role is to:
        1. Generate working code solutions
        2. Analyze error messages and logs
        3. Help troubleshoot build failures
        4. Provide technical explanations
        
        When generating code:
        1. Include all necessary imports
        2. Follow best practices and patterns
        3. Add helpful comments
        4. Consider error handling
        5. Make code modular and maintainable
        """)
        
        self.sandbox = SimpleSandbox(workspace_dir)
        self._load_requests()

    def _add_log(self, request_id: str, message: str, level: str = "info"):
        """Add a log entry to a build request."""
        request = next((r for r in self.requests if r.id == request_id), None)
        if request:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "level": level
            }
            request.logs.append(log_entry)
            self._save_requests()

    def get_logs(self, request_id: str) -> List[Dict[str, str]]:
        """Get all logs for a build request."""
        request = next((r for r in self.requests if r.id == request_id), None)
        if request:
            return request.logs
        return []

    def _load_requests(self):
        if os.path.exists(self.requests_file):
            with open(self.requests_file, 'r') as f:
                self.requests = [BuildRequest.from_dict(r) for r in json.load(f)]
        else:
            self.requests = []

    def _save_requests(self):
        with open(self.requests_file, 'w') as f:
            json.dump([r.to_dict() for r in self.requests], f, indent=2)

    def _parse_code_blocks(self, text: str) -> List[Tuple[str, str]]:
        """Extract code blocks and their file paths from text."""
        # Pattern to match markdown code blocks with optional file paths
        pattern = r"```(\w+)?\s*(?:\[([\w\-\./]+)\])?\n(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)
        
        code_blocks = []
        for match in matches:
            lang = match.group(1) or ""
            path = match.group(2) or ""
            code = match.group(3).strip()
            code_blocks.append((path, code))
            
        return code_blocks

    def create_build_request(self, description: str) -> BuildRequest:
        request = BuildRequest(
            id=f"build_{len(self.requests) + 1}",
            description=description,
            status="pending",
            todos=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            logs=[]  # Initialize empty logs
        )
        
        self._add_log(request.id, f"Created build request: {description}")
        
        # Use user_claude to analyze the request and generate todos
        self._add_log(request.id, "Analyzing request and generating todos...")
        response = self.user_claude.send_message(f"""
        Please analyze this build request and break it down into specific todos:
        {description}
        
        For each todo, specify:
        1. The specific task to be done
        2. Any dependencies or prerequisites
        3. Expected output or success criteria
        
        Format the response as a list of dictionaries with 'task' and 'status' keys.
        Make tasks granular and actionable.
        """)
        
        # Parse the response to extract structured todos
        try:
            # Look for a code block with JSON content
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                todos = json.loads(json_str)
            else:
                # Fallback to default todos
                todos = [
                    {"task": "Initialize project structure", "status": "pending"},
                    {"task": "Set up development environment", "status": "pending"},
                    {"task": "Implement core features", "status": "pending"},
                    {"task": "Add tests and documentation", "status": "pending"},
                    {"task": "Review and optimize", "status": "pending"}
                ]
            
            request.todos = todos
            self._add_log(request.id, f"Generated {len(todos)} todos")
            
        except Exception as e:
            self._add_log(request.id, f"Error parsing todos: {str(e)}", "error")
            request.todos = [
                {"task": "Initialize project structure", "status": "pending"},
                {"task": "Set up development environment", "status": "pending"},
                {"task": "Implement core features", "status": "pending"},
                {"task": "Add tests and documentation", "status": "pending"},
                {"task": "Review and optimize", "status": "pending"}
            ]
        
        self.requests.append(request)
        self._save_requests()
        return request

    def get_active_requests(self) -> List[BuildRequest]:
        return [r for r in self.requests if r.status != "completed"]

    def update_request_status(self, request_id: str, status: str):
        for request in self.requests:
            if request.id == request_id:
                request.status = status
                request.updated_at = datetime.now().isoformat()
                self._save_requests()
                break

    def process_next_step(self, request_id: str) -> Optional[str]:
        request = next((r for r in self.requests if r.id == request_id), None)
        if not request:
            return None

        # Find the next pending todo
        next_todo = next((todo for todo in request.todos if todo["status"] == "pending"), None)
        if not next_todo:
            self._add_log(request_id, "All tasks completed", "info")
            request.status = "completed"
            self._save_requests()
            return "All tasks completed"

        try:
            self._add_log(request_id, f"Starting task: {next_todo['task']}")
            
            # Use debug_claude to help with implementation
            self._add_log(request_id, "Generating implementation...")
            debug_response = self.debug_claude.send_message(f"""
            Please help implement this task:
            {next_todo['task']}
            
            Context:
            - Project: {request.description}
            - Current directory: {self.workspace_dir}
            
            Provide the implementation as code blocks with file paths in this format:
            ```python [path/to/file.py]
            # Code here
            ```
            
            Include all necessary files, imports, and setup.
            """)

            # Extract and process code blocks
            code_blocks = self._parse_code_blocks(debug_response)
            
            if not code_blocks:
                self._add_log(request_id, "No code generated for task", "warning")
                return f"No code generated for task: {next_todo['task']}"
                
            # Create files and execute setup commands
            self._add_log(request_id, f"Creating {len(code_blocks)} files...")
            for file_path, code in code_blocks:
                if file_path:
                    # Create directory if needed
                    os.makedirs(os.path.dirname(os.path.join(self.workspace_dir, file_path)), exist_ok=True)
                    
                    # Write the file
                    with open(os.path.join(self.workspace_dir, file_path), 'w') as f:
                        f.write(code)
                    self._add_log(request_id, f"Created/updated file: {file_path}")

            # Update todo status
            next_todo["status"] = "completed"
            self._add_log(request_id, f"Completed task: {next_todo['task']}")
            self._save_requests()
            
            return f"Completed task: {next_todo['task']}\nCreated/updated {len(code_blocks)} files"
            
        except Exception as e:
            # Use debug_claude to analyze the error
            self._add_log(request_id, f"Error: {str(e)}", "error")
            error_analysis = self.debug_claude.send_message(f"""
            Please analyze this error and suggest a fix:
            {str(e)}
            
            Context:
            - Task: {next_todo['task']}
            - Project: {request.description}
            """)
            
            self._add_log(request_id, "Generated error analysis", "info")
            return f"Error processing task: {str(e)}\nAnalysis: {error_analysis}"

    def get_user_assistance(self, query: str) -> str:
        """Get help from the user-focused Claude instance"""
        return self.user_claude.send_message(query)

    def get_debug_assistance(self, query: str) -> str:
        """Get technical help from the debug-focused Claude instance"""
        return self.debug_claude.send_message(query) 