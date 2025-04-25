from livekit.agents import Agent, function_tool, ChatContext, ChatMessage, StopResponse
from utils.template_utils import load_template
from components.tools import get_file_snapshot, get_interview_time_left, finish_interview
from utils.shared_state import get_interview_controller, get_data_utils
import logging
import time
import asyncio

logger = logging.getLogger(__name__)


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
        self.last_activity_time = None

    async def on_user_turn_started(self, ctx: ChatContext) -> None:
        """Called when user starts speaking"""
        self.interview_controller.cancel_heartbeat_task()
        # Update activity time
        self.interview_controller.last_activity_time = time.time()

    async def on_agent_turn_completed(self, response: ChatMessage) -> None:
        """Called after agent generates response"""
        # Log the agent's response
        asyncio.create_task(self.data_utils.handle_agent_speech(response))
        # Start heartbeat after agent finishes speaking
        self.interview_controller.start_heartbeat_task()
