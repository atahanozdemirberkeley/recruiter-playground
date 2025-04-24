from livekit.agents import Agent, function_tool
from utils.template_utils import load_template
from utils.shared_state import get_interview_controller
from components.tools import get_interview_time_left

class OutroAgent(Agent):
    """
    OutroAgent is responsible for thanking the candidate, and handling any final questions.
    """
    
    def __init__(self):
        self.template = load_template('template_outro_agent')
        super().__init__(
            instructions=self.template,
            tools=[get_interview_time_left]
        )
        self.interview_controller = get_interview_controller()
        self.room = None
    
    @function_tool()
    async def on_exit(self):
        pass
    
        