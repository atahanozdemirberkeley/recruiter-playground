import enum
from typing import Annotated
from livekit.agents import llm
import logging
from components.filewatcher import FileWatcher

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)


class AssistantFnc(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()

        self.file_watcher = FileWatcher(
            "/testing/test_files/test.py")

        self.file_watcher.start_watching()

    @llm.ai_callable(
        description="Get the current snapshot of the test file. This returns the file's contents as a string."
    )
    def get_file_snapshot(self) -> str:
        """
        Returns the latest snapshot of the file.
        It refreshes the snapshot before returning it.
        """
        self.file_watcher._take_snapshot()
        return self.file_watcher.last_snapshot

    @llm.ai_callable(
        description="Force an update of the file snapshot."
    )
    def update_file_snapshot(self) -> str:
        """
        Forces an update of the file snapshot by re-reading the file in case agent not 
        in contempt with a previous possibly incomplete snapshot.
        """
        self.file_watcher._take_snapshot()
        return self.file_watcher.last_snapshot
