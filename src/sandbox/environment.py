import os
import io
import docker
from pathlib import Path
from typing import Optional, Dict, Tuple, List
import hashlib
import codecs
import shlex
import base64

from ..utils.logging import setup_logger

logger = setup_logger(__name__)

class SandboxEnvironment:
    def __init__(
        self,
        workspace_path: str,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0
    ):
        logger.info(f"Initializing sandbox environment with workspace: {workspace_path}")
        self.client = docker.from_env()
        self.workspace_path = Path(workspace_path)
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.container: Optional[docker.models.containers.Container] = None
        
    def _build_sandbox_image(self) -> str:
        """Build a custom Docker image for the sandbox."""
        logger.debug("Building sandbox Docker image")
        dockerfile = """FROM busybox:latest

# Add sandbox user and group
RUN addgroup -g 1000 sandbox_group && \\
    adduser -D -u 1000 -G sandbox_group -h /home/sandbox_user -s /bin/sh sandbox_user

# Create and configure workspace directory
RUN mkdir -p /workspace && \\
    chown -R sandbox_user:sandbox_group /workspace && \\
    chmod 755 /workspace

# Switch to sandbox user
USER sandbox_user
WORKDIR /workspace

# Default command
CMD ["tail", "-f", "/dev/null"]"""
        
        # Build the image
        logger.debug("Starting Docker build process")
        image, logs = self.client.images.build(
            fileobj=io.BytesIO(dockerfile.encode('utf-8')),
            tag="sandbox:latest",
            rm=True
        )
        
        # Log build output
        for log in logs:
            if 'stream' in log:
                logger.debug(f"Build: {log['stream'].strip()}")
                
        logger.info(f"Successfully built sandbox image: {image.id}")
        return image.id
        
    def create_container(self) -> None:
        """Create a new sandboxed container with restricted permissions."""
        # Build custom image with sandbox user
        image_id = self._build_sandbox_image()
        
        logger.debug("Creating container with configuration:")
        container_config = {
            "image": image_id,
            "detach": True,
            "working_dir": "/workspace",
            "volumes": {
                str(self.workspace_path.absolute()): {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            },
            "mem_limit": self.memory_limit,
            "cpu_quota": int(100000 * self.cpu_limit),
            "cpu_period": 100000,
            "security_opt": ["no-new-privileges"],
            "cap_drop": ["ALL"],
            "network_mode": "none",
            "user": "1000:1000",
            "hostname": "sandbox",
            "ipc_mode": "private",
            "privileged": False,
            "publish_all_ports": False,
            "init": True
        }
        
        logger.debug(f"Container configuration: {container_config}")
        
        logger.info("Starting container")
        self.container = self.client.containers.run(**container_config)
        
        # Wait for container to be fully running
        logger.debug("Waiting for container to be ready")
        self.container.reload()
        
        if self.container.status != "running":
            error_msg = f"Container failed to start. Status: {self.container.status}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        logger.info(f"Container {self.container.id} is running")
        
    def execute_command(self, command: str) -> Dict[str, str]:
        """Execute a command in the sandbox and return the result."""
        if not self.container:
            error_msg = "Container not initialized"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        logger.debug(f"Executing command in sandbox: {command}")
        exit_code, output = self.container.exec_run(
            command,
            workdir="/workspace",
            user="1000:1000",  # Use numeric UID:GID instead of username
            environment={
                "PATH": "/bin:/usr/bin",
                "HOME": "/home/sandbox_user"
            }
        )
        
        output_str = output.decode('utf-8')
        logger.debug(f"Command exit code: {exit_code}")
        logger.debug(f"Command output: {output_str}")
        
        return {
            "exit_code": exit_code,
            "output": output_str
        }
        
    def cleanup(self) -> None:
        """Stop and remove the container."""
        if self.container:
            logger.info(f"Cleaning up container {self.container.id}")
            try:
                self.container.stop()
                self.container.remove()
                logger.debug("Container stopped and removed")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            self.container = None 
        
    def write_file(self, file_path: str, content: str) -> Dict[str, str]:
        """Write content to a file in the sandbox."""
        if not self.container:
            raise RuntimeError("Container not initialized")
            
        # Encode content in base64 to avoid shell escaping issues
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        # Create a shell script to handle the file writing
        script = f"""#!/bin/sh
echo '{content_b64}' > temp.b64
base64 -d temp.b64 > {file_path}
rm temp.b64
"""
        # Write the script to a temporary file
        script_b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
        command = f"echo '{script_b64}' | base64 -d > write_file.sh && chmod +x write_file.sh && ./write_file.sh && rm write_file.sh"
        return self.execute_command(command)
        
    def validate_script_content(self, script_path: str, expected_content: str) -> Tuple[bool, str]:
        """
        Validate script content byte-by-byte with exact matching.
        
        Args:
            script_path: Path to the script file relative to workspace
            expected_content: Expected content of the script
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.container:
            return False, "Container not initialized"
            
        try:
            # Get actual content from container
            result = self.execute_command(f"cat {script_path}")
            if result["exit_code"] != 0:
                return False, f"Failed to read script: {result['output']}"
                
            actual_content = result["output"]
            
            # Normalize line endings
            expected_normalized = expected_content.replace('\r\n', '\n')
            actual_normalized = actual_content.replace('\r\n', '\n')
            
            # Check for exact content match
            if expected_normalized != actual_normalized:
                return False, "Content mismatch"
                
            # Verify character encoding
            try:
                expected_bytes = expected_normalized.encode('utf-8')
                actual_bytes = actual_normalized.encode('utf-8')
                
                # Compare content hashes for byte-level verification
                expected_hash = hashlib.sha256(expected_bytes).hexdigest()
                actual_hash = hashlib.sha256(actual_bytes).hexdigest()
                
                if expected_hash != actual_hash:
                    return False, "Byte-level content mismatch"
                    
            except UnicodeEncodeError:
                return False, "Invalid character encoding"
                
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating script content: {e}")
            return False, str(e)
            
    def get_script_encoding(self, script_path: str) -> Tuple[str, str]:
        """
        Detect the character encoding of a script file.
        
        Args:
            script_path: Path to the script file relative to workspace
            
        Returns:
            Tuple of (encoding, error_message)
        """
        if not self.container:
            return "", "Container not initialized"
            
        try:
            result = self.execute_command(f"cat {script_path}")
            if result["exit_code"] != 0:
                return "", f"Failed to read script: {result['output']}"
                
            # Try to detect encoding
            try:
                content = result["output"]
                content.encode('ascii')
                return "ascii", ""
            except UnicodeEncodeError:
                try:
                    content.encode('utf-8')
                    return "utf-8", ""
                except UnicodeEncodeError:
                    return "", "Unknown or invalid encoding"
                    
        except Exception as e:
            logger.error(f"Error detecting script encoding: {e}")
            return "", str(e) 
        
    def execute_command_with_log_watch(self, command: str, error_patterns: List[str]) -> Dict[str, str]:
        """Execute a command and watch its output for errors, stopping at first error."""
        from ..utils.log_watcher import LogWatcher
        import tempfile
        
        # Create temporary file for command output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_log:
            try:
                # Execute command and redirect output to temp file
                modified_command = f"{command} 2>&1 | tee {temp_log.name}"
                result = self.execute_command(modified_command)
                
                # Watch the log file for errors
                watcher = LogWatcher(max_context_lines=5)
                for error in watcher.watch_log(temp_log.name, error_patterns):
                    return {
                        "exit_code": 1,
                        "output": error.message,
                        "error_context": error.context,
                        "error_line": error.line_number
                    }
                
                # If no errors found, return original result
                return result
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_log.name)
                except Exception as e:
                    logger.error(f"Error cleaning up temp log file: {e}") 