import enum
from typing_extensions import Annotated
from livekit.agents import Agent, function_tool, get_job_context
import logging
from components.filewatcher import FileWatcher
from components.interview_state import InterviewStage, InterviewController

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)


class AssistantFnc(Agent):
    def __init__(self, interview_controller: InterviewController) -> None:

        super().__init__()
        self.interview_controller = interview_controller
        self.file_watcher = interview_controller.get_file_watcher()

    @function_tool()
    def get_file_snapshot(self) -> str:
        """
        Returns the latest snapshot of the file.
        """
        self.file_watcher._take_snapshot()
        return self.file_watcher.last_snapshot

    @function_tool()
    def refresh_file_snapshot(self) -> str:
        """
        Forces an update of the file snapshot by re-reading the file in case agent not
        in content with a previous possibly incomplete snapshot.
        """
        self.file_watcher._take_snapshot()
        return self.file_watcher.last_snapshot

    @function_tool()
    def get_interview_time_left(self) -> str:
        """Returns the current interview duration in HH:MM:SS format"""
        return self.interview_controller.get_interview_time_left(formatted=True)

    @function_tool()
    def get_interview_stage_duration(self, stage: Annotated[str, "The interview stage to get duration for"]) -> str:
        """Returns the duration of a specified interview stage in HH:MM:SS format. This includes completed stages (how long it took), the current stage (current timer), and future stages (0)."""
        try:
            interview_stage = InterviewStage(stage)
            return self.interview_controller.get_stage_duration(interview_stage, formatted=True)
        except ValueError:
            return "Invalid stage name"
