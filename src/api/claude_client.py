"""
Claude client implementation using Anthropic API.
"""

import os
from typing import Optional
import anthropic

class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Claude API key not provided. Set ANTHROPIC_API_KEY environment variable.")
            
        self.client = anthropic.Client(api_key=self.api_key)
        self.system_prompt = None
        self.context = []
        self.model = "claude-3-opus-20240229"

    def set_system_prompt(self, prompt: str):
        """Set the system prompt for the Claude instance."""
        self.system_prompt = prompt

    def update_context(self, context: str):
        """Update the conversation context."""
        self.context.append(context)

    def send_message(self, message: str) -> str:
        """Send a message to Claude and get a response."""
        try:
            # Construct the message with system prompt and context
            system = self.system_prompt if self.system_prompt else ""
            
            # Create the message
            response = self.client.messages.create(
                model=self.model,
                system=system,
                messages=[
                    *[{"role": "user", "content": ctx} for ctx in self.context],
                    {"role": "user", "content": message}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error communicating with Claude: {str(e)}" 