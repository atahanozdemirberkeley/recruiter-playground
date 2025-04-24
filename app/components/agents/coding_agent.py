from livekit.agents import Agent, function_tool
from utils.template_utils import load_template
from components.tools import get_file_snapshot, get_interview_time_left
from utils.shared_state import get_interview_controller
from components.agents.outro_agent import OutroAgent

class CodingAgent(Agent):
    """
    CodingAgent is responsible for presenting the coding problem,
    answering clarification questions, and providing hints without revealing the full answer.
    It analyzes user code submissions and provides appropriate feedback.
    """
    
    def __init__(self):
        self.template = load_template('template_coding_agent')
        super().__init__(
            instructions=self.template,
            tools=[get_file_snapshot, get_interview_time_left]
        )       
        self.interview_controller = get_interview_controller()
        self.question = None
        
    async def on_enter(self):
        """Initialize the coding agent with necessary components"""
        pass

    @function_tool()
    async def handoff_to_outro_agent(self):
        """Handoff to the outro agent when the coding portion of the interview is complete."""
        return OutroAgent()
    