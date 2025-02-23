import asyncio
import json
from datetime import datetime
from pathlib import Path
from aiofile import async_open
from api import AssistantFnc
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero
from components.filewatcher import FileWatcher
from components.question_manager import QuestionManager
from rich.console import Console
from components.interview_state import InterviewState, InterviewController
from utils.template_utils import load_template, save_prompt
import os
import logging
from livekit.rtc import DataPacket
from utils.data_utils import DataUtils


console = Console()
load_dotenv()

QUESTION_NUMBER = 1

logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext):

    # Initialize QuestionManager
    question_manager = QuestionManager(Path("testing/test_files"))

    # Initialize InterviewController with FileWatcher
    interview_controller = InterviewController(question_manager)

    # Initialize AssistantFnc with interview_controller
    fnc_ctx = AssistantFnc(interview_controller)

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Set the room in the interview controller
    interview_controller.room = ctx.room

    # Initialize DataUtils
    data_utils = DataUtils(interview_controller)

    try:
        # Initialize the interview state
        question_id, prompt_information = question_manager.select_question(
            QUESTION_NUMBER)
        interview_controller.initialize_interview(question_id)

        # Create timer updates task
        asyncio.create_task(interview_controller.start_time_updates(ctx.room))
        logger.info("Timer updates task created")

    except KeyboardInterrupt:
        console.print("\nExiting...", style="yellow")
        return

    # Load and format the template
    template = load_template('template_initial_prompt')
    formatted_prompt = template.format(
        PROMPT_INFORMATION=prompt_information
    )

    save_prompt("initial_prompt", formatted_prompt)

    # Create initial context with formatted prompt
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=formatted_prompt
    )

    agent = VoicePipelineAgent(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
        fnc_ctx=fnc_ctx,
    )

    # Update data_utils with agent reference
    data_utils.agent = agent

    # Start the file watcher
    interview_controller.file_watcher.start_watching()

    agent.start(ctx.room)

    ########### START EVENT LISTENERS ###########

    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        asyncio.create_task(data_utils.handle_user_speech(msg))

    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        asyncio.create_task(data_utils.handle_agent_speech(msg))

    # 2) Attach an event listener for data packets
    @ctx.room.on("data_received")
    def handle_data_received(packet: DataPacket):
        asyncio.create_task(data_utils.process_data_packet(packet))

    write_task = asyncio.create_task(data_utils.write_transcription())

    ctx.add_shutdown_callback(data_utils.finish_queue)

    ########### END EVENT LISTENERS ###########

    await agent.say("Hey, welcome to our interview. Are you ready to start?",
                    allow_interruptions=True)

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
