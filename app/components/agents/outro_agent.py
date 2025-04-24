import asyncio
from livekit.agents import Agent, llm, AgentSession, RoomInputOptions, function_tool
from livekit.plugins import openai, silero, noise_cancellation
from livekit.plugins.turn_detector import multilingual
from utils.template_utils import load_template
from app.components.interview_controller import InterviewController
from app.components.tools import get_interview_time_left

class OutroAgent(Agent):
    """
    OutroAgent is responsible for thanking the candidate, and handling any final questions.
    """
    
    def __init__(self, interview_controller: InterviewController):
        self.template = load_template('template_outro_agent')
        super().__init__(
            instructions=self.template,
            tools=[get_interview_time_left]
        )
        self.interview_controller = interview_controller
        self.room = None
    
    @function_tool()
    async def on_exit(self):
        pass
    
        