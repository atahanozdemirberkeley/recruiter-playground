import asyncio
from pathlib import Path
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, AgentSession, cli, llm, RoomInputOptions, UserStateChangedEvent, AgentStateChangedEvent, ConversationItemAddedEvent
from livekit.plugins import openai, silero, noise_cancellation
from livekit.plugins.turn_detector.english import EnglishModel
from components.question_manager import QuestionManager
from rich.console import Console
from components.interview_controller import InterviewController
from components.agents.intro_agent import IntroAgent
import os
import logging
from livekit.rtc import DataPacket
from livekit import api
from utils.data_utils import DataUtils
from utils.shared_state import set_state, set_session, get_interview_controller
from fastapi import FastAPI
# Import our new API setup utilities
from utils.api_setup import setup_api

console = Console()
logger = logging.getLogger(__name__)
load_dotenv()

QUESTION_NUMBER = 2

# Create FastAPI instance
app = FastAPI()
# Setup API with CORS and routes
setup_api(app)


async def entrypoint(ctx: JobContext):
    
    logger.info("[DEBUG] Starting entrypoint")

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    logger.info("[DEBUG] Connected to room")

    # Create LiveKit API client
    api_client = api.LiveKitAPI(
        os.getenv('LIVEKIT_URL'),
        os.getenv('LIVEKIT_API_KEY'),
        os.getenv('LIVEKIT_API_SECRET'),
    )

    # Initialize components
    question_manager = QuestionManager()
    interview_controller = InterviewController(question_manager)
    interview_controller.room = ctx.room
    interview_controller.api_client = api_client  # Store API client
    data_utils = DataUtils(interview_controller)
    set_state(data_utils, interview_controller)

    # Initialize the interview state
    question = question_manager.select_question(QUESTION_NUMBER)
    interview_controller.initialize_interview(question)

    asyncio.create_task(interview_controller.start_time_updates(ctx.room))

    intro_agent = IntroAgent()
    interview_controller.current_agent = intro_agent

    session = AgentSession(
        vad=silero.VAD.load(
            max_buffered_speech=500
        ),
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(),
        allow_interruptions=False,
        min_endpointing_delay=2,
        turn_detection=EnglishModel(),
    )
    set_session(session)

    # Start the session - the Agent class will handle speech events internally
    await session.start(room=ctx.room, agent=intro_agent, room_input_options=RoomInputOptions(
        noise_cancellation=noise_cancellation.BVC(),
    ),)

    await data_utils.send_question_to_frontend()

    # Start the file watcher
    interview_controller.file_watcher.start_watching()
    asyncio.create_task(data_utils.write_transcription())
    asyncio.create_task(interview_controller.start_heartbeat())
    ########### START EVENT LISTENERS ###########

    # Attach an event listener for data packets from frontend

    @session.on("conversation_item_added")
    def on_conversation_item_added(ev: ConversationItemAddedEvent):
        if ev.item.role == "user":
            asyncio.create_task(
                data_utils.handle_user_speech(ev.item.text_content))
        elif ev.item.role == "assistant":
            asyncio.create_task(
                data_utils.handle_agent_speech(ev.item.text_content))

    @session.on("user_state_changed")
    def on_user_state_changed(ev: UserStateChangedEvent):
        interview_controller = get_interview_controller()
        if ev.old_state == "listening" and ev.new_state == "speaking":
            # on_user_turn_started
            asyncio.create_task(interview_controller.pause_heartbeat_timer())

    @session.on("agent_state_changed")
    def on_agent_state_changed(ev: AgentStateChangedEvent):
        interview_controller = get_interview_controller()
        if ev.old_state == "speaking" and ev.new_state == "listening":
            # on_agent_turn_completed
            asyncio.create_task(interview_controller.resume_heartbeat_timer())

    @ctx.room.on("data_received")
    def handle_data_received(packet: DataPacket):
        asyncio.create_task(data_utils.process_data_packet(packet))

    ########### END EVENT LISTENERS ###########
    
    # Add shutdown callback for evaluation and room deletion
    ctx.add_shutdown_callback(interview_controller.eval_and_send_results)

    # Keep the agent running
    while True:
        if interview_controller.is_interview_complete:
            # Delete the room to disconnect everyone
            try:
                if ctx.room:
                    await api_client.room.delete_room(api.DeleteRoomRequest(
                        room=ctx.room.name,
                    ))
                    logger.info(f"Room {ctx.room.name} deleted successfully")
            except Exception as e:
                logger.error(f"Error deleting room: {e}")
                break

        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        cli.run_app(WorkerOptions(
            entrypoint_fnc=entrypoint,
            api_key=os.getenv('LIVEKIT_API_KEY'),
            api_secret=os.getenv('LIVEKIT_API_SECRET'),
            ws_url=os.getenv('LIVEKIT_URL'),
            port=8082
        ))
    except Exception as e:
        console.print(f"\nError: {e}", style="red")
    finally:
        console.print("\nShutting down...", style="yellow")
