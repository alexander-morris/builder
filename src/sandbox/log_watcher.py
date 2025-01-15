"""Log watching functionality for the sandbox environment."""
import os
import re
import asyncio
import aiofiles
from typing import List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class LogWatcher:
    """Watches a log file for specific patterns."""

    def __init__(self, 
                 file_path: str,
                 error_patterns: List[str],
                 warning_patterns: Optional[List[str]] = None,
                 ignore_patterns: Optional[List[str]] = None,
                 context_lines: int = 5):
        """Initialize log watcher.
        
        Args:
            file_path: Path to log file to watch
            error_patterns: List of regex patterns that indicate errors
            warning_patterns: Optional list of regex patterns for warnings
            ignore_patterns: Optional list of patterns to ignore
            context_lines: Number of lines of context to keep around matches
        """
        self.file_path = file_path
        self.error_patterns = [re.compile(pattern) for pattern in error_patterns]
        self.warning_patterns = [re.compile(pattern) for pattern in (warning_patterns or [])]
        self.ignore_patterns = [re.compile(pattern) for pattern in (ignore_patterns or [])]
        self.context_lines = context_lines
        
        self._current_position = 0
        self._current_inode = None
        self._context_buffer = []
        self.error_context = []
        self.warning_context = []
        self._error_found = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._watch_task = None
        self._loop = None
        
    async def start(self):
        """Start watching the log file."""
        try:
            self._loop = asyncio.get_running_loop()
            self._watch_task = self._loop.create_task(self._watch_file())
        except RuntimeError:
            logging.error("Error watching log file: no running event loop")
            return
            
    async def stop(self):
        """Stop watching the log file."""
        if self._stop_event:
            self._stop_event.set()
        if self._watch_task:
            try:
                self._watch_task.cancel()
                await asyncio.shield(self._watch_task)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logging.error(f"Error stopping log watcher: {e}")
            
    async def wait_for_error(self, timeout: Optional[float] = None) -> bool:
        """Wait for an error to be detected within the specified timeout."""
        try:
            await asyncio.wait_for(self._error_found.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
            
    async def _watch_file(self):
        """Watch the file for changes and process new lines."""
        while not self._stop_event.is_set():
            try:
                # Wait for file to exist
                while not os.path.exists(self.file_path):
                    if self._stop_event.is_set():
                        return
                    await asyncio.sleep(0.1)
                    continue

                # Get current inode
                current_inode = os.stat(self.file_path).st_ino
                if self._current_inode is None:
                    self._current_inode = current_inode
                elif self._current_inode != current_inode:
                    # File has been rotated
                    self._current_position = 0
                    self._current_inode = current_inode

                async with aiofiles.open(self.file_path, 'r') as f:
                    await f.seek(self._current_position)
                    while not self._stop_event.is_set():
                        line = await f.readline()
                        if not line:
                            # Check if file was rotated
                            try:
                                if not os.path.exists(self.file_path):
                                    break
                                stat = os.stat(self.file_path)
                                if stat.st_ino != self._current_inode:
                                    break
                            except FileNotFoundError:
                                break
                            await asyncio.sleep(0.1)
                            continue

                        self._current_position = await f.tell()
                        await self._process_line(line.strip())

            except FileNotFoundError:
                await asyncio.sleep(0.1)
                continue
            except Exception as e:
                logging.error(f"Error watching log file: {e}")
                await asyncio.sleep(0.1)
            
    async def _process_line(self, line: str):
        """Process a single line from the log file."""
        # Check if line should be ignored first
        for pattern in self.ignore_patterns:
            if pattern.search(line):
                return

        # Add line to context buffer
        self._context_buffer.append(line)
        if len(self._context_buffer) > self.context_lines:
            self._context_buffer.pop(0)

        # Check for errors
        for pattern in self.error_patterns:
            if pattern.search(line):
                self.error_context.extend(self._context_buffer)
                self._error_found.set()
                return

        # Check for warnings
        for pattern in self.warning_patterns:
            if pattern.search(line):
                self.warning_context.extend(self._context_buffer)
                logging.warning(f"Warning detected in log: {line}")
                return 