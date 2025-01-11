"""
Tests for ProcessManager class.
"""
import os
import pytest
from unittest.mock import Mock, patch, mock_open
from src.utils.process_manager import ProcessManager, Task

@pytest.fixture
def mock_repo():
    """Mock git.Repo for testing."""
    with patch('git.Repo') as mock:
        mock.return_value.index = Mock()
        yield mock

@pytest.fixture
def process_manager(mock_repo, tmp_path):
    """Create ProcessManager instance with mocked repo."""
    return ProcessManager(str(tmp_path))

@pytest.fixture
def sample_todo_content():
    """Sample todo.md content for testing."""
    return """
PRIORITY-1: Implement feature X
Status: In Progress
Acceptance Criteria:
  - Criterion 1
  - Criterion 2
Next Steps:
  - Step 1
  - Step 2

PRIORITY-2: Fix bug Y
Status: Not Started
Acceptance Criteria:
  - Bug is fixed
  - Tests added
Next Steps:
  - Investigate
  - Fix
  - Test
"""

def test_load_todo(process_manager, sample_todo_content):
    """Test loading tasks from todo.md."""
    with patch('builtins.open', mock_open(read_data=sample_todo_content)):
        tasks = process_manager.load_todo()
        
    assert len(tasks) == 2
    assert tasks[0].priority == 1
    assert tasks[0].description == "Implement feature X"
    assert tasks[0].status == "In Progress"
    assert len(tasks[0].acceptance_criteria) == 2
    assert len(tasks[0].next_steps) == 2

def test_select_next_task(process_manager, sample_todo_content):
    """Test selecting next task."""
    with patch('builtins.open', mock_open(read_data=sample_todo_content)):
        task = process_manager.select_next_task()
        
    assert task is not None
    assert task.priority == 1
    assert task.status == "In Progress"

def test_update_task_status(process_manager, sample_todo_content, mock_repo):
    """Test updating task status."""
    with patch('builtins.open', mock_open(read_data=sample_todo_content)) as mock_file:
        tasks = process_manager.load_todo()
        process_manager.update_task_status(tasks[0], "Completed")
        
    # Verify file was written
    mock_file().write.assert_called()
    
    # Verify commit was made
    mock_repo.return_value.index.add.assert_called_once()
    mock_repo.return_value.index.commit.assert_called_once()

def test_commit_changes(process_manager, mock_repo):
    """Test committing changes."""
    files = ["file1.py", "file2.py"]
    message = "feat: Add new feature"
    
    process_manager.commit_changes(files, message)
    
    mock_repo.return_value.index.add.assert_called_once_with(files)
    mock_repo.return_value.index.commit.assert_called_once()

def test_commit_changes_invalid_message(process_manager):
    """Test committing with invalid message format."""
    with pytest.raises(ValueError):
        process_manager.commit_changes(["file.py"], "Invalid message")

def test_verify_task_completion(process_manager, mock_repo):
    """Test task completion verification."""
    with patch('pytest.main', return_value=0):
        task = Task(1, "Test task", "In Progress", [], [])
        assert process_manager.verify_task_completion(task) is True

def test_verify_task_completion_failing_tests(process_manager, mock_repo):
    """Test task completion verification with failing tests."""
    with patch('pytest.main', return_value=1):
        task = Task(1, "Test task", "In Progress", [], [])
        assert process_manager.verify_task_completion(task) is False

def test_document_error(process_manager, sample_todo_content, mock_repo):
    """Test documenting new error."""
    with patch('builtins.open', mock_open(read_data=sample_todo_content)) as mock_file:
        process_manager.document_error("New error", "Error context")
        
    # Verify error was documented
    mock_file().write.assert_called()
    
    # Verify commit was made
    mock_repo.return_value.index.add.assert_called_once()
    mock_repo.return_value.index.commit.assert_called_once() 