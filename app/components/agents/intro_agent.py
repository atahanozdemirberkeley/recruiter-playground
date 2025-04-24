import asyncio
from livekit.agents import Agent, llm, AgentSession, RoomInputOptions, function_tool
from livekit.plugins import openai, silero, noise_cancellation
from livekit.plugins.turn_detector import multilingual
from utils.template_utils import load_template
from app.components.interview_controller import InterviewController
from app.components.tools import get_interview_time_left

class IntroAgent(Agent):
    """
    IntroAgent is responsible for greeting the candidate, explaining the interview process,
    and handling clarification questions before handing off to the coding agent.
    """
    
    def __init__(self, interview_controller: InterviewController):
        self.template = load_template('template_intro_agent')
        super().__init__(
            instructions=self.template,
            tools=[get_interview_time_left]
        )
        self.interview_controller = interview_controller
        self.room = None

    async def on_enter(self):
        """Send the initial greeting to the user"""
        await self.agent.say(
            """Hello, and welcome to this AI-powered technical interview. 
            I'm here to help you through this interview process.
            Today, you'll be solving a coding problem similar to what you might encounter in real technical interviews.
            Before we start, could you briefly introduce yourself? 
            And please feel free to ask any questions about the process.""", 
            allow_interruptions=True
        )
    
    @function_tool()
    async def handoff_to_coding_agent(self):
        """Handoff to the coding agent"""
        #TODO
        pass
    
    
        