"""Shared state management"""

from typing import Optional
from app.components.interview_state import InterviewController

class SharedState:
    interview_controller: Optional[InterviewController] = None

shared_state = SharedState()

def set_interview_controller(interview_controller: InterviewController):
    shared_state.interview_controller = interview_controller

def get_interview_controller() -> Optional[InterviewController]:
    return shared_state.interview_controller
