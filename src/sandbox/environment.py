import os
import base64
import resource

class SandboxEnvironment:
    # Constants for workspace limits
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_FILES = 100
    MAX_PATH_DEPTH = 10
    CPU_TIMEOUT = 5  # seconds
    MAX_MEMORY = 100 * 1024 * 1024  # 100MB
    
    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.file_count = 0
        print(f"[Mock] Initialized sandbox in {workspace_path}")
        
    def create_container(self):
        """Create and initialize the sandbox container."""
        try:
            # Create workspace directory if it doesn't exist
            if not os.path.exists(self.workspace_path):
                os.makedirs(self.workspace_path)
            self.file_count = 0
            print("[Mock] Created sandbox container")
        except Exception as e:
            print(f"[Mock] Container creation failed: {e}")
        
    def execute_command(self, command: str) -> dict:
        """Execute a command and return its result.
        
        Args:
            command: The command to execute
            
        Returns:
            Dictionary containing:
            - exit_code: The command's exit code
            - output: stdout output
            - error: stderr output
            
        Raises:
            Exception: If command execution exceeds resource limits
        """
        try:
            import subprocess
            import signal
            from threading import Timer, Event
            
            # Create process
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=self._set_process_limits  # Set resource limits
            )
            
            # Event to track if timeout occurred
            timeout_event = Event()
            timeout_error = None
            
            # Set up CPU timeout
            def kill_process():
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    timeout_event.set()
                    nonlocal timeout_error
                    timeout_error = f"Process terminated: CPU time limit ({self.CPU_TIMEOUT}s) exceeded"
                except ProcessLookupError:
                    pass  # Process already finished
                    
            timer = Timer(self.CPU_TIMEOUT, kill_process)
            timer.start()
            
            try:
                stdout, stderr = process.communicate()
                
                # Check if timeout occurred
                if timeout_event.is_set():
                    raise Exception(timeout_error)
                    
                return {
                    "exit_code": process.returncode,
                    "output": stdout,
                    "error": stderr
                }
            finally:
                timer.cancel()
                
        except Exception as e:
            if any(msg in str(e) for msg in [
                "CPU time limit",
                "Memory limit",
                "Process limit"
            ]):
                raise
            return {
                "exit_code": 1,
                "output": "",
                "error": str(e)
            }
            
    def _set_process_limits(self):
        """Set resource limits for child processes."""
        # Set memory limit
        resource.setrlimit(resource.RLIMIT_AS, (self.MAX_MEMORY, self.MAX_MEMORY))
        
        # Set up process group for cleanup
        os.setsid()
        
    def _count_files(self) -> int:
        """Count all files in the workspace.
        
        Returns:
            Total number of files in workspace
        """
        count = 0
        if os.path.exists(self.workspace_path):
            for _, _, files in os.walk(self.workspace_path):
                count += len(files)
        return count
        
    def _validate_file_count(self):
        """Validate that the workspace has not exceeded file count limits.
        
        Raises:
            Exception: If file count would exceed limit
        """
        count = 0
        if os.path.exists(self.workspace_path):
            for _, _, files in os.walk(self.workspace_path):
                count += len(files)
                if count >= self.MAX_FILES:
                    raise Exception(f"File count would exceed limit of {self.MAX_FILES} (current count: {count})")
        
    def write_file(self, path: str, content: str):
        """Write file content to the workspace.
        
        Args:
            path: Path to write to, relative to workspace
            content: Content to write
            
        Returns:
            Dict with exit_code and output/error message
            
        Raises:
            Exception: If validation fails or file count exceeds limit
        """
        try:
            # Validate path and content first
            self._validate_path(path)
            self._validate_content(content)
                
            # Get full path and check if file exists
            full_path = os.path.join(self.workspace_path, path)
            file_exists = os.path.exists(full_path)
                
            # Create directory if needed
            dir_path = os.path.dirname(full_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                
            # Check file count limit for new files
            if not file_exists:
                self._validate_file_count()
                
            # Write file
            with open(full_path, 'w') as f:
                f.write(content)
                
            return {"exit_code": 0, "output": f"Wrote file: {path}"}
                
        except Exception as e:
            # Re-raise validation and limit exceptions
            if any(msg in str(e) for msg in [
                "File count would exceed limit",
                "Path validation failed",
                "Content validation failed",
                "Content size exceeds limit"
            ]):
                raise
            return {"exit_code": 1, "error": str(e)}
        
    def cleanup(self):
        """Clean up the workspace directory."""
        try:
            import shutil
            if os.path.exists(self.workspace_path):
                shutil.rmtree(self.workspace_path)
            self.file_count = 0
            print("[Mock] Cleaned up sandbox")
        except Exception as e:
            print(f"[Mock] Cleanup failed: {e}")
        
    def validate_script_content(self, path: str, expected_content: str) -> tuple[bool, str]:
        """Validate that a script's content exactly matches the expected content.
        
        Args:
            path: Path to the script file relative to workspace
            expected_content: Expected content of the script
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Get full path
            full_path = os.path.join(self.workspace_path, path)
            
            # Check if file exists
            if not os.path.exists(full_path):
                return False, "Failed to read script: File does not exist"
                
            # Read actual content
            with open(full_path, 'rb') as f:
                actual_bytes = f.read()
                
            # Convert expected content to bytes with normalized line endings
            expected_bytes = expected_content.encode('utf-8')
            expected_bytes = expected_bytes.replace(b'\r\n', b'\n')
            
            # Normalize actual content line endings
            actual_bytes = actual_bytes.replace(b'\r\n', b'\n')
            
            # Compare normalized content
            if actual_bytes == expected_bytes:
                return True, ""
            else:
                return False, "Content mismatch: Script content does not match expected content"
                
        except Exception as e:
            return False, f"Failed to validate script content: {str(e)}"
            
    def get_script_encoding(self, path: str) -> tuple[str, str]:
        """Detect the encoding of a script file.
        
        Args:
            path: Path to the script file relative to workspace
            
        Returns:
            Tuple of (encoding, error_message)
            encoding will be 'ascii', 'utf-8', or '' if detection fails
        """
        try:
            # Get full path
            full_path = os.path.join(self.workspace_path, path)
            
            # Check if file exists
            if not os.path.exists(full_path):
                return "", "Failed to read script: File does not exist"
                
            # Try to decode as ASCII first
            with open(full_path, 'rb') as f:
                content = f.read()
                try:
                    content.decode('ascii')
                    return "ascii", ""
                except UnicodeDecodeError:
                    # Try UTF-8 if ASCII fails
                    try:
                        content.decode('utf-8')
                        return "utf-8", ""
                    except UnicodeDecodeError:
                        return "", "Failed to detect encoding: Content is neither ASCII nor UTF-8"
                        
        except Exception as e:
            return "", f"Failed to detect script encoding: {str(e)}" 
        
    def validate_shell_syntax(self, path: str) -> tuple[bool, str]:
        """Validate shell script syntax.
        
        Args:
            path: Path to the shell script relative to workspace
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Get full path
            full_path = os.path.join(self.workspace_path, path)
            
            # Check if file exists
            if not os.path.exists(full_path):
                return False, "Failed to read script: File does not exist"
                
            # Use bash -n to check syntax
            result = self.execute_command(f"bash -n {full_path}")
            
            # bash -n returns 0 for valid syntax, non-zero for invalid
            if result["exit_code"] == 0:
                return True, ""
            else:
                # Extract error message from stderr if available
                error_msg = result.get("error", "Unknown syntax error")
                return False, f"Shell syntax error: {error_msg}"
                
        except Exception as e:
            return False, f"Failed to validate shell syntax: {str(e)}" 
        
    def validate_file_permissions(self, path: str) -> tuple[dict, str]:
        """Validate file permissions.
        
        Args:
            path: Path to the file relative to workspace
            
        Returns:
            Tuple of (permissions_dict, error_message)
            permissions_dict contains:
            - user: User permission string (e.g. "rwx")
            - group: Group permission string
            - other: Other permission string
        """
        try:
            # Get full path
            full_path = os.path.join(self.workspace_path, path)
            
            # Check if file exists
            if not os.path.exists(full_path):
                return {}, "Failed to read file: File does not exist"
                
            # Get file mode
            mode = os.stat(full_path).st_mode
            
            # Convert mode to permission strings
            def mode_to_str(m):
                return ''.join([
                    'r' if m & 4 else '-',
                    'w' if m & 2 else '-',
                    'x' if m & 1 else '-'
                ])
            
            # Extract user, group, other permissions
            perms = {
                "user": mode_to_str((mode >> 6) & 7),
                "group": mode_to_str((mode >> 3) & 7),
                "other": mode_to_str(mode & 7)
            }
            
            return perms, ""
            
        except Exception as e:
            return {}, f"Failed to validate file permissions: {str(e)}" 
        
    def _validate_path(self, path: str):
        """Validate a file path for security.
        
        Args:
            path: Path to validate relative to workspace
            
        Raises:
            Exception: If path validation fails
        """
        try:
            # Get absolute paths
            full_path = os.path.abspath(os.path.join(self.workspace_path, path))
            norm_workspace = os.path.abspath(self.workspace_path)
            
            # Check for path traversal
            if not full_path.startswith(norm_workspace):
                raise Exception("Path traversal attempt detected")
                
            # Check path depth
            rel_path = os.path.relpath(full_path, norm_workspace)
            depth = len(rel_path.split(os.sep))
            if depth > self.MAX_PATH_DEPTH:
                raise Exception(f"Path depth exceeds limit of {self.MAX_PATH_DEPTH}")
                
        except Exception as e:
            raise Exception(f"Path validation failed: {str(e)}")
            
    def _validate_content(self, content: str):
        """Validate file content.
        
        Args:
            content: Content to validate
            
        Raises:
            Exception: If content validation fails
        """
        try:
            # Check content size - use len(content) for efficiency
            if len(content) > self.MAX_FILE_SIZE:
                raise Exception(f"Content size exceeds limit of {self.MAX_FILE_SIZE} bytes")
                
            # Only encode if size check passes
            try:
                content.encode('utf-8')
            except UnicodeEncodeError:
                raise Exception("Content must be valid UTF-8")
                
        except Exception as e:
            raise Exception(f"Content validation failed: {str(e)}") 