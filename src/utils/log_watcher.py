import os
from typing import Optional, Dict, List, Generator
from dataclasses import dataclass
from .logging import setup_logger

logger = setup_logger(__name__)

@dataclass
class LogError:
    message: str
    level: str
    context: Dict[str, str]
    line_number: int

class LogWatcher:
    def __init__(self, max_context_lines: int = 5):
        self.max_context_lines = max_context_lines
        self.context_buffer: List[str] = []
        
    def _maintain_context_buffer(self, line: str) -> None:
        """Maintain a rolling buffer of the last N lines for context."""
        self.context_buffer.append(line)
        if len(self.context_buffer) > self.max_context_lines:
            self.context_buffer.pop(0)
            
    def _extract_error_context(self) -> Dict[str, str]:
        """Extract relevant context from the buffer."""
        return {
            f"context_line_{i+1}": line 
            for i, line in enumerate(self.context_buffer)
        }

    def watch_log(self, log_file: str, error_patterns: List[str]) -> Generator[LogError, None, None]:
        """
        Watch a log file and yield the first error found along with its context.
        
        Args:
            log_file: Path to the log file to watch
            error_patterns: List of regex patterns that indicate errors
            
        Yields:
            LogError object containing error details and context
        """
        import re
        
        # Compile error patterns for efficiency
        compiled_patterns = [re.compile(pattern) for pattern in error_patterns]
        
        try:
            with open(log_file, 'r') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    self._maintain_context_buffer(line)
                    
                    # Check for errors
                    for pattern in compiled_patterns:
                        if pattern.search(line):
                            error = LogError(
                                message=line,
                                level="ERROR",
                                context=self._extract_error_context(),
                                line_number=line_number
                            )
                            yield error
                            return  # Stop after first error
                            
                    # Optional: Check if line contains common error indicators
                    lower_line = line.lower()
                    if any(indicator in lower_line for indicator in 
                          ['error', 'exception', 'failed', 'crash']):
                        error = LogError(
                            message=line,
                            level="WARNING",
                            context=self._extract_error_context(),
                            line_number=line_number
                        )
                        yield error
                        return  # Stop after first error
                        
        except Exception as e:
            logger.error(f"Error watching log file: {e}")
            error = LogError(
                message=str(e),
                level="ERROR",
                context={"error": "Failed to read log file"},
                line_number=-1
            )
            yield error

    def tail_and_watch(self, log_file: str, error_patterns: List[str]) -> Generator[LogError, None, None]:
        """
        Tail a log file and watch for new errors in real-time.
        
        Args:
            log_file: Path to the log file to watch
            error_patterns: List of regex patterns that indicate errors
            
        Yields:
            LogError object containing error details and context
        """
        import time
        
        file_size = os.path.getsize(log_file) if os.path.exists(log_file) else 0
        
        while True:
            if os.path.exists(log_file):
                current_size = os.path.getsize(log_file)
                if current_size > file_size:
                    # New content added
                    with open(log_file, 'r') as f:
                        f.seek(file_size)
                        new_content = f.read()
                        file_size = current_size
                        
                        for error in self.watch_log(log_file, error_patterns):
                            yield error
                            return  # Stop after first error
                            
            time.sleep(0.1)  # Prevent CPU overuse 