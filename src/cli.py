import os
import sys
import cmd
from typing import Optional
from .agent_interface import AgentInterface

class AgentCLI(cmd.Cmd):
    intro = 'Welcome to the Build Agent CLI. Type help or ? to list commands.\n'
    prompt = '(agent) '

    def __init__(self):
        super().__init__()
        self.agent = AgentInterface(os.getcwd())
        self.current_request = None

    def do_build(self, arg):
        """Create a new build request with the given description.
        Usage: build <description>"""
        if not arg:
            print("Error: Please provide a build description")
            return

        self.current_request = self.agent.create_build_request(arg)
        print("\nCreated new build request:")
        print(f"Description: {self.current_request.description}")
        print("\nGenerated todos:")
        for todo in self.current_request.todos:
            print(f"  {todo}")

    def do_list(self, arg):
        """List all active build requests."""
        requests = self.agent.get_active_requests()
        if not requests:
            print("No active build requests")
            return

        print("\nActive build requests:")
        for i, request in enumerate(requests):
            print(f"\n{i+1}. {request.description}")
            print(f"   Status: {request.status}")
            print(f"   Progress: {request.current_step}/{len(request.todos)} steps")
            print("   Current todos:")
            for j, todo in enumerate(request.todos[request.current_step:], request.current_step):
                print(f"     {todo}")

    def do_next(self, arg):
        """Process the next step of the current build request."""
        if not self.current_request:
            print("No active build request. Use 'build' to create one.")
            return

        result = self.agent.process_next_step(self.current_request)
        print(f"\n{result}")

        if self.current_request.current_step >= len(self.current_request.todos):
            print("\nBuild request completed!")
            self.agent.update_request_status(self.current_request, "completed")
            self.current_request = None

    def do_status(self, arg):
        """Show the status of the current build request."""
        if not self.current_request:
            print("No active build request")
            return

        print(f"\nCurrent build request:")
        print(f"Description: {self.current_request.description}")
        print(f"Status: {self.current_request.status}")
        print(f"Progress: {self.current_request.current_step}/{len(self.current_request.todos)} steps")
        print("\nRemaining todos:")
        for todo in self.current_request.todos[self.current_request.current_step:]:
            print(f"  {todo}")

    def do_quit(self, arg):
        """Exit the CLI."""
        print("\nGoodbye!")
        return True

    def do_EOF(self, arg):
        """Exit on EOF (Ctrl+D)."""
        print("\nGoodbye!")
        return True

def main():
    try:
        AgentCLI().cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)

if __name__ == '__main__':
    main() 