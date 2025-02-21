import enum
from typing import Annotated
from livekit.agents import llm
import logging
from components.filewatcher import FileWatcher
from recruiter.components.interview_state import InterviewStage

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)


class AssistantFnc(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()

        self.file_watcher = FileWatcher(
            "/testing/test_files/test.py")

        self.file_watcher.start_watching()
        self.interview_controller = None  # set from main.py

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

    @llm.ai_callable(
        description="Get the current time left for the interview in HH:MM format"
    )
    def get_interview_duration(self) -> str:
        """Returns the current interview duration in HH:MM format"""
        return self.interview_controller.get_interview_duration(formatted=True)

    @llm.ai_callable(
        description="Get the duration of a specific interview stage in HH:MM format"
    )
    def get_stage_duration(self, stage: Annotated[str, "The interview stage to get duration for"]) -> str:
        """Returns the duration of a specific stage in HH:MM:SS format"""
        try:
            interview_stage = InterviewStage(stage)
            return self.interview_controller.get_stage_duration(interview_stage, formatted=True)
        except ValueError:
            return "Invalid stage name"
