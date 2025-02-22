import enum
from typing import Annotated, Optional
from livekit.agents import llm
import logging
from components.filewatcher import FileWatcher
from components.interview_state import InterviewStage

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)


class AssistantFnc(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()

        self.file_watcher = FileWatcher(
            "testing/test.py")

        self.file_watcher.start_watching()
        self.interview_controller = None  # set from main.py

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
        Forces an update of the file snapshot by re-reading the file in case agent not
        in contempt with a previous possibly incomplete snapshot.
        """
        self.file_watcher._take_snapshot()
        return self.file_watcher.last_snapshot

    @llm.ai_callable(
        description="Get the current time left for the interview in HH:MM:SS format"
    )
    def get_interview_time_left(self) -> str:
        """Returns the current interview duration in HH:MM:SS format"""
        return self.interview_controller.get_interview_time_left(formatted=True)

    @llm.ai_callable(
        description="Get the duration of a specific interview stage in HH:MM:SS format"
    )
    def get_stage_duration(self, stage: Annotated[str, "The interview stage to get duration for"]) -> str:
        """Returns the duration of a specific stage in HH:MM:SS format"""
        try:
            interview_stage = InterviewStage(stage)
            return self.interview_controller.get_stage_duration(interview_stage, formatted=True)
        except ValueError:
            return "Invalid stage name"
