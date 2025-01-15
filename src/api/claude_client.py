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
            
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.system_prompt = None
        self.context = []
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")

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
            prompt = ""
            if self.system_prompt:
                prompt += f"\n\nSystem: {self.system_prompt}\n\n"
            
            for ctx in self.context:
                prompt += f"Human: {ctx}\n\nAssistant: I understand.\n\n"
                
            prompt += f"Human: {message}\n\nAssistant:"
            
            # Create the completion
            response = self.client.completions.create(
                prompt=prompt,
                model=self.model,
                max_tokens_to_sample=2000,
                temperature=0.7,
                stop_sequences=["\n\nHuman:"]
            )
            
            return response.completion
            
        except Exception as e:
            return {"role": "error", "content": f"Error communicating with Claude: {str(e)}"}