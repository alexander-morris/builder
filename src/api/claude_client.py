import os
import json
import aiohttp
from typing import Dict, Optional, List

class ClaudeClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.system_prompt = ""
        
    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt
        
    def update_context(self, context: dict):
        pass  # Stub for now
        
    async def send_message(self, message: str) -> dict:
        return {
            "role": "assistant",
            "content": "This is a stub response from Claude."
        } 