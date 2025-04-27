"""Shared state management"""

# Remove all imports that could cause circular references
# from components.interview_controller import InterviewController
# from utils.data_utils import DataUtils

_interview_controller = None
_data_utils = None
_session = None

def set_state(data_utils_instance, interview_controller_instance):
    """Set shared state instances"""
    global _interview_controller, _data_utils
    _interview_controller = interview_controller_instance
    _data_utils = data_utils_instance

def set_session(session_instance):
    """Set the shared session instance"""
    global _session
    _session = session_instance

def get_interview_controller():
    """Get the shared interview controller instance"""
    return _interview_controller

def get_data_utils():
    """Get the shared data utils instance"""
    return _data_utils

def get_session():
    """Get the shared session instance"""
    return _session


