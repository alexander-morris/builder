import os
import json
from datetime import datetime
from typing import List, Dict
from .sandbox.environment import SimpleSandbox

class BuildRequest:
    def __init__(self, description: str):
        self.description = description
        self.created_at = datetime.now()
        self.status = "pending"
        self.todos = []
        self.current_step = 0

    def to_dict(self) -> Dict:
        return {
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "todos": self.todos,
            "current_step": self.current_step
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BuildRequest':
        request = cls(data["description"])
        request.created_at = datetime.fromisoformat(data["created_at"])
        request.status = data["status"]
        request.todos = data["todos"]
        request.current_step = data["current_step"]
        return request

class AgentInterface:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.sandbox = SimpleSandbox(workspace_path)
        self.requests_file = os.path.join(workspace_path, "build_requests.json")
        self.requests: List[BuildRequest] = []
        self.load_requests()

    def load_requests(self):
        """Load existing build requests from file."""
        if os.path.exists(self.requests_file):
            with open(self.requests_file, 'r') as f:
                data = json.load(f)
                self.requests = [BuildRequest.from_dict(r) for r in data]

    def save_requests(self):
        """Save current build requests to file."""
        with open(self.requests_file, 'w') as f:
            json.dump([r.to_dict() for r in self.requests], f, indent=2)

    def create_build_request(self, description: str) -> BuildRequest:
        """Create a new build request and generate initial todos."""
        request = BuildRequest(description)
        
        # Generate initial todos based on description
        if "react" in description.lower():
            todos = [
                "1. Initialize new React project with create-react-app",
                "2. Set up project structure (components, styles, etc.)",
                "3. Install required dependencies (react-router, etc.)",
                "4. Create basic component layout",
                "5. Implement core functionality",
                "6. Add styling and polish UI",
                "7. Test all features",
                "8. Build and verify deployment"
            ]
        elif "api" in description.lower():
            todos = [
                "1. Set up basic server structure",
                "2. Define API endpoints and routes",
                "3. Implement database models",
                "4. Add authentication/authorization",
                "5. Implement API handlers",
                "6. Add input validation",
                "7. Write API tests",
                "8. Document API endpoints"
            ]
        else:
            todos = [
                f"1. Analyze requirements for: {description}",
                "2. Set up project structure",
                "3. Install dependencies",
                "4. Implement core features",
                "5. Add tests and documentation",
                "6. Review and optimize",
                "7. Prepare for deployment"
            ]
            
        request.todos = todos
        self.requests.append(request)
        self.save_requests()
        return request

    def get_active_requests(self) -> List[BuildRequest]:
        """Get all active build requests."""
        return [r for r in self.requests if r.status != "completed"]

    def update_request_status(self, request: BuildRequest, status: str):
        """Update the status of a build request."""
        request.status = status
        self.save_requests()

    def process_next_step(self, request: BuildRequest) -> str:
        """Process the next step in the build request."""
        if request.current_step >= len(request.todos):
            return "All steps completed"

        current_todo = request.todos[request.current_step]
        # Here we would actually process the todo item
        # For now, just increment the step
        request.current_step += 1
        self.save_requests()
        return f"Completed: {current_todo}" 