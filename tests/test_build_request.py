import pytest
from datetime import datetime
from src.agent_interface import BuildRequest

def test_build_request_initialization():
    """Test BuildRequest initialization."""
    request = BuildRequest("Test project")
    
    assert request.description == "Test project"
    assert request.status == "pending"
    assert isinstance(request.id, str)
    assert len(request.todos) == 0
    assert len(request.logs) == 1  # Initial creation log
    assert request.logs[0]["message"] == "Build request created"
    assert request.logs[0]["level"] == "info"

def test_add_todo():
    """Test adding a todo item."""
    request = BuildRequest("Test project")
    request.add_todo(
        "Test task",
        ["Should work"],
        ["test_functionality"],
        "low"
    )
    
    assert len(request.todos) == 1
    todo = request.todos[0]
    assert todo["task"] == "Test task"
    assert todo["status"] == "pending"
    assert todo["acceptance_criteria"] == ["Should work"]
    assert todo["test_cases"] == ["test_functionality"]
    assert todo["complexity"] == "low"
    assert isinstance(todo["created_at"], str)

def test_add_log():
    """Test adding a log entry."""
    request = BuildRequest("Test project")
    initial_log_count = len(request.logs)  # Should be 1
    request.add_log("Test message", "info")
    
    assert len(request.logs) == initial_log_count + 1
    assert request.logs[-1]["message"] == "Test message"
    assert request.logs[-1]["level"] == "info"

def test_to_dict():
    """Test converting BuildRequest to dictionary."""
    request = BuildRequest("Test project")
    initial_log_count = len(request.logs)  # Should be 1
    request.add_todo(
        "Test task",
        ["Should work"],
        ["test_functionality"],
        "medium"
    )
    request.add_log("Test message", "info")
    
    data = request.to_dict()
    
    assert data["description"] == "Test project"
    assert data["status"] == "pending"
    assert len(data["todos"]) == 1
    assert len(data["logs"]) == initial_log_count + 1
    assert data["logs"][-1]["message"] == "Test message"
    assert data["logs"][-1]["level"] == "info"

def test_from_dict():
    """Test creating BuildRequest from dictionary."""
    data = {
        "id": "test-id",
        "description": "Test project",
        "status": "pending",
        "todos": [{
            "task": "Test task",
            "status": "pending",
            "acceptance_criteria": ["Should work"],
            "test_cases": ["test_functionality"],
            "complexity": "medium",
            "created_at": datetime.now().isoformat()
        }],
        "logs": [{
            "message": "Test message",
            "level": "info",
            "timestamp": datetime.now().isoformat()
        }],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    request = BuildRequest.from_dict(data)
    
    assert request.id == "test-id"
    assert request.description == "Test project"
    assert request.status == "pending"
    assert len(request.todos) == 1
    assert len(request.logs) == 1

def test_updated_at_changes():
    """Test that updated_at changes when modifications are made."""
    request = BuildRequest("Test project")
    initial_updated_at = request.updated_at
    
    # Wait a moment to ensure timestamp changes
    import time
    time.sleep(0.001)
    
    request.add_todo(
        "Test task",
        ["Should work"],
        ["test_functionality"],
        "medium"
    )
    assert request.updated_at != initial_updated_at
    
    time.sleep(0.001)
    request.add_log("Test message", "info")
    assert request.updated_at != initial_updated_at

def test_default_complexity():
    """Test default complexity when adding a todo."""
    request = BuildRequest("Test project")
    request.add_todo(
        "Test task",
        ["Should work"],
        ["test_functionality"]
    )
    
    assert request.todos[0]["complexity"] == "medium"

def test_invalid_data_from_dict():
    """Test handling invalid data in from_dict."""
    invalid_data = {
        "description": "Test project",
        "status": "pending",
        "todos": [],
        "logs": []
    }
    
    with pytest.raises(KeyError):
        BuildRequest.from_dict(invalid_data)  # Missing required fields 