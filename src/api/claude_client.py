"""
Stub implementation of Claude client for testing.
"""

class ClaudeClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.system_prompt = None
        self.context = []

    def set_system_prompt(self, prompt: str):
        """Set the system prompt for the Claude instance."""
        self.system_prompt = prompt

    def update_context(self, context: str):
        """Update the conversation context."""
        self.context.append(context)

    def send_message(self, message: str) -> str:
        """Send a message to Claude and get a response.
        This is a stub implementation that returns predefined responses."""
        
        # Return different responses based on the type of query
        if "how" in message.lower() or "what" in message.lower():
            if "structure" in message.lower() and "api" in message.lower():
                return """
                For a FastAPI and SQLAlchemy project, I recommend the following structure:

                1. Use RESTful endpoints following standard conventions:
                   - GET /items - List all items
                   - POST /items - Create new item
                   - GET /items/{id} - Get specific item
                   - PUT /items/{id} - Update item
                   - DELETE /items/{id} - Delete item

                2. Organize your code into:
                   - routes/ - API endpoint definitions
                   - models/ - SQLAlchemy models
                   - schemas/ - Pydantic schemas
                   - services/ - Business logic
                   - dependencies/ - Shared dependencies

                3. Use dependency injection for database sessions
                4. Implement proper error handling and validation
                5. Add authentication middleware where needed
                """
            elif "implement" in message.lower():
                return """
                Here's a step-by-step implementation plan:
                1. Set up the project structure
                2. Define database models
                3. Create API routes
                4. Add validation and error handling
                5. Test the endpoints
                """
        elif "error" in message.lower():
            return """
            Based on the error message, here are potential solutions:
            1. Check your dependencies are installed correctly
            2. Verify your database connection
            3. Ensure proper error handling
            """
        else:
            return "I understand your request. Let me help you with that step by step." 