from livekit.agents import Agent, function_tool
from utils.template_utils import load_template
from components.tools import get_file_snapshot, get_interview_time_left, finish_interview
from utils.shared_state import get_interview_controller
import logging

logger = logging.getLogger(__name__)

class CodingAgent(Agent):
    """
    CodingAgent is responsible for presenting the coding problem,
    answering clarification questions, and providing hints without revealing the full answer.
    It analyzes user code submissions and provides appropriate feedback.
    """
    
    def __init__(self):
        self.interview_controller = get_interview_controller()
        question_prompt = self.interview_controller.question_manager.get_question_prompt(self.interview_controller.question.id)
        template = load_template('template_coding_agent')
        self.template = template.format(QUESTION=question_prompt)
        super().__init__(
            instructions=self.template,
            tools=[get_file_snapshot, get_interview_time_left, finish_interview]
        )       
        
        self.question = None
        
    async def on_enter(self):
        """Initialize the coding agent with necessary components"""
        self.session.say("Now we can start the coding problem.")