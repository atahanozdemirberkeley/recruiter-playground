from livekit.agents import Agent, function_tool
from utils.template_utils import load_template
from utils.shared_state import get_interview_controller
from components.tools import get_interview_time_left
from components.agents.coding_agent import CodingAgent
from utils.data_utils import DataUtils

class IntroAgent(Agent):
    """
    IntroAgent is responsible for greeting the candidate, explaining the interview process,
    and handling clarification questions before handing off to the coding agent.
    """
    
    def __init__(self):
        self.template = load_template('template_intro_agent')
        super().__init__(
            instructions=self.template,
            tools=[get_interview_time_left]
        )
        self.interview_controller = get_interview_controller()
        self.room = None

    async def on_enter(self):
        """Send the initial greeting to the user"""
        await self.session.say(
            """Hello, and welcome to this AI-powered technical interview. 
            I'm here to help you through this interview process.
            Today, you'll be solving a coding problem similar to what you might encounter in real technical interviews.
            Before we start, could you briefly introduce yourself? 
            And please feel free to ask any questions about the process."""
        )
    
    @function_tool()
    async def handoff_to_coding_agent(self):
        """Hand off to the coding agent when the introduction is complete and
        the candidate is ready to start the coding portion of the interview.
        """
        # Send question data to frontend for code editor
        data_utils = self.interview_controller.data_utils
        await data_utils.send_question_to_frontend()
        
        return CodingAgent()
    
    
        