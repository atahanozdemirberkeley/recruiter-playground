from livekit.agents import Agent, function_tool
from utils.template_utils import load_template
from utils.shared_state import get_interview_controller, get_data_utils
from components.tools import get_interview_time_left
from components.agents.coding_agent import CodingAgent
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
            Today, you'll be solving a coding problem similar to what you might encounter in real technical interviews.
            As your interviewer, I am here to help you through the process.
            Before we start, could you briefly introduce yourself?
            Also, please feel free to ask any questions about the process."""
        )

    def get_heartbeat_context(self) -> str:
        """
        Get the heartbeat context template for the intro agent.

        Returns:
            str: Formatted heartbeat context template
        """
        try:
            # Load the template specific to this agent type
            template_path = "heartbeats/template_heartbeat_intro_agent"
            template = load_template(template_path)

            # Get context info from interview controller
            interview_time = self.interview_controller.get_interview_time_since_start(
                formatted=True)
            time_left = self.interview_controller.get_interview_time_left(
                formatted=True)
            heartbeat_interval = self.interview_controller.heartbeat_interval

            # Format the template with context
            return template.format(
                heartbeat_interval=heartbeat_interval,
                interview_time=interview_time,
                time_left=time_left
            )
        except Exception as e:
            logger.error(
                f"Error loading heartbeat template for intro agent: {e}")
            # Fallback to a generic template
            return ""

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
