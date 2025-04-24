import asyncio
import re
from livekit.agents import Agent, llm, AgentSession, RoomInputOptions, function_tool
from livekit.plugins import openai, silero, noise_cancellation
from livekit.plugins.turn_detector import multilingual
from utils.template_utils import load_template
from app.components.tools import get_file_snapshot, get_interview_time_left

class CodingAgent(Agent):
    """
    CodingAgent is responsible for presenting the coding problem,
    answering clarification questions, and providing hints without revealing the full answer.
    It analyzes user code submissions and provides appropriate feedback.
    """
    
    def __init__(self, interview_controller):
        self.template = load_template('template_coding_agent')
        super().__init__(
            instructions=self.template,
            tools=[get_file_snapshot, get_interview_time_left]
        )
        self.interview_controller = interview_controller
        self.question = None
        
    async def on_enter(self):
        """Initialize the coding agent with necessary components"""
        pass

    @function_tool()
    async def handoff_to_outro_agent(self):
        """Handoff to the outro agent"""
        #TODO
        pass
    