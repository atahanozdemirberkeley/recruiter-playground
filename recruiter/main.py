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
from utils.template_utils import load_template
import os
import logging


console = Console()
load_dotenv()

QUESTION_NUMBER = 1

logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext):
    # Initialize QuestionManager
    question_manager = QuestionManager(Path("testing/test_files"))
    fnc_ctx = AssistantFnc()

    # Initialize InterviewController
    interview_controller = InterviewController(question_manager)
    fnc_ctx.interview_controller = interview_controller

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Set the room in the interview controller
    interview_controller.room = ctx.room

    try:
        # Initialize the interview state (synchronous)
        question_id, prompt_information = question_manager.select_question(
            QUESTION_NUMBER)
        interview_controller.initialize_interview(question_id)

        # Explicitly create and start the timer updates task
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

    os.makedirs("prompts", exist_ok=True)
    async with async_open("prompts/initial_prompt", "w") as f:
        f.write(formatted_prompt)



    # Create initial context with formatted prompt
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=formatted_prompt
    )

    # Initialize FileWatcher
    file_watcher = FileWatcher(
        "recruiter/testing/test.py")

    agent = VoicePipelineAgent(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
        fnc_ctx=fnc_ctx,
    )

    # Start the file watcher
    file_watcher.start_watching()

    agent.start(ctx.room)

    log_queue = asyncio.Queue()

    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        asyncio.create_task(async_handle_speech(msg))

    async def async_handle_speech(msg: llm.ChatMessage):
        if isinstance(msg.content, list):
            msg.content = "\n".join(
                "[image]" if isinstance(x, llm.ChatImage) else x for x in msg
            )

        # Take code snapshot
        code_snapshot = file_watcher._take_snapshot()
        interview_controller.state.code_snapshots[str(
            len(interview_controller.state.code_snapshots))] = code_snapshot

        # Only update agent context if stage changes
        new_stage_prompt = await interview_controller.evaluate_and_update_stage(msg.content, code_snapshot)
        if new_stage_prompt:
            agent.chat_ctx.append(
                role="system",
                text=new_stage_prompt
            )

        # Log interaction with interview duration
        duration = interview_controller.get_interview_time_since_start()
        log_queue.put_nowait(
            f"[{duration}] USER:\n{msg.content}\n\n"
            f"CODE:\n{code_snapshot}\n\n"
            f"STAGE: {interview_controller.state.current_stage.value}\n"
            f"{'='*80}\n\n"
        )

    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        # Take a snapshot of the code
        code_snapshot = file_watcher._take_snapshot()
        duration = interview_controller.get_interview_time_since_start()
        log_queue.put_nowait(
            f"[{duration}] AGENT:\n{msg.content}\n\n"
            f"CODE :\n{code_snapshot}\n\n"
            f"{'='*80}\n\n"  # Separator for better readability
        )

    async def write_transcription():
        async with async_open("transcriptions.log", "w") as f:
            while True:
                msg = await log_queue.get()
                if msg is None:
                    break
                await f.write(msg)

    write_task = asyncio.create_task(write_transcription())

    async def finish_queue():
        log_queue.put_nowait(None)
        await write_task

    ctx.add_shutdown_callback(finish_queue)

    await agent.say("Hey, welcome to our interview. Are you ready to start?",
                    allow_interruptions=True)

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