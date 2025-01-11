"""
Command-line interface for the Build Agent.
"""

import cmd
import os
from typing import Optional

from src.agent_interface import AgentInterface

class AgentCLI(cmd.Cmd):
    intro = 'Welcome to the Build Agent CLI. Type help or ? to list commands.\n'
    prompt = '(agent) '

    def __init__(self):
        super().__init__()
        self.agent = AgentInterface(os.getcwd())
        self.current_request_id: Optional[str] = None

    def do_build(self, arg):
        """Create a new build request with the given description.
        Usage: build <description>"""
        if not arg:
            print("Error: Please provide a description of what you want to build")
            return

        request = self.agent.create_build_request(arg)
        self.current_request_id = request.id
        print(f"\nCreated build request {request.id}")
        print("\nGenerated todos:")
        for todo in request.todos:
            print(f"- {todo['task']} ({todo['status']})")

    def do_list(self, arg):
        """List all active build requests.
        Usage: list"""
        requests = self.agent.get_active_requests()
        if not requests:
            print("No active build requests")
            return

        for request in requests:
            print(f"\nRequest {request.id}:")
            print(f"Description: {request.description}")
            print(f"Status: {request.status}")
            print("Todos:")
            for todo in request.todos:
                print(f"- {todo['task']} ({todo['status']})")

    def do_next(self, arg):
        """Process the next step of the current build request.
        Usage: next"""
        if not self.current_request_id:
            print("No active build request. Use 'build' to create one first.")
            return

        result = self.agent.process_next_step(self.current_request_id)
        if result:
            print(result)
        else:
            print("Error: Could not process next step")

    def do_status(self, arg):
        """Show the status of the current build request.
        Usage: status"""
        if not self.current_request_id:
            print("No active build request. Use 'build' to create one first.")
            return

        request = next((r for r in self.agent.get_active_requests() 
                       if r.id == self.current_request_id), None)
        if request:
            print(f"\nCurrent build request {request.id}:")
            print(f"Description: {request.description}")
            print(f"Status: {request.status}")
            print("\nTodos:")
            for todo in request.todos:
                print(f"- {todo['task']} ({todo['status']})")
        else:
            print("Current build request not found")

    def do_ask(self, arg):
        """Ask a question about the build process or get help with requirements.
        Usage: ask <question>"""
        if not arg:
            print("Error: Please provide a question")
            return
        
        response = self.agent.get_user_assistance(arg)
        print(f"\nAssistant: {response}")

    def do_debug(self, arg):
        """Get technical help or debugging assistance.
        Usage: debug <question>"""
        if not arg:
            print("Error: Please provide a technical question or issue")
            return
        
        response = self.agent.get_debug_assistance(arg)
        print(f"\nTechnical Assistant: {response}")

    def do_quit(self, arg):
        """Exit the CLI.
        Usage: quit"""
        print("Goodbye!")
        return True

    def do_EOF(self, arg):
        """Exit on EOF (Ctrl+D)"""
        print("Goodbye!")
        return True

def main():
    AgentCLI().cmdloop() 