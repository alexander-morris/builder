"""
Build Agent interface for managing build requests and Claude sessions.
"""

from dataclasses import dataclass, asdict
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

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

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
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
        """)
        
        self.debug_claude.set_system_prompt("""
        You are a technical debugging assistant focused on solving code and build issues.
        Your role is to:
        1. Analyze error messages and logs
        2. Suggest specific code fixes
        3. Help troubleshoot build failures
        4. Provide technical explanations
        """)
        
        self.sandbox = SimpleSandbox(workspace_dir)
        self._load_requests()

    def _load_requests(self):
        if os.path.exists(self.requests_file):
            with open(self.requests_file, 'r') as f:
                self.requests = [BuildRequest.from_dict(r) for r in json.load(f)]
        else:
            self.requests = []

    def _save_requests(self):
        with open(self.requests_file, 'w') as f:
            json.dump([r.to_dict() for r in self.requests], f, indent=2)

    def create_build_request(self, description: str) -> BuildRequest:
        # Use user_claude to analyze the request and generate todos
        response = self.user_claude.send_message(f"""
        Please analyze this build request and break it down into specific todos:
        {description}
        
        Format the response as a list of dictionaries with 'task' and 'status' keys.
        """)
        
        # Parse the response to get todos (simplified for stub)
        todos = [
            {"task": "Initialize project", "status": "pending"},
            {"task": "Setup basic structure", "status": "pending"},
            {"task": "Implement core features", "status": "pending"},
            {"task": "Add tests", "status": "pending"},
            {"task": "Documentation", "status": "pending"}
        ]

        request = BuildRequest(
            id=f"build_{len(self.requests) + 1}",
            description=description,
            status="pending",
            todos=todos,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
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
            request.status = "completed"
            self._save_requests()
            return "All tasks completed"

        try:
            # Use debug_claude to help with implementation
            debug_response = self.debug_claude.send_message(f"""
            Please help implement this task:
            {next_todo['task']}
            
            Context:
            - Project: {request.description}
            - Current directory: {self.workspace_dir}
            """)

            # Update todo status
            next_todo["status"] = "completed"
            self._save_requests()
            
            return f"Completed task: {next_todo['task']}"
            
        except Exception as e:
            # Use debug_claude to analyze the error
            error_analysis = self.debug_claude.send_message(f"""
            Please analyze this error and suggest a fix:
            {str(e)}
            """)
            
            return f"Error processing task: {str(e)}\nAnalysis: {error_analysis}"

    def get_user_assistance(self, query: str) -> str:
        """Get help from the user-focused Claude instance"""
        return self.user_claude.send_message(query)

    def get_debug_assistance(self, query: str) -> str:
        """Get technical help from the debug-focused Claude instance"""
        return self.debug_claude.send_message(query) 