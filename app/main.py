import asyncio
from pathlib import Path
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, AgentSession, cli, llm, RoomInputOptions
from livekit.plugins import openai, silero, noise_cancellation
from components.question_manager import QuestionManager
from rich.console import Console
from components.interview_controller import InterviewController
from components.agents.intro_agent import IntroAgent
import os
import logging
from livekit.rtc import DataPacket
from utils.data_utils import DataUtils
from utils.shared_state import set_state

console = Console()
logger = logging.getLogger(__name__)
load_dotenv()

QUESTION_NUMBER = 2
PATH = "testing/test_files"


async def entrypoint(ctx: JobContext):

    logger.info("[DEBUG] Starting entrypoint")

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    logger.info("[DEBUG] Connected to room")

    # Initialize components
    question_manager = QuestionManager(Path(PATH))
    interview_controller = InterviewController(question_manager)
    interview_controller.room = ctx.room
    data_utils = DataUtils(interview_controller)
    set_state(data_utils, interview_controller)

    # Initialize the interview state
    question = question_manager.select_question(QUESTION_NUMBER)
    interview_controller.initialize_interview(question)

    asyncio.create_task(interview_controller.start_time_updates(ctx.room))

    intro_agent = IntroAgent()
    interview_controller.current_agent = intro_agent

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        allow_interruptions=False,
    )

    # Start the session - the Agent class will handle speech events internally
    await session.start(room=ctx.room, agent=intro_agent, room_input_options=RoomInputOptions(
        noise_cancellation=noise_cancellation.BVC(),
    ),)

    # Start the file watcher
    interview_controller.file_watcher.start_watching()
    asyncio.create_task(data_utils.write_transcription())
    asyncio.create_task(interview_controller.start_heartbeat())

    ########### START EVENT LISTENERS ###########

    # Attach an event listener for data packets from frontend

    @ctx.room.on("data_received")
    def handle_data_received(packet: DataPacket):
        asyncio.create_task(data_utils.process_data_packet(packet))

    ########### END EVENT LISTENERS ###########

    # Add shutdown callback for transcription writing
    ctx.add_shutdown_callback(data_utils.finish_queue)

    # Keep the agent running
    while True:
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
