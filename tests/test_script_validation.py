"""Tests for script content validation in the sandbox environment."""
import os
import pytest
from pathlib import Path
import tempfile
from src.sandbox.environment import SandboxEnvironment

@pytest.fixture
def sandbox_env():
    """Create a temporary sandbox environment for testing."""
    with tempfile.TemporaryDirectory() as workspace:
        env = SandboxEnvironment(workspace_path=workspace)
        env.create_container()
        yield env
        env.cleanup()

def test_script_content_validation_ascii(sandbox_env):
    """Test validation of ASCII script content."""
    # Create a test script
    script_content = "#!/bin/bash\necho 'Hello, World!'\n"
    script_path = "test_script.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"Script content validation failed: {error}"

def test_script_content_validation_utf8(sandbox_env):
    """Test validation of UTF-8 script content with special characters."""
    # Create a test script with UTF-8 characters
    script_content = """#!/bin/bash
echo '¡Hola, mundo!'  # Spanish
echo '你好，世界！'  # Chinese
echo 'Привет, мир!'  # Russian
"""
    script_path = "test_utf8_script.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"UTF-8 script content validation failed: {error}"

def test_script_content_line_endings(sandbox_env):
    """Test handling of different line ending styles."""
    # Test content with different line endings
    unix_content = "line1\nline2\nline3"
    windows_content = "line1\r\nline2\r\nline3"
    script_path = "test_endings.txt"
    
    # Write with Unix endings
    sandbox_env.write_file(script_path, unix_content)
    
    # Should validate successfully against both Unix and Windows endings
    is_valid, error = sandbox_env.validate_script_content(script_path, unix_content)
    assert is_valid, f"Unix line ending validation failed: {error}"
    
    is_valid, error = sandbox_env.validate_script_content(script_path, windows_content)
    assert is_valid, f"Windows line ending validation failed: {error}"

def test_script_encoding_detection(sandbox_env):
    """Test script encoding detection."""
    # Test ASCII content
    ascii_content = "#!/bin/bash\necho 'Hello!'\n"
    ascii_path = "test_ascii.sh"
    sandbox_env.write_file(ascii_path, ascii_content)
    encoding, error = sandbox_env.get_script_encoding(ascii_path)
    assert encoding == "ascii", f"ASCII detection failed: {error}"
    
    # Test UTF-8 content
    utf8_content = "#!/bin/bash\necho '¡Hola!'\n"
    utf8_path = "test_utf8.sh"
    sandbox_env.write_file(utf8_path, utf8_content)
    encoding, error = sandbox_env.get_script_encoding(utf8_path)
    assert encoding == "utf-8", f"UTF-8 detection failed: {error}"

def test_content_mismatch_detection(sandbox_env):
    """Test detection of content mismatches."""
    script_path = "test_mismatch.sh"
    actual_content = "echo 'Hello'\n"
    expected_content = "echo 'World'\n"
    
    # Write actual content
    sandbox_env.write_file(script_path, actual_content)
    
    # Validate against different content
    is_valid, error = sandbox_env.validate_script_content(script_path, expected_content)
    assert not is_valid, "Validation should fail for mismatched content"
    assert "Content mismatch" in error

def test_invalid_file_handling(sandbox_env):
    """Test handling of invalid or non-existent files."""
    # Test non-existent file
    is_valid, error = sandbox_env.validate_script_content("nonexistent.sh", "content")
    assert not is_valid, "Validation should fail for non-existent file"
    assert "Failed to read script" in error
    
    # Test encoding detection for non-existent file
    encoding, error = sandbox_env.get_script_encoding("nonexistent.sh")
    assert encoding == "", "Encoding detection should fail for non-existent file"
    assert "Failed to read script" in error 

def test_multiline_script_validation(sandbox_env):
    """Test validation of multi-line scripts with complex structure."""
    # Test script with functions, loops, and conditionals
    script_content = """#!/bin/bash
# Function definition
say_hello() {
    local name=$1
    echo "Hello, $name!"
}

# Loop with conditional
for i in {1..3}; do
    if [ $i -eq 2 ]; then
        say_hello "World $i"
    else
        echo "Iteration $i"
    fi
done

# Here document
cat << EOF > output.txt
Line 1
Line 2
Line 3
EOF
"""
    script_path = "test_multiline.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"Multi-line script validation failed: {error}"

def test_multiline_indentation_handling(sandbox_env):
    """Test handling of different indentation styles."""
    # Test script with mixed indentation
    script_content = """#!/bin/bash
if true; then
    # 4 spaces
    echo "Four spaces"
	# Tab
	echo "Tab"
  # 2 spaces
  echo "Two spaces"
fi
"""
    script_path = "test_indentation.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"Indentation handling failed: {error}"

def test_multiline_comment_handling(sandbox_env):
    """Test handling of different comment styles."""
    # Test script with various comment styles
    script_content = """#!/bin/bash
# Single line comment
echo "Hello" # End of line comment

: '
Multi-line comment using :
Line 1
Line 2
'

<<COMMENT
Here document style comment
Multiple lines
COMMENT

echo "Done"
"""
    script_path = "test_comments.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"Comment handling failed: {error}"

def test_multiline_empty_lines(sandbox_env):
    """Test handling of empty lines and whitespace."""
    # Test script with various empty line patterns
    script_content = """#!/bin/bash

# Empty line above
echo "First"

    # Empty line with spaces above
echo "Second"
	
	# Empty line with tabs above
echo "Third"


# Multiple empty lines above
echo "Fourth"
"""
    script_path = "test_empty_lines.sh"
    
    # Write script to workspace
    sandbox_env.write_file(script_path, script_content)
    
    # Test exact content match
    is_valid, error = sandbox_env.validate_script_content(script_path, script_content)
    assert is_valid, f"Empty line handling failed: {error}" 

def test_shell_syntax_validation(sandbox_env):
    """Test shell script syntax validation."""
    # Test valid script
    valid_script = """#!/bin/bash
if [ "$1" = "test" ]; then
    echo "Test mode"
else
    echo "Normal mode"
fi
"""
    valid_path = "valid_script.sh"
    sandbox_env.write_file(valid_path, valid_script)
    is_valid, error = sandbox_env.validate_shell_syntax(valid_path)
    assert is_valid, f"Valid script failed syntax check: {error}"
    
    # Test script with syntax error (missing 'fi')
    invalid_script = """#!/bin/bash
if [ "$1" = "test" ]; then
    echo "Test mode"
else
    echo "Normal mode"
"""
    invalid_path = "invalid_script.sh"
    sandbox_env.write_file(invalid_path, invalid_script)
    is_valid, error = sandbox_env.validate_shell_syntax(invalid_path)
    assert not is_valid, "Invalid script passed syntax check"
    assert "syntax error" in error.lower()

def test_shell_syntax_error_reporting(sandbox_env):
    """Test detailed error reporting for shell syntax errors."""
    # Test missing closing quote
    script1 = """#!/bin/bash
echo "Hello World
"""
    path1 = "missing_quote.sh"
    sandbox_env.write_file(path1, script1)
    is_valid, error = sandbox_env.validate_shell_syntax(path1)
    assert not is_valid, "Script with missing quote passed syntax check"
    assert "quote" in error.lower()
    
    # Test unmatched parentheses
    script2 = """#!/bin/bash
function test( {
    echo "Test"
}
"""
    path2 = "unmatched_paren.sh"
    sandbox_env.write_file(path2, script2)
    is_valid, error = sandbox_env.validate_shell_syntax(path2)
    assert not is_valid, "Script with unmatched parentheses passed syntax check"
    assert "syntax error" in error.lower()
    
    # Test invalid command
    script3 = """#!/bin/bash
if; then
    echo "Invalid"
fi
"""
    path3 = "invalid_command.sh"
    sandbox_env.write_file(path3, script3)
    is_valid, error = sandbox_env.validate_shell_syntax(path3)
    assert not is_valid, "Script with invalid command passed syntax check"
    assert "syntax error" in error.lower()

def test_shell_syntax_edge_cases(sandbox_env):
    """Test edge cases in shell syntax validation."""
    # Test empty script
    script1 = ""
    path1 = "empty.sh"
    sandbox_env.write_file(path1, script1)
    is_valid, error = sandbox_env.validate_shell_syntax(path1)
    assert is_valid, f"Empty script failed syntax check: {error}"
    
    # Test script with only shebang
    script2 = "#!/bin/bash\n"
    path2 = "shebang_only.sh"
    sandbox_env.write_file(path2, script2)
    is_valid, error = sandbox_env.validate_shell_syntax(path2)
    assert is_valid, f"Shebang-only script failed syntax check: {error}"
    
    # Test script with only comments
    script3 = """#!/bin/bash
# This is a comment
# Another comment
"""
    path3 = "comments_only.sh"
    sandbox_env.write_file(path3, script3)
    is_valid, error = sandbox_env.validate_shell_syntax(path3)
    assert is_valid, f"Comments-only script failed syntax check: {error}" 

def test_permission_bit_validation(sandbox_env):
    """Test validation of file permission bits."""
    # Test executable script
    script1 = "#!/bin/bash\necho 'Hello'\n"
    path1 = "executable.sh"
    sandbox_env.write_file(path1, script1)
    sandbox_env.execute_command(f"chmod 755 {path1}")
    
    perms, error = sandbox_env.validate_file_permissions(path1)
    assert perms["user"] == "rwx", f"Incorrect user permissions: {error}"
    assert perms["group"] == "r-x", f"Incorrect group permissions: {error}"
    assert perms["other"] == "r-x", f"Incorrect other permissions: {error}"
    
    # Test read-only file
    script2 = "readonly content"
    path2 = "readonly.txt"
    sandbox_env.write_file(path2, script2)
    sandbox_env.execute_command(f"chmod 444 {path2}")
    
    perms, error = sandbox_env.validate_file_permissions(path2)
    assert perms["user"] == "r--", f"Incorrect user permissions: {error}"
    assert perms["group"] == "r--", f"Incorrect group permissions: {error}"
    assert perms["other"] == "r--", f"Incorrect other permissions: {error}"

def test_permission_inheritance(sandbox_env):
    """Test directory permission inheritance."""
    # Create directory with specific permissions
    dir_path = "test_dir"
    sandbox_env.execute_command(f"mkdir -p {dir_path}")
    sandbox_env.execute_command(f"chmod 750 {dir_path}")
    
    # Create file in directory and set permissions
    file_path = f"{dir_path}/test.sh"
    sandbox_env.write_file(file_path, "#!/bin/bash\necho 'test'\n")
    sandbox_env.execute_command(f"chmod 750 {file_path}")
    
    # Verify permissions
    perms, error = sandbox_env.validate_file_permissions(file_path)
    assert perms["user"] == "rwx", f"Incorrect user permissions: {error}"
    assert perms["group"] == "r-x", f"Incorrect group permissions: {error}"
    assert perms["other"] == "---", f"Incorrect other permissions: {error}"

def test_permission_boundaries(sandbox_env):
    """Test permission boundary cases."""
    # Test file permission bits
    script = "#!/bin/bash\necho 'test'\n"
    path = "test.sh"
    sandbox_env.write_file(path, script)
    
    # Test setting and validating different permission combinations
    test_cases = [
        ("400", {"user": "r--", "group": "---", "other": "---"}),
        ("600", {"user": "rw-", "group": "---", "other": "---"}),
        ("644", {"user": "rw-", "group": "r--", "other": "r--"}),
        ("755", {"user": "rwx", "group": "r-x", "other": "r-x"}),
        ("640", {"user": "rw-", "group": "r--", "other": "---"}),
        ("444", {"user": "r--", "group": "r--", "other": "r--"})
    ]
    
    for mode, expected in test_cases:
        sandbox_env.execute_command(f"chmod {mode} {path}")
        perms, error = sandbox_env.validate_file_permissions(path)
        for key in expected:
            assert perms[key] == expected[key], f"Mode {mode}: Incorrect {key} permissions: {error}" 

def test_workspace_cleanup(sandbox_env):
    """Test workspace cleanup after operations."""
    # Create some test files
    files = [
        ("test1.txt", "content 1"),
        ("test2.txt", "content 2"),
        ("dir1/test3.txt", "content 3"),
        ("dir2/test4.txt", "content 4")
    ]
    
    for path, content in files:
        sandbox_env.write_file(path, content)
    
    # Verify files exist
    for path, _ in files:
        full_path = os.path.join(sandbox_env.workspace_path, path)
        assert os.path.exists(full_path), f"File not created: {path}"
    
    # Cleanup
    sandbox_env.cleanup()
    
    # Verify workspace is cleaned up
    assert not os.path.exists(sandbox_env.workspace_path), "Workspace not cleaned up"

def test_workspace_isolation(sandbox_env):
    """Test workspace path isolation."""
    # Test absolute path traversal
    with pytest.raises(Exception):
        sandbox_env.write_file("/etc/passwd", "malicious content")
    
    # Test relative path traversal
    with pytest.raises(Exception):
        sandbox_env.write_file("../outside.txt", "malicious content")
    
    # Test deep path traversal
    with pytest.raises(Exception):
        sandbox_env.write_file("dir1/../../outside.txt", "malicious content")
    
    # Verify workspace is still isolated
    assert os.path.exists(sandbox_env.workspace_path), "Workspace should still exist"
    assert not os.path.exists("/etc/passwd.bak"), "Should not write outside workspace"
    assert not os.path.exists("../outside.txt"), "Should not write outside workspace"

def test_workspace_size_limits(sandbox_env):
    """Test workspace size limits."""
    # Test large file creation
    large_content = "x" * (10 * 1024 * 1024)  # 10MB
    with pytest.raises(Exception):
        sandbox_env.write_file("large.txt", large_content)
    
    # Create files up to the limit
    for i in range(sandbox_env.MAX_FILES):
        path = f"many_files/file{i}.txt"
        content = f"content {i}"
        sandbox_env.write_file(path, content)
    
    # Try to create one more file - should fail
    with pytest.raises(Exception):
        sandbox_env.write_file("many_files/one_too_many.txt", "overflow")
    
    # Delete a file to make space
    os.remove(os.path.join(sandbox_env.workspace_path, "many_files/file0.txt"))
    
    # Now we should be able to write a new file
    sandbox_env.write_file("test.txt", "test content")
    assert os.path.exists(os.path.join(sandbox_env.workspace_path, "test.txt"))
    
    # Test deep directory structure
    deep_path = "/".join([f"dir{i}" for i in range(100)])
    with pytest.raises(Exception):
        sandbox_env.write_file(f"{deep_path}/deep.txt", "too deep") 

def test_container_resource_limits(sandbox_env):
    """Test container resource limits."""
    # Test CPU limit
    cpu_hog = """#!/bin/bash
    while true; do
        echo "consuming CPU"
    done
    """
    path = "cpu_hog.sh"
    sandbox_env.write_file(path, cpu_hog)
    
    # Run with CPU limit - should be terminated
    with pytest.raises(Exception):
        result = sandbox_env.execute_command(f"bash {path}")
        assert result["exit_code"] != 0, "CPU-intensive process should be terminated"
    
    # Test memory limit
    memory_hog = """#!/bin/bash
    for i in {1..1000}; do
        data=$data$data  # Double data size each iteration
    done
    """
    path = "memory_hog.sh"
    sandbox_env.write_file(path, memory_hog)
    
    # Run with memory limit - should be terminated
    with pytest.raises(Exception):
        result = sandbox_env.execute_command(f"bash {path}")
        assert result["exit_code"] != 0, "Memory-intensive process should be terminated"
    
    # Test process limit
    fork_bomb = """#!/bin/bash
    :(){ :|:& };:
    """
    path = "fork_bomb.sh"
    sandbox_env.write_file(path, fork_bomb)
    
    # Run with process limit - should be terminated
    with pytest.raises(Exception):
        result = sandbox_env.execute_command(f"bash {path}")
        assert result["exit_code"] != 0, "Process-spawning script should be terminated" 