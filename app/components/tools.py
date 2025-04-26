
from typing_extensions import Annotated
from livekit.agents import Agent, function_tool
from utils.shared_state import get_interview_controller
import logging

logger = logging.getLogger(__name__)


@function_tool()
async def get_file_snapshot() -> str:
    """
    Returns the latest snapshot of the code file.
    """
    interview_controller = get_interview_controller()
    interview_controller.file_watcher._take_snapshot()
    return interview_controller.file_watcher.last_snapshot


@function_tool()
async def get_interview_time_left() -> str:
    """Returns the current interview duration in HH:MM:SS format"""
    interview_controller = get_interview_controller()
    return interview_controller.get_interview_time_left(formatted=True)


@function_tool()
async def finish_interview():
    """Finish the interview when the coding portion of the interview is complete."""
    logger.info("Finishing the interview")
    interview_controller = get_interview_controller()
    return interview_controller.finish_interview()
