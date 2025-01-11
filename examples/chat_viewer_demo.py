import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.chat_viewer import create_chat_viewer

def handle_prompt(prompt: str) -> None:
    """Handle submitted prompts."""
    # Echo the prompt back
    viewer.add_message("User", prompt)
    viewer.add_message("Agent", "Please use the CLI tab to execute commands directly.")

if __name__ == "__main__":
    # Create chat viewer with prompt handler
    viewer = create_chat_viewer(handle_prompt)
    
    # Set initial progress
    initial_progress = """CLI Verification Tasks:
1. Create and run Rust program:
   $ echo 'fn main() { println!("Hello, world!"); }' > hello.rs
   $ rustc hello.rs
   $ ./hello

2. List and describe files:
   $ ls -la
   $ cat README.md | head -n 5

3. Create and verify new directory:
   $ mkdir -p test_workspace
   $ ls -ld test_workspace

Use the CLI tab to execute these commands."""
    
    viewer.update_progress(initial_progress)
    
    # Add initial messages
    viewer.add_message("System", "CLI verification session started")
    viewer.add_message("Agent", "Please switch to the CLI tab to execute commands.")
    viewer.add_message("Agent", "The progress summary shows the commands to verify.")
    
    # Start the viewer
    viewer.run() 