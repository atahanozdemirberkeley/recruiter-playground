from livekit.agents import Agent, function_tool, ChatContext, ChatMessage, StopResponse
from utils.template_utils import load_template
from components.tools import get_file_snapshot, get_interview_time_left, finish_interview
from utils.shared_state import get_interview_controller, get_data_utils, get_session
import logging
import time
import asyncio

logger = logging.getLogger(__name__)
session = None


class CodingAgent(Agent):
    """
    CodingAgent is responsible for presenting the coding problem,
    answering clarification questions, and providing hints without revealing the full answer.
    It analyzes user code submissions and provides appropriate feedback.
    """

    def __init__(self):
        self.interview_controller = get_interview_controller()
        self.data_utils = get_data_utils()
        question_prompt = self.interview_controller.question_manager.get_question_prompt(
            self.interview_controller.question.id)
        template = load_template('template_coding_agent')
        self.template = template.format(QUESTION=question_prompt)
        super().__init__(
            instructions=self.template,
            tools=[get_file_snapshot, get_interview_time_left, finish_interview]
        )

        self.question = None
        self.last_code_snapshot = None
        global session
        session = get_session()

    async def on_enter(self):
        """Called when the agent enters the conversation"""
        self.interview_controller.current_agent = self

        await self.session.generate_reply(
            instructions="Start by introducing the coding problem now.",
        )

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Called when user finishes speaking"""
        asyncio.create_task(self.data_utils.handle_user_speech(new_message))
        # Resume heartbeat timer when user finishes speaking
        self.interview_controller.resume_heartbeat_timer()

    async def on_agent_turn_completed(self, response: ChatMessage) -> None:
        """Called after agent generates response"""
        asyncio.create_task(self.data_utils.handle_agent_speech(response))
        # Resume heartbeat timer when agent finishes speaking
        self.interview_controller.resume_heartbeat_timer()

    async def on_agent_turn_started(self, turn_ctx: ChatContext) -> None:
        """Called when agent starts speaking"""
        # Pause heartbeat timer when agent starts speaking
        self.interview_controller.pause_heartbeat_timer()
    
    async def on_user_turn_started(self, turn_ctx: ChatContext) -> None:
        """Called when user starts speaking"""
        # Pause heartbeat timer when user starts speaking
        self.interview_controller.pause_heartbeat_timer()

    def get_heartbeat_context(self) -> str:
        """
        Get the heartbeat context template for the coding agent.

        Returns:
            str: Formatted heartbeat context template
        """
        try:
            # Load the template specific to this agent type
            template_path = "heartbeats/template_heartbeat_coding_agent"
            template = load_template(template_path)

            # Get context info from interview controller
            interview_time = self.interview_controller.get_interview_time_since_start(
                formatted=True)
            time_since_last_interaction = time.time(
            ) - self.interview_controller.last_activity_time
            time_left = self.interview_controller.get_interview_time_left(
                formatted=True)
            heartbeat_interval = self.interview_controller.heartbeat_interval
            self.interview_controller.file_watcher._take_snapshot()
            code_snapshot = self.interview_controller.file_watcher.last_snapshot

            # Format the template with context
            return template.format(
                heartbeat_interval=heartbeat_interval,
                interview_time=interview_time,
                time_left=time_left,
                current_code=code_snapshot,
                time_since_last_interaction=time_since_last_interaction
            )
        except Exception as e:
            logger.error(
                f"Error loading heartbeat template for coding agent: {e}")
            # Fallback to a generic template
            return ""
