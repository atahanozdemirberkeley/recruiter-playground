"""Shared state management"""

_interview_controller = None
_data_utils = None

def set_state(data_utils_instance, interview_controller_instance):
    """Set shared state instances"""
    global _interview_controller, _data_utils
    _interview_controller = interview_controller_instance
    _data_utils = data_utils_instance

def get_interview_controller():
    """Get the shared interview controller instance"""
    return _interview_controller

def get_data_utils():
    """Get the shared data utils instance"""
    return _data_utils
