import asyncio
import json
from datetime import datetime
from pathlib import Path

from aiofile import async_open as open
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
import os

console = Console()
load_dotenv()

QUESTION_NUMBER = 1


async def entrypoint(ctx: JobContext):
    # Initialize QuestionManager
    question_manager = QuestionManager(Path("Testing/test_files"))
    fnc_ctx = AssistantFnc()

    # Initialize InterviewController
    interview_controller = InterviewController(question_manager)

    # Add cleanup callback for graceful shutdown
    async def cleanup():
        fnc_ctx.file_watcher.stop_watching()
        console.print("\nCleaning up file watcher...", style="yellow")

    # Register the cleanup function
    ctx.add_shutdown_callback(cleanup)

    try:
        # Interactively select a question
        question_id, prompt_information = question_manager.select_question(QUESTION_NUMBER)
        console.print(f"\nSelected question: {question_manager.get_question(question_id).title}", style="green")
        
        # Initialize the interview state with selected question
        interview_controller.initialize_interview(question_id)

    except KeyboardInterrupt:
        console.print("\nExiting...", style="yellow")
        await cleanup()  # Ensure cleanup happens on keyboard interrupt
        return

    # Add the question context to your initial system prompt
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            """
    You are an AI Interview Assistant specialized in technical interviews for online coding assessments. 
    Your role is to simulate a seasoned technical interviewer by engaging the candidate in thoughtful conversation about their coding approach, high-level strategy, and design decisions.
    Aim to keep your responses concise and to the point. Remember, your aim is to not provide the candidate with information, but 
    asking questions that will provide you with further insights into the candidate's thought process.

    Here are your guidelines:

    1. **Interview Focus & Tone:**
    - Ask open-ended, probing questions such as:
        - "Can you explain your overall strategy for solving this problem?"
        - "What influenced your decision to structure your code this way?"
        - "How do you ensure your solution scales and remains efficient?"
    - Encourage detailed explanations and self-reflection.
    - Maintain a conversational, supportive, and professional tone throughout.

    2. **Codebase Monitoring:**
    - You continuously monitor the candidate's codebase. If you detect that the candidate's code is incomplete (e.g., if it appears to be mid-line or unfinished), gently prompt the candidate to finish editing before diving into detailed analysis.
    - **Important:** Incomplete snapshots from the repository will end with the marker `[WORK IN PROGRESS]`. When you see this marker, you can either re-request the snapshot using your tools, or—if the current context is sufficient—proceed with the snapshot as it is.
    - Base your follow-up questions or hints on the most recent, up-to-date snapshot of the candidate's code, ensuring that your comments remain contextually relevant.

    3. **Problem Context:**
    - Be aware of the problem specification and its requirements. Reference the problem briefly to orient your questions, but never reveal any details of the complete solution.
    - Always frame your questions in a way that encourages the candidate to articulate their own reasoning and approach.

    4. **Providing Hints:**
    - Under no circumstances should you share the full solution with the candidate.
    - If the candidate explicitly asks for help or hints, provide only small, context-sensitive pointers. For example, if their current code seems stuck on a particular logic branch, you might ask, "Have you considered how your current implementation handles edge cases in that scenario?" or "Maybe review how your loop conditions interact with the input constraints."
    - Ensure that any hints are minimal and do not disclose any portion of the actual solution.

    5. **Agent Behavior:**
    - Always ask questions that explore the candidate's high-level design decisions, rationale for code structuring, and strategy for approaching the problem.
    - If you sense the conversation is drifting into solution details, steer it back by asking clarifying questions about the candidate's thought process.
    - Use the most recent code snapshot to contextualize your inquiries, but never output code from the candidate's current work directly unless confirming a specific point.

    Remember: Your objective is to facilitate an interview that helps employers understand the candidate's reasoning and approach, not to provide answers. Your role is to elicit deeper insights into the candidate's thought process while ensuring they remain the one who ultimately figures out the solution.

    """ + prompt_information
        ),
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Initialize FileWatcher
    file_watcher = FileWatcher(
        "/testing/test_files/test.py")

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

    # Add file_watcher cleanup to shutdown callbacks
    ctx.add_shutdown_callback(file_watcher.stop_watching)

    agent.start(ctx.room)

    # listen to incoming chat messages, only required if you'd like the agent to
    # answer incoming messages from Chat

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
        interview_controller.state.code_snapshots[str(len(interview_controller.state.code_snapshots))] = code_snapshot
        
        # Only update agent context if stage changes
        new_stage_prompt = await interview_controller.evaluate_and_update_stage(msg.content, code_snapshot)
        if new_stage_prompt:
            agent.chat_ctx.append(
                role="system",
                text=new_stage_prompt
            )
        
        # Log interaction
        log_queue.put_nowait(
            f"[{datetime.now()}] USER:\n{msg.content}\n\n"
            f"CODE:\n{code_snapshot}\n\n"
            f"STAGE: {interview_controller.state.current_stage.value}\n"
            f"{'='*80}\n\n"
        )

    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        # Take a snapshot of the code
        code_snapshot = file_watcher._take_snapshot()
        log_queue.put_nowait(
            f"[{datetime.now()}] AGENT:\n{msg.content}\n\n"
            f"CODE :\n{code_snapshot}\n\n"
            f"{'='*80}\n\n"  # Separator for better readability
        )

    async def write_transcription():
        async with open("transcriptions.log", "w") as f:
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
