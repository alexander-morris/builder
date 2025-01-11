import pytest
from unittest.mock import Mock, patch, ANY
import tkinter as tk
from src.utils.chat_viewer import ChatViewer, create_chat_viewer

@pytest.fixture
def mock_tk():
    """Mock tkinter components."""
    with patch('tkinter.Tk') as mock_tk, \
         patch('tkinter.ttk.Frame') as mock_frame, \
         patch('tkinter.ttk.LabelFrame') as mock_label_frame, \
         patch('tkinter.scrolledtext.ScrolledText') as mock_text, \
         patch('tkinter.ttk.Entry') as mock_entry, \
         patch('tkinter.ttk.Button') as mock_button:
        
        # Configure mock window
        mock_window = mock_tk.return_value
        mock_window.geometry = Mock()
        mock_window.grid_rowconfigure = Mock()
        mock_window.grid_columnconfigure = Mock()
        
        # Configure mock widgets
        for mock_widget in [mock_frame, mock_label_frame, mock_text, mock_entry, mock_button]:
            mock_widget.return_value.grid = Mock()
            mock_widget.return_value.grid_rowconfigure = Mock()
            mock_widget.return_value.grid_columnconfigure = Mock()
        
        yield {
            'tk': mock_tk,
            'frame': mock_frame,
            'label_frame': mock_label_frame,
            'text': mock_text,
            'entry': mock_entry,
            'button': mock_button
        }

@pytest.fixture
def chat_viewer(mock_tk):
    """Create a ChatViewer instance with mocked components."""
    return ChatViewer()

def test_create_chat_viewer():
    """Test creating a chat viewer instance."""
    callback = Mock()
    viewer = create_chat_viewer(callback)
    assert isinstance(viewer, ChatViewer)
    assert viewer.on_prompt_submit == callback

def test_chat_viewer_initialization(mock_tk):
    """Test ChatViewer initialization."""
    viewer = ChatViewer()
    
    # Verify window setup
    mock_tk['tk'].return_value.title.assert_called_once_with("Agent Chat Viewer")
    mock_tk['tk'].return_value.geometry.assert_called_once_with("1200x800")
    
    # Verify frame creation
    assert mock_tk['frame'].call_count > 0
    assert mock_tk['label_frame'].call_count > 0
    
    # Verify text areas
    assert mock_tk['text'].call_count >= 2  # Progress and chat log
    
    # Verify entry and button
    assert mock_tk['entry'].call_count > 0
    assert mock_tk['button'].call_count > 0

def test_add_message(chat_viewer, mock_tk):
    """Test adding a message to the chat log."""
    mock_text = mock_tk['text'].return_value
    
    chat_viewer.add_message("User", "Test message")
    
    # Verify text widget was enabled, updated, and disabled
    assert mock_text.config.call_count >= 2
    assert mock_text.insert.call_count == 1
    assert mock_text.see.call_count == 1

def test_update_progress(chat_viewer, mock_tk):
    """Test updating the progress summary."""
    mock_text = mock_tk['text'].return_value
    
    chat_viewer.update_progress("Test progress")
    
    # Verify text widget was enabled, cleared, updated, and disabled
    assert mock_text.config.call_count >= 2
    assert mock_text.delete.call_count == 1
    assert mock_text.insert.call_count == 1

def test_prompt_submission(chat_viewer, mock_tk):
    """Test prompt submission handling."""
    callback = Mock()
    chat_viewer.on_prompt_submit = callback
    mock_entry = mock_tk['entry'].return_value
    mock_entry.get.return_value = "test prompt"
    
    chat_viewer._on_submit()
    
    # Verify callback was called with prompt
    callback.assert_called_once_with("test prompt")
    # Verify entry was cleared
    mock_entry.delete.assert_called_once_with(0, tk.END)

def test_task_handling(chat_viewer, mock_tk):
    """Test task button handling."""
    callback = Mock()
    chat_viewer.on_prompt_submit = callback
    
    # Test each task
    for task, desc in chat_viewer.tasks.items():
        chat_viewer._handle_task(task)
        assert callback.call_count > 0
        # Reset mock for next iteration
        callback.reset_mock()

def test_tooltip_creation(chat_viewer, mock_tk):
    """Test tooltip creation for buttons."""
    mock_button = Mock()
    mock_tooltip = Mock()
    mock_tooltip.wm_geometry = Mock()
    mock_tooltip.wm_overrideredirect = Mock()
    mock_label = Mock()
    
    with patch('tkinter.Toplevel', return_value=mock_tooltip) as mock_toplevel, \
         patch('tkinter.ttk.Label', return_value=mock_label) as mock_label_class:
        chat_viewer._create_tooltip(mock_button, "Test tooltip")
        
        # Get the bound event handlers
        enter_handler = mock_button.bind.call_args_list[0][0][1]
        
        # Create a mock event
        mock_event = Mock()
        mock_event.x_root = 100
        mock_event.y_root = 10
        
        # Trigger the tooltip creation
        enter_handler(mock_event)
        
        # Verify tooltip window creation
        mock_toplevel.assert_called_once()
        mock_tooltip.wm_overrideredirect.assert_called_once_with(True)
        mock_tooltip.wm_geometry.assert_called_once_with("+110+20")
        
        # Verify label creation
        mock_label_class.assert_called_once()
        mock_label.pack.assert_called_once()
        
        # Verify event bindings
        mock_button.bind.assert_any_call('<Enter>', ANY)
        mock_button.bind.assert_any_call('<Leave>', ANY)

def test_close_window(chat_viewer, mock_tk):
    """Test closing the chat viewer window."""
    chat_viewer.close()
    mock_tk['tk'].return_value.destroy.assert_called_once()

def test_empty_prompt_handling(chat_viewer, mock_tk):
    """Test handling of empty prompts."""
    callback = Mock()
    chat_viewer.on_prompt_submit = callback
    mock_entry = mock_tk['entry'].return_value
    mock_entry.get.return_value = "   "  # Whitespace
    
    chat_viewer._on_submit()
    
    # Verify callback was not called
    callback.assert_not_called()

def test_keyboard_shortcuts(chat_viewer, mock_tk):
    """Test keyboard shortcut bindings."""
    mock_entry = mock_tk['entry'].return_value
    
    # Verify prompt entry has Enter key binding
    assert '<Return>' in [call[0][0] for call in mock_entry.bind.call_args_list]
    
    # Verify CLI entry has Enter, Up, and Down key bindings
    cli_bindings = [call[0][0] for call in mock_entry.bind.call_args_list]
    assert '<Return>' in cli_bindings
    assert '<Up>' in cli_bindings
    assert '<Down>' in cli_bindings

def test_cli_command_execution(chat_viewer, mock_tk):
    """Test CLI command execution."""
    mock_process = Mock()
    mock_process.stdout.readline.side_effect = ["output line 1\n", ""]
    mock_process.poll.return_value = 0
    mock_process.communicate.return_value = ("", "")
    
    with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
        # Set up CLI entry
        mock_entry = mock_tk['entry'].return_value
        mock_entry.get.return_value = "test command"
        
        # Execute command
        chat_viewer._execute_command()
        
        # Verify command execution
        mock_popen.assert_called_once_with(
            "test command",
            shell=True,
            stdout=ANY,
            stderr=ANY,
            text=True
        )
        
        # Verify entry was cleared
        mock_entry.delete.assert_called_with(0, tk.END)

def test_cli_command_history(chat_viewer, mock_tk):
    """Test CLI command history navigation."""
    # Add some commands to history
    chat_viewer.command_history = ["cmd1", "cmd2", "cmd3"]
    chat_viewer.history_index = 3
    
    mock_entry = mock_tk['entry'].return_value
    
    # Test previous command
    chat_viewer._previous_command()
    mock_entry.delete.assert_called_with(0, tk.END)
    mock_entry.insert.assert_called_with(0, "cmd3")
    
    # Test next command
    chat_viewer._next_command()
    mock_entry.delete.assert_called_with(0, tk.END)

def test_cli_output_display(chat_viewer, mock_tk):
    """Test CLI output display."""
    mock_text = mock_tk['text'].return_value
    
    # Test appending output
    chat_viewer._append_cli_output("test output")
    
    # Verify text widget was enabled, updated, and disabled
    assert mock_text.config.call_count >= 2
    assert mock_text.insert.call_count == 1
    assert mock_text.see.call_count == 1

def test_cli_error_handling(chat_viewer, mock_tk):
    """Test CLI error handling."""
    mock_process = Mock()
    mock_process.stdout.readline.side_effect = Exception("Test error")
    
    with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
        # Execute command that will raise error
        chat_viewer._execute_command()
        
        # Verify error handling
        assert "Error executing command: Test error" in str(chat_viewer.output_queue.get()) 