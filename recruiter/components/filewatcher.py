import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from livekit.rtc import EventEmitter
from typing import Callable, Optional
import logging

logger = logging.getLogger("filewatcher")
logger.setLevel(logging.INFO)


class FileWatcher(EventEmitter):
    def __init__(self):
        """
        FileWatcher is a foundational agent function that allows the AI
        to access a snapshot of a file's contents. It supports:
        - Retrieving the latest file snapshot.
        - Validating whether the file snapshot appears complete.
        - Manually updating the file snapshot.
        - Maintaining a history of file snapshots.

        This tool is intended to be called by the AI agent in order to ensure
        that it is working with a complete and up-to-date version of a file (e.g.,
        a codebase file), which is critical if the file might be in mid-edit.
        """
        super().__init__()
        self.current_code = ""
        self.code_history = {}  # Dictionary to store code snapshots with timestamps
        self.max_history = 100

    def update_code(self, code: str):
        """Update the current code and store in history"""
        current_time = time.time()
        self.current_code = code
        logger.info(f"Code updated: {code[:100]}...")  # Log first 100 chars
        
        # Add to history with timestamp
        self.code_history[current_time] = {
            'content': code,
            'timestamp': current_time,
            'is_complete': True  # Since we're getting complete updates from editor
        }
        
        # Trim history if it exceeds max size
        if len(self.code_history) > self.max_history:
            oldest_key = min(self.code_history.keys())
            del self.code_history[oldest_key]
            
        # Emit an event that code has been updated
        self.emit('code_updated', code)

    def get_current_code(self) -> str:
        """Get the current code content"""
        return self.current_code
    
    def get_code_history(self, limit: Optional[int] = None) -> dict:
        """Get the history of code changes"""
        if not limit:
            return self.code_history
            
        # Get the most recent 'limit' snapshots
        sorted_times = sorted(self.code_history.keys(), reverse=True)
        recent_times = sorted_times[:limit]
        
        return {
            time: self.code_history[time]
            for time in recent_times
        }

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        pass

    def is_snapshot_complete(self, snapshot: str) -> bool:
        """
        Check if a snapshot is complete (ends with newline and not marked as WIP).

        Args:
            snapshot (str): The snapshot content to check

        Returns:
            bool: True if the snapshot is complete, False otherwise
        """
        return (snapshot and
                snapshot.endswith('\n') and
                not snapshot.endswith('[WORK IN PROGRESS] """'))
