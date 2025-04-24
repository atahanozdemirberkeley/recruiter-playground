import asyncio
from livekit.agents import Agent, llm, AgentSession, RoomInputOptions
from livekit.plugins import openai, silero, noise_cancellation
from livekit.plugins.turn_detector import multilingual
from utils.template_utils import load_template
from app.components.interview_state import InterviewController

class IntroAgent:
    """
    IntroAgent is responsible for greeting the candidate, explaining the interview process,
    and handling clarification questions before handing off to the coding agent.
    """
    
    def __init__(self):
        self.interview_controller = None
        self.agent = None
        self.session = None
        
    async def initialize(self, room, interview_controller):
        """Initialize the intro agent with necessary components"""
        self.interview_controller = interview_controller

        self.template = load_template('template_intro_agent')
        
        # Create initial context with template
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=self.template
        )
        
        # Create agent with instructions
        self.agent = Agent(instructions=self.template)
        
        # Create agent session
        self.session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(),
            llm=openai.LLM(),
            tts=openai.TTS(),
            turn_detection=multilingual.MultilingualModel(),
            chat_ctx=initial_ctx,
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
        """Register event handlers for the intro agent"""
        @self.agent.on("user_speech_committed")
        def on_user_speech_committed(msg: llm.ChatMessage):
            asyncio.create_task(self._handle_user_speech(msg))
    
    async def _handle_user_speech(self, msg: llm.ChatMessage):
        """Handle user speech events"""
        # Check if it's time to hand off to coding agent
        if self._should_handoff_to_coding_agent(msg.text):
            await self.handoff_to_coding_agent()
    
    def _should_handoff_to_coding_agent(self, text):
        """Determine if it's time to hand off to the coding agent based on user input"""
        # This is a simple implementation - you'd want more sophisticated logic
        handoff_phrases = [
            "i'm ready", "let's start", "ready to begin", 
            "start coding", "begin the coding", "give me the question"
        ]
        
        return any(phrase in text.lower() for phrase in handoff_phrases)
    
    async def handoff_to_coding_agent(self):
        """Handle the transition to the coding agent"""
        await self.agent.say("Great! I'll now hand you over to our coding specialist who will guide you through the technical portion of the interview.")
        await self.interview_controller.transition_to_coding_agent()
        
    async def greet_candidate(self):
        """Send the initial greeting to the candidate"""
        await self.agent.say(
            """Hello, and welcome to this AI-powered technical interview. 
            I'm here to help you through this interview process.
            Today, you'll be solving a coding problem similar to what you might encounter in real technical interviews.
            Before we start, could you briefly introduce yourself? 
            And please feel free to ask any questions about the process.""", 
            allow_interruptions=True
        )
