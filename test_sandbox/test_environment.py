import os
import sys
import docker
import io
import time
import base64

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SimpleSandbox:
    def __init__(self, workspace_path: str):
        self.client = docker.from_env()
        self.workspace_path = workspace_path
        self.container = None
        
    def create_container(self):
        dockerfile = """FROM node:18-alpine
RUN apk add --no-cache curl && \\
    addgroup -S sandbox_group && \\
    adduser -S -G sandbox_group sandbox_user && \\
    mkdir -p /workspace && \\
    chown -R sandbox_user:sandbox_group /workspace && \\
    npm config set prefix '/workspace/.npm-global' && \\
    mkdir -p /workspace/.npm-global && \\
    chown -R sandbox_user:sandbox_group /workspace/.npm-global

WORKDIR /workspace
USER sandbox_user

ENV NODE_ENV=development
ENV USER=sandbox_user
ENV PATH=/workspace/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV NPM_CONFIG_PREFIX=/workspace/.npm-global

CMD ["tail", "-f", "/dev/null"]"""
        
        # Build image using BytesIO
        f = io.BytesIO(dockerfile.encode('utf-8'))
        
        # Build image
        image, _ = self.client.images.build(
            fileobj=f,
            tag="sandbox-test:latest",
            rm=True
        )
        
        # Create container
        self.container = self.client.containers.run(
            image.id,
            detach=True,
            working_dir="/workspace",
            volumes={
                os.path.abspath(self.workspace_path): {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            },
            user="sandbox_user",
            environment={
                "NODE_ENV": "development",
                "USER": "sandbox_user",
                "PATH": "/workspace/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "NPM_CONFIG_PREFIX": "/workspace/.npm-global"
            },
            ports={'3000/tcp': 3000}
        )
        
    def execute_command(self, command: str):
        if not self.container:
            raise RuntimeError("Container not initialized")
            
        # Wrap complex commands with sh -c
        if '&&' in command or '>' in command or '|' in command:
            command = f'sh -c "{command}"'
            
        exit_code, output = self.container.exec_run(
            command,
            workdir="/workspace",
            user="sandbox_user",
            environment={
                "NODE_ENV": "development",
                "USER": "sandbox_user",
                "PATH": "/workspace/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "NPM_CONFIG_PREFIX": "/workspace/.npm-global"
            }
        )
        
        return {
            "exit_code": exit_code,
            "output": output.decode('utf-8')
        }
        
    def write_file(self, path: str, content: str):
        """Write file content using base64 encoding to avoid shell escaping issues."""
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        command = f'echo "{content_b64}" | base64 -d > {path}'
        return self.execute_command(command)
        
    def cleanup(self):
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
            except Exception as e:
                print(f"Error during cleanup: {e}")
            self.container = None

def test_sandbox():
    # Initialize sandbox with current directory
    sandbox = SimpleSandbox(workspace_path=os.getcwd())
    
    try:
        print("Creating sandbox container...")
        sandbox.create_container()
        
        print("\nTesting file operations...")
        
        # Create a test file with some content
        test_content = '''Hello from the sandbox!
This is a test file.
It has multiple lines.
Current time: {}'''.format(time.strftime('%Y-%m-%d %H:%M:%S'))
        
        print("Writing test file...")
        result = sandbox.write_file('test_file.txt', test_content)
        print("Write result:", result['output'])
        
        # Verify file exists
        print("\nVerifying file exists...")
        result = sandbox.execute_command('ls -l test_file.txt')
        print("File info:", result['output'])
        
        # Read file content
        print("\nReading file content...")
        result = sandbox.execute_command('cat test_file.txt')
        print("File content:", result['output'])
        
        # Verify file permissions
        print("\nVerifying file permissions...")
        result = sandbox.execute_command('stat test_file.txt')
        print("File stats:", result['output'])
        
        # Verify file ownership
        print("\nVerifying file ownership...")
        result = sandbox.execute_command('ls -n test_file.txt')
        print("File ownership:", result['output'])
        
        # Verify content with checksum
        print("\nVerifying file content with checksum...")
        content_b64 = base64.b64encode(test_content.encode('utf-8')).decode('utf-8')
        result = sandbox.execute_command(f'echo "{content_b64}" | base64 -d | md5sum')
        expected_md5 = result['output'].split()[0]
        
        result = sandbox.execute_command('md5sum test_file.txt')
        actual_md5 = result['output'].split()[0]
        
        print("Expected MD5:", expected_md5)
        print("Actual MD5:", actual_md5)
        print("Checksums match:", expected_md5 == actual_md5)
        
    finally:
        print("\nCleaning up...")
        sandbox.cleanup()

if __name__ == '__main__':
    test_sandbox() 