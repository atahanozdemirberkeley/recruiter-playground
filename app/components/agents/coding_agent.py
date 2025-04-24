import asyncio
import re
from livekit.agents import Agent, llm, AgentSession, RoomInputOptions
from livekit.plugins import openai, silero, noise_cancellation
from livekit.plugins.turn_detector import multilingual
from utils.template_utils import load_template
from api import CodeTools

class CodingAgent:
    """
    CodingAgent is responsible for presenting the coding problem,
    answering clarification questions, and providing hints without revealing the full answer.
    It analyzes user code submissions and provides appropriate feedback.
    """
    
    def __init__(self, interview_controller):
        self.interview_controller = interview_controller
        self.template = load_template('template_coding_agent')
        self.agent = None
        self.session = None
        self.current_question = None
        self.hint_level = 0
        self.max_hint_level = 3
        self.file_watcher = None
        self.code_tools = None
        
    async def initialize(self, room, question_data):
        """Initialize the coding agent with necessary components"""
        self.current_question = question_data
        
        # Set up file watcher if available
        if hasattr(self.interview_controller, 'file_watcher'):
            self.file_watcher = self.interview_controller.file_watcher
            self.file_watcher.add_callback(self._on_file_change)
            
            # Initialize code tools
            self.code_tools = CodeTools(self.file_watcher)
        
        # Create system prompt for the coding agent with question details
        formatted_template = self.template.format(
            QUESTION_TITLE=question_data.get('title', 'Coding Question'),
            QUESTION_DESCRIPTION=question_data.get('description', ''),
            QUESTION_EXAMPLES=question_data.get('examples', ''),
            QUESTION_CONSTRAINTS=question_data.get('constraints', ''),
            SOLUTION_APPROACH=question_data.get('solution_approach', ''),
            HINTS=question_data.get('hints', [])
        )
        
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=formatted_template
        )
        
        # Create agent with instructions
        self.agent = Agent(instructions=formatted_template)
        
        # Create agent session
        self.session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(),
            llm=openai.LLM(),
            tts=openai.TTS(),
            turn_detection=multilingual.MultilingualModel(),
            chat_ctx=initial_ctx,
            fnc_ctx=self.code_tools if self.code_tools else None
        )
        
        # Start the session
        await self.session.start(
            room=room,
            agent=self.agent,
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        )
        
        # Register event handlers
        self._register_events()
        
        return self.agent
    
    def _register_events(self):
        """Register event handlers for the coding agent"""
        @self.agent.on("user_speech_committed")
        def on_user_speech_committed(msg: llm.ChatMessage):
            asyncio.create_task(self._handle_user_speech(msg))
    
    async def _handle_user_speech(self, msg: llm.ChatMessage):
        """Handle user speech events during coding"""
        text = msg.text.lower()
        
        # Check for hint requests
        if any(phrase in text for phrase in ["hint", "help", "stuck", "not sure", "confused"]):
            await self._provide_hint()
        
        # Check for solution explanation requests
        elif any(phrase in text for phrase in ["solution", "answer", "solve", "how to solve"]):
            await self._explain_approach_not_solution()
        
        # Check for completion indication
        elif any(phrase in text for phrase in ["i'm done", "finished", "complete", "submitted"]):
            await self._review_solution()
            
        # Check for readiness to end coding portion
        elif any(phrase in text for phrase in ["move on", "next part", "wrap up"]):
            await self._prepare_for_handoff()
    
    async def _provide_hint(self):
        """Provide an appropriate hint based on the current hint level"""
        hints = self.current_question.get('hints', [])
        
        if not hints or self.hint_level >= len(hints) or self.hint_level >= self.max_hint_level:
            await self.agent.say(
                "I'd suggest reviewing your approach. Think about edge cases and the constraints of the problem. "
                "Can you walk me through your current thought process?",
                allow_interruptions=True
            )
        else:
            await self.agent.say(
                f"Here's a hint that might help: {hints[self.hint_level]}",
                allow_interruptions=True
            )
            self.hint_level += 1
    
    async def _explain_approach_not_solution(self):
        """Explain a general approach without revealing the full solution"""
        approach = self.current_question.get('solution_approach', '')
        
        if approach:
            # Extract just the high-level approach, not the detailed solution
            high_level = self._extract_high_level_approach(approach)
            await self.agent.say(
                f"I can give you a general approach without revealing the full solution. {high_level} "
                f"Would you like me to clarify any part of this approach?",
                allow_interruptions=True
            )
        else:
            await self.agent.say(
                "I'm here to guide you, not provide the solution directly. Let's think about this step by step. "
                "What have you tried so far, and where are you getting stuck?",
                allow_interruptions=True
            )
    
    def _extract_high_level_approach(self, approach):
        """Extract a high-level approach from the detailed solution"""
        # This is a simplified implementation - in a real system, you'd want more sophistication
        sentences = re.split(r'(?<=[.!?])\s+', approach)
        if len(sentences) <= 2:
            return approach
        return ' '.join(sentences[:2])  # Return just the first two sentences
    
    async def _review_solution(self):
        """Review the candidate's solution"""
        # In a real implementation, this would analyze the code and provide feedback
        await self.agent.say(
            "Let me take a look at your solution. I'll check for correctness, efficiency, and code quality.",
            allow_interruptions=False
        )
        
        # Get the latest code using CodeTools
        code_content = self.file_watcher.latest_content if self.file_watcher else None
        
        # Simulate code review (in a real system, you'd analyze the actual code)
        if code_content:
            await self._analyze_code(code_content)
        else:
            await self.agent.say(
                "I don't see your code submission yet. Can you make sure it's saved properly?",
                allow_interruptions=True
            )
    
    async def _analyze_code(self, code_content):
        """Analyze the submitted code - placeholder for actual code analysis"""
        # In a real implementation, this would perform actual code analysis
        # This is a simplified placeholder
        await asyncio.sleep(2)  # Simulate analysis time
        
        await self.agent.say(
            "I've reviewed your solution. Your approach looks solid. Let's discuss a few aspects of your code. "
            "First, let's talk about the time and space complexity. Based on your implementation, "
            "what do you think the time complexity is?",
            allow_interruptions=True
        )
    
    async def _on_file_change(self, file_path, content):
        """Handle file changes during the coding session"""
        # This would be called when the candidate modifies their code
        # You could implement real-time feedback here if desired
        pass
    
    async def _prepare_for_handoff(self):
        """Prepare to hand off to the outro agent"""
        await self.agent.say(
            "Great job with the coding portion! Let's wrap up this part of the interview and move on to some reflection questions.",
            allow_interruptions=True
        )
        await self.interview_controller.transition_to_outro_agent()
    
    async def present_question(self):
        """Present the coding question to the candidate"""
        question = self.current_question
        
        intro = (
            f"Now, let's move on to the coding challenge. Today, you'll be solving the problem: {question.get('title', 'Coding Problem')}. "
            f"I'll explain the problem, and then you'll have time to solve it. "
            f"Feel free to ask clarifying questions before you start coding."
        )
        
        await self.agent.say(intro, allow_interruptions=True)
        await asyncio.sleep(1)
        
        description = (
            f"{question.get('description', '')} "
            f"\n\nHere are some examples: {question.get('examples', '')} "
            f"\n\nAnd here are the constraints: {question.get('constraints', '')}"
        )
        
        await self.agent.say(description, allow_interruptions=True)
        
        await self.agent.say(
            "Do you have any questions about the problem before you start coding?",
            allow_interruptions=True
        )
