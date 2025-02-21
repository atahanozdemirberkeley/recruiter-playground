import enum
from typing import Annotated, Optional
from livekit.agents import llm
import logging
from components.filewatcher import FileWatcher

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)


class AssistantFnc(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()
        self.file_watcher = FileWatcher()

    @llm.ai_callable(
        description="Get the current code from the editor"
    )
    def get_current_code(self) -> str:
        """Returns the latest code from the editor."""
        return self.file_watcher.get_current_code()

    @llm.ai_callable(
        description="Get the code history"
    )
    def get_code_history(self, limit: Optional[int] = None) -> dict:
        """Returns the history of code changes."""
        return self.file_watcher.get_code_history(limit)

    @llm.ai_callable(
        description="Monitor code changes in real-time"
    )
    async def monitor_code_changes(self) -> str:
        """
        Monitors and returns the latest code changes from the editor.
        Also updates the agent's context with the new code.
        """
        current_code = self.file_watcher.get_current_code()
        return f"Current code state:\n```python\n{current_code}\n```"
