# LogWatcher Usage Guide

The `LogWatcher` class provides efficient log monitoring with early error detection and context preservation. This guide demonstrates common usage patterns and best practices.

## Basic Usage

```python
from src.utils.log_watcher import LogWatcher

# Initialize with context buffer size
watcher = LogWatcher(max_context_lines=5)

# Watch a log file with specific error patterns
error_patterns = [
    r"Error:",
    r"Exception occurred:",
    r"Failed to"
]

for error in watcher.watch_log("app.log", error_patterns):
    print(f"Error found at line {error.line_number}: {error.message}")
    print("Context:")
    for line_num, line in error.context.items():
        print(f"  {line_num}: {line}")
    break  # Stop at first error
```

## Real-time Log Tailing

```python
# Watch a log file in real-time
watcher = LogWatcher()
for error in watcher.tail_and_watch("app.log", error_patterns):
    print(f"Error detected: {error.message}")
    print(f"Previous context: {error.context}")
    break  # Stop at first error
```

## Integration with Sandbox Environment

```python
from src.sandbox.environment import SandboxEnvironment

sandbox = SandboxEnvironment("/path/to/workspace")

# Execute command with log watching
result = sandbox.execute_command_with_log_watch(
    "long_running_script.sh",
    error_patterns=[
        r"Error:",
        r"Failed:",
        r"Exception:"
    ]
)

if result["exit_code"] != 0:
    print(f"Error found: {result['output']}")
    print(f"Context: {result['error_context']}")
```

## Best Practices

1. **Error Pattern Design**
   - Use specific patterns to catch known errors
   - Include common error indicators (error, exception, failed)
   - Consider case sensitivity in patterns

2. **Memory Efficiency**
   - The watcher processes files line by line
   - Context buffer size affects memory usage
   - Use appropriate buffer size for your needs

3. **Early Error Detection**
   - Watcher stops at first error by default
   - Helps prevent unnecessary processing
   - Returns context around the error

4. **Context Management**
   - Default context is 5 lines
   - Adjust based on log verbosity
   - Context includes lines before error

## Error Handling

```python
try:
    for error in watcher.watch_log("app.log", error_patterns):
        if error.level == "ERROR":
            # Critical error found
            raise Exception(f"Critical error: {error.message}")
        elif error.level == "WARNING":
            # Warning found, log it
            print(f"Warning: {error.message}")
except Exception as e:
    print(f"Error watching logs: {e}")
``` 