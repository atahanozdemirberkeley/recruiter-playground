from livekit.agents import Agent, function_tool, ChatContext, ChatMessage, StopResponse
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
        self.last_code_snapshot = None
        self.last_activity_time = None
        
    async def on_enter(self):
        """Initialize the coding agent with necessary components"""
        self.interview_controller.current_agent = self
        self.session.say("Now we can start the coding problem.")
        
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """
        Called when the user finishes speaking, before the agent generates a response.
        This is where we can add current code context to help the agent understand
        what the user is working on.
        
        Args:
            turn_ctx: The current chat context
            new_message: The user's message that triggered this turn
        """
        # Only continue if there's an actual message
        if not new_message.text_content:
            return
            
        # Get the current code snapshot
        current_code = self.interview_controller.file_watcher._take_snapshot()
        
        # Only add code context if code has changed from last time
        if current_code != self.last_code_snapshot and current_code.strip():
            # Add current code context as a system message
            code_context = f"""
                [SYSTEM NOTE: Here's the candidate's current code:
                ```python
                {current_code}
                ```
                Current interview time: {self.interview_controller.get_interview_time_since_start(formatted=True)}
                ] You don't need to respond to this message.
                """
            # Add to the context for this response only
            turn_ctx.add_message(role="system", content=code_context)
            
            # Update our stored snapshot
            self.last_code_snapshot = current_code
            
        # If needed, you can persist changes to the chat context with:
        # chat_ctx = turn_ctx.copy()
        # chat_ctx.add_message(...)
        # await self.update_chat_ctx(chat_ctx)