import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Callable, List, Optional, Dict
import datetime
import subprocess
import threading
import queue
import os

class ChatViewer:
    def __init__(self, on_prompt_submit: Optional[Callable[[str], None]] = None):
        """Initialize chat viewer window.
        
        Args:
            on_prompt_submit: Callback function that takes prompt text when submitted
        """
        self.window = tk.Tk()
        self.window.title("Agent Chat Viewer")
        self.window.geometry("1200x800")
        
        # Configure grid weights
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Create task menu
        task_frame = ttk.LabelFrame(main_frame, text="Common Tasks")
        task_frame.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(0, 10))
        
        # Define common tasks with descriptions
        self.tasks: Dict[str, str] = {
            "Show Progress": "Get latest development progress and decisions",
            "Run Tests": "Execute test suite and show results",
            "Check Todo": "View and update items from todo list",
            "Report Bug": "Report a bug or issue that needs fixing",
            "Try Product": "Test the current product functionality",
            "View Logs": "Check system and error logs",
            "Code Review": "Request review of recent changes",
            "Performance": "Run performance analysis",
            "Documentation": "View or update documentation",
            "Dependencies": "Check and update dependencies"
        }
        
        # Create task buttons
        for i, (task, desc) in enumerate(self.tasks.items()):
            btn = ttk.Button(
                task_frame,
                text=task,
                command=lambda t=task: self._handle_task(t)
            )
            btn.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            # Add tooltip
            self._create_tooltip(btn, desc)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=(0, 10))
        
        # Create chat tab
        chat_tab = ttk.Frame(self.notebook)
        self.notebook.add(chat_tab, text="Chat")
        chat_tab.grid_rowconfigure(1, weight=1)
        chat_tab.grid_columnconfigure(0, weight=1)
        
        # Create CLI tab
        cli_tab = ttk.Frame(self.notebook)
        self.notebook.add(cli_tab, text="CLI")
        cli_tab.grid_rowconfigure(1, weight=1)
        cli_tab.grid_columnconfigure(0, weight=1)
        
        # Progress summary in chat tab
        summary_frame = ttk.LabelFrame(chat_tab, text="Development Progress")
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        summary_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_text = scrolledtext.ScrolledText(
            summary_frame,
            wrap=tk.WORD,
            width=80,
            height=8,
            font=("Courier", 10)
        )
        self.progress_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.progress_text.config(state=tk.DISABLED)
        
        # Chat log area
        chat_frame = ttk.LabelFrame(chat_tab, text="Chat History")
        chat_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_log = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            width=80,
            height=25,
            font=("Courier", 10)
        )
        self.chat_log.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.chat_log.config(state=tk.DISABLED)
        
        # CLI output area
        cli_output_frame = ttk.LabelFrame(cli_tab, text="Command Output")
        cli_output_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        cli_output_frame.grid_rowconfigure(0, weight=1)
        cli_output_frame.grid_columnconfigure(0, weight=1)
        
        self.cli_output = scrolledtext.ScrolledText(
            cli_output_frame,
            wrap=tk.WORD,
            width=80,
            height=30,
            font=("Courier", 10),
            bg='black',
            fg='white'
        )
        self.cli_output.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.cli_output.config(state=tk.DISABLED)
        
        # Command history
        self.command_history: List[str] = []
        self.history_index = 0
        
        # Command input area
        cli_input_frame = ttk.Frame(cli_tab)
        cli_input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        cli_input_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(cli_input_frame, text="$").grid(row=0, column=0, padx=(5, 0))
        
        self.cli_entry = ttk.Entry(cli_input_frame)
        self.cli_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.cli_entry.bind("<Return>", self._execute_command)
        self.cli_entry.bind("<Up>", self._previous_command)
        self.cli_entry.bind("<Down>", self._next_command)
        
        # Create prompt entry area
        prompt_frame = ttk.LabelFrame(main_frame, text="Enter Prompt")
        prompt_frame.grid(row=2, column=1, sticky="ew")
        prompt_frame.grid_columnconfigure(0, weight=1)
        
        self.prompt_entry = ttk.Entry(prompt_frame)
        self.prompt_entry.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        submit_button = ttk.Button(
            prompt_frame,
            text="Submit",
            command=self._on_submit
        )
        submit_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Store callback
        self.on_prompt_submit = on_prompt_submit
        
        # Bind enter key to submit
        self.prompt_entry.bind("<Return>", lambda e: self._on_submit())
        
        # Command output queue and thread
        self.output_queue = queue.Queue()
        self.is_command_running = False
    
    def _create_tooltip(self, widget: ttk.Button, text: str) -> None:
        """Create a tooltip for a widget."""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                            background="#ffffe0", relief=tk.SOLID, borderwidth=1)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
            
        widget.bind('<Enter>', show_tooltip)
        
    def _handle_task(self, task: str) -> None:
        """Handle clicking a task button."""
        if self.on_prompt_submit:
            # Convert task to a natural language prompt
            prompts = {
                "Show Progress": "show me the latest development progress",
                "Run Tests": "run the test suite and show me the results",
                "Check Todo": "what are the current items in the todo list?",
                "Report Bug": "I'd like to report a bug",
                "Try Product": "let's test the current product functionality",
                "View Logs": "show me the recent system logs",
                "Code Review": "can you review the recent code changes?",
                "Performance": "run a performance analysis",
                "Documentation": "show me the current documentation",
                "Dependencies": "check if any dependencies need updating"
            }
            self.on_prompt_submit(prompts.get(task, task))
        
    def add_message(self, sender: str, message: str) -> None:
        """Add a message to the chat log.
        
        Args:
            sender: Name of message sender (e.g. "User" or "Agent")
            message: The message content
        """
        self.chat_log.config(state=tk.NORMAL)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.chat_log.insert(tk.END, f"[{timestamp}] {sender}: {message}\n")
        self.chat_log.see(tk.END)
        self.chat_log.config(state=tk.DISABLED)
        
    def update_progress(self, progress: str) -> None:
        """Update the progress summary.
        
        Args:
            progress: New progress summary text
        """
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.delete(1.0, tk.END)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.progress_text.insert(tk.END, f"Last Updated: {timestamp}\n\n{progress}")
        self.progress_text.config(state=tk.DISABLED)
        
    def _on_submit(self) -> None:
        """Handle prompt submission."""
        if not self.on_prompt_submit:
            return
            
        prompt = self.prompt_entry.get().strip()
        if prompt:
            self.on_prompt_submit(prompt)
            self.prompt_entry.delete(0, tk.END)
            
    def _execute_command(self, event=None) -> None:
        """Execute a command in the CLI."""
        command = self.cli_entry.get().strip()
        if not command:
            return
            
        # Add to history
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # Clear entry
        self.cli_entry.delete(0, tk.END)
        
        # Show command in output
        self._append_cli_output(f"\n$ {command}\n")
        
        # Start command in thread
        if not self.is_command_running:
            self.is_command_running = True
            threading.Thread(target=self._run_command, args=(command,), daemon=True).start()
            self.window.after(100, self._check_command_output)
    
    def _run_command(self, command: str) -> None:
        """Run a command and put output in queue."""
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Read output line by line
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.output_queue.put(line)
                    
            # Get any remaining output
            stdout, stderr = process.communicate()
            if stdout:
                self.output_queue.put(stdout)
            if stderr:
                self.output_queue.put(f"Error: {stderr}")
                
            # Signal completion
            self.output_queue.put(None)
            
        except Exception as e:
            self.output_queue.put(f"Error executing command: {str(e)}")
            self.output_queue.put(None)
    
    def _check_command_output(self) -> None:
        """Check for command output and update display."""
        try:
            while True:
                line = self.output_queue.get_nowait()
                if line is None:
                    self.is_command_running = False
                    break
                self._append_cli_output(line)
        except queue.Empty:
            if self.is_command_running:
                self.window.after(100, self._check_command_output)
    
    def _append_cli_output(self, text: str) -> None:
        """Append text to CLI output."""
        self.cli_output.config(state=tk.NORMAL)
        self.cli_output.insert(tk.END, text)
        self.cli_output.see(tk.END)
        self.cli_output.config(state=tk.DISABLED)
    
    def _previous_command(self, event=None) -> str:
        """Show previous command from history."""
        if not self.command_history:
            return "break"
            
        self.history_index = max(0, self.history_index - 1)
        if self.history_index < len(self.command_history):
            self.cli_entry.delete(0, tk.END)
            self.cli_entry.insert(0, self.command_history[self.history_index])
        return "break"
    
    def _next_command(self, event=None) -> str:
        """Show next command from history."""
        if not self.command_history:
            return "break"
            
        self.history_index = min(len(self.command_history), self.history_index + 1)
        if self.history_index < len(self.command_history):
            self.cli_entry.delete(0, tk.END)
            self.cli_entry.insert(0, self.command_history[self.history_index])
        else:
            self.cli_entry.delete(0, tk.END)
        return "break"
    
    def run(self) -> None:
        """Start the chat viewer window."""
        self.window.mainloop()
        
    def close(self) -> None:
        """Close the chat viewer window."""
        self.window.destroy()

def create_chat_viewer(callback: Optional[Callable[[str], None]] = None) -> ChatViewer:
    """Create and return a new chat viewer instance.
    
    Args:
        callback: Optional callback function for handling prompt submissions
        
    Returns:
        ChatViewer instance
    """
    return ChatViewer(callback) 