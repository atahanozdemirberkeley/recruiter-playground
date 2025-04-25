from livekit.agents import Agent, function_tool, ChatContext, ChatMessage
from utils.template_utils import load_template
from utils.shared_state import get_interview_controller, get_data_utils
from components.tools import get_interview_time_left
from components.agents.coding_agent import CodingAgent
from utils.data_utils import DataUtils
import time
import asyncio
import logging

logger = logging.getLogger(__name__)


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
        self.data_utils = get_data_utils()
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
        self.interview_controller.start_heartbeat_task()

    async def on_user_turn_started(self, ctx: ChatContext) -> None:
        """Called when user starts speaking"""
        logger.info("User turn started - canceling heartbeat")
        self.interview_controller.cancel_heartbeat_task()
        # Update activity time
        self.interview_controller.last_activity_time = time.time()

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Called after user finishes speaking"""
        # Handle the user speech (logging, code snapshot, etc.)
        asyncio.create_task(self.data_utils.handle_user_speech(new_message))

    async def on_agent_turn_completed(self, response: ChatMessage) -> None:
        """Called after agent generates response"""
        # Log the agent's response
        asyncio.create_task(self.data_utils.handle_agent_speech(response))
        # Start heartbeat after agent finishes speaking
        self.interview_controller.start_heartbeat_task()

    @function_tool()
    async def handoff_to_coding_agent(self):
        """Hand off to the coding agent when the introduction is complete and
        the candidate is ready to start the coding portion of the interview.
        """
        # Send question data to frontend for code editor
        data_utils = get_data_utils()
        await data_utils.send_question_to_frontend()
        self.interview_controller.stage_timestamps["intro_end"] = int(
            self.interview_controller.get_interview_time_since_start())
        return CodingAgent()
