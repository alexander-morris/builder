import os
import pytest
import tempfile
from pathlib import Path
from src.utils.log_watcher import LogWatcher, LogError

@pytest.fixture
def temp_log_file():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def log_watcher():
    return LogWatcher(max_context_lines=3)

def test_watch_log_basic_error_detection(temp_log_file, log_watcher):
    # Write test log content
    with open(temp_log_file, 'w') as f:
        f.write("Info: Starting process\n")
        f.write("Debug: Step 1 complete\n")
        f.write("Error: Something went wrong\n")
        f.write("Info: Continuing anyway\n")
    
    error_patterns = [r"Error:.*"]
    errors = list(log_watcher.watch_log(temp_log_file, error_patterns))
    
    assert len(errors) == 1
    assert errors[0].message == "Error: Something went wrong"
    assert errors[0].level == "ERROR"
    assert len(errors[0].context) == 3  # Should have 3 lines of context
    assert errors[0].line_number == 3

def test_watch_log_context_buffer(temp_log_file, log_watcher):
    # Test that context buffer maintains correct size and order
    with open(temp_log_file, 'w') as f:
        f.write("Line 1\n")
        f.write("Line 2\n")
        f.write("Line 3\n")
        f.write("Line 4\n")
        f.write("Error line\n")
    
    error_patterns = [r"Error.*"]
    error = next(log_watcher.watch_log(temp_log_file, error_patterns))
    
    # Buffer should contain the 3 lines before the error
    assert error.context["context_line_1"] == "Line 3"
    assert error.context["context_line_2"] == "Line 4"
    assert error.context["context_line_3"] == "Error line"

def test_watch_log_multiple_patterns(temp_log_file, log_watcher):
    # Test multiple error patterns
    with open(temp_log_file, 'w') as f:
        f.write("Info: Normal operation\n")
        f.write("Warning: Disk space low\n")
        f.write("Critical: Service stopped\n")
    
    error_patterns = [r"Warning:.*", r"Critical:.*", r"Error:.*"]
    error = next(log_watcher.watch_log(temp_log_file, error_patterns))
    
    assert error.message == "Warning: Disk space low"
    assert error.line_number == 2

def test_watch_log_no_errors(temp_log_file, log_watcher):
    # Test handling when no errors are found
    with open(temp_log_file, 'w') as f:
        f.write("Info: Normal operation\n")
        f.write("Debug: All good\n")
    
    error_patterns = [r"Error:.*"]
    errors = list(log_watcher.watch_log(temp_log_file, error_patterns))
    
    assert len(errors) == 0

def test_watch_log_common_error_keywords(temp_log_file, log_watcher):
    # Test detection of common error keywords
    with open(temp_log_file, 'w') as f:
        f.write("Starting process\n")
        f.write("Process failed to start\n")
        f.write("Continuing execution\n")
    
    error_patterns = []  # No explicit patterns, should catch "failed"
    error = next(log_watcher.watch_log(temp_log_file, error_patterns))
    
    assert error.message == "Process failed to start"
    assert error.level == "WARNING" 