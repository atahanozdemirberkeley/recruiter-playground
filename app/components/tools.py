
from typing_extensions import Annotated
from livekit.agents import Agent, function_tool, get_job_context  
from components.filewatcher import FileWatcher
from components.interview_state import InterviewStage, InterviewController
from utils.shared_state import get_interview_controller

@function_tool()
def get_file_snapshot() -> str:
    """
    Returns the latest snapshot of the code file.
    """
    interview_controller = get_interview_controller()
    interview_controller.file_watcher._take_snapshot()
    return interview_controller.file_watcher.last_snapshot


@function_tool()
def get_interview_time_left() -> str:
    """Returns the current interview duration in HH:MM:SS format"""
    interview_controller = get_interview_controller()
    return interview_controller.get_interview_time_left(formatted=True)
