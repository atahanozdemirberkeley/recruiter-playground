import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from livekit.rtc import EventEmitter
from typing import Callable, Optional
import logging
import json

logger = logging.getLogger("filewatcher")
logger.setLevel(logging.INFO)


class FileWatcher(EventEmitter):
    def __init__(self, path_to_watch):
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
        self.path_to_watch = path_to_watch
        self.observer = Observer()
        self.event_handler = None
        self._last_modified = {}

        # Initialize snapshot tracking
        self.last_snapshot = ""
        self.snapshot_history = {}
        self.max_history = 100

        # Ensure the file exists
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the file if it doesn't exist and reset its contents"""
        os.makedirs(os.path.dirname(self.path_to_watch), exist_ok=True)
        with open(self.path_to_watch, 'w') as f:
            f.write('')

    def write_content(self, content: str) -> bool:
        """
        Write new content to the file.

        Args:
            content (str): The content to write to the file

        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            with open(self.path_to_watch, 'w') as f:
                f.write(content)
            self._take_snapshot()  # Update snapshot after write
            return True
        except Exception as e:
            logger.error("Error writing to file %s: %s", self.path_to_watch, e)
            return False

    def _take_snapshot(self):
        """
        Internal helper to read the file contents.
        Updates the last_snapshot attribute and stores in history with timestamp.
        Marks incomplete snapshots with [WORK IN PROGRESS] tag.
        """
        try:
            with open(self.path_to_watch, "r") as f:
                current_content = f.read()

                # TODO: Experimenting with removing WIP detection
                # # Check if snapshot appears incomplete
                # if current_content and not current_content.endswith('\n'):
                #     current_content += '\n""" [WORK IN PROGRESS] """'

                current_time = time.time()

                # Update last snapshot
                self.last_snapshot = current_content

                # Add to history with timestamp
                self.snapshot_history[current_time] = {
                    'content': current_content,
                    'timestamp': current_time,
                    'is_complete': current_content.endswith('\n') and not current_content.endswith('[WORK IN PROGRESS] """')
                }

                # Trim history if it exceeds max size
                if len(self.snapshot_history) > self.max_history:
                    oldest_key = min(self.snapshot_history.keys())
                    del self.snapshot_history[oldest_key]

        except Exception as e:
            logger.error("Error reading file %s: %s", self.path_to_watch, e)
            self.last_snapshot = ""

        return self.last_snapshot

    def get_snapshot_history(self, limit: Optional[int] = None) -> dict:
        """
        Get the history of file snapshots.

        Args:
            limit (Optional[int]): Maximum number of recent snapshots to return

        Returns:
            dict: Dictionary of timestamps and their corresponding snapshots
        """
        if not limit:
            return self.snapshot_history

        # Get the most recent 'limit' snapshots
        sorted_times = sorted(self.snapshot_history.keys(), reverse=True)
        recent_times = sorted_times[:limit]

        return {
            time: self.snapshot_history[time]
            for time in recent_times
        }

    def get_snapshot_at_time(self, timestamp: float) -> Optional[str]:
        """
        Get a specific snapshot by timestamp.

        Args:
            timestamp (float): The timestamp of the desired snapshot

        Returns:
            Optional[str]: The snapshot content if found, None otherwise
        """
        snapshot = self.snapshot_history.get(timestamp)
        return snapshot['content'] if snapshot else None

    def start_watching(self, callback: Optional[Callable] = None):
        """Start watching the specified path for changes.

        Args:
            callback (callable): Function to call when a file is saved
        """
        class CustomHandler(FileSystemEventHandler):
            def __init__(self, callback=None):
                super().__init__()
                self._callback = callback

            def on_modified(self, event):
                if not event.is_directory:
                    try:
                        if self._callback:
                            self._callback(event.src_path)
                    except Exception as e:
                        print(f"Error in file change callback: {e}")

        self.event_handler = CustomHandler(callback)
        self.observer.schedule(
            self.event_handler,
            path=os.path.dirname(self.path_to_watch) if os.path.isfile(
                self.path_to_watch) else self.path_to_watch,
            recursive=False
        )
        self.observer.start()

    def stop_watching(self):
        """Stop watching for file changes and reset the target file."""
        if self.observer:
            self.observer.stop()
            # Reset the observer and event handler
            self.event_handler = None

            # Reset the contents of the target file
            try:
                with open(self.path_to_watch, 'w') as f:
                    f.write('')
            except IOError as e:
                print(f"Error resetting file contents: {e}")

    def get_current_file(self):
        """Get the current file contents."""
        try:
            with open(self.path_to_watch, 'r') as f:
                return f.read()
        except IOError as e:
            print(f"Error reading file: {e}")
            return None

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.stop_watching()

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

    def on_data_received(self, data: bytes, topic: str):
        try:
            logger.info(f"Received data on topic: {topic}")
            decoded = json.loads(data.decode('utf-8'))
            logger.info(f"Decoded data type: {decoded.get('type')}")
            if decoded.get('type') == 'code_update':
                code = decoded.get('code', '')
                # Log first 100 chars
                logger.info(f"Attempting to write code: {code[:100]}...")
                success = self.write_content(code)
                logger.info(f"Write success: {success}")
        except Exception as e:
            logger.error(
                f"Error handling data channel message: {e}", exc_info=True)
