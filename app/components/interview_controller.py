from typing import Dict, Optional, Union
from components.question_manager import QuestionManager, Question
import json
from datetime import datetime, timedelta
import asyncio
import logging
from components.filewatcher import FileWatcher
from utils.shared_state import get_data_utils
import time
from livekit.agents.llm import ChatMessage, ChatChunk, ChatContext
from livekit.agents.voice import ModelSettings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEST_FILE_PATH = "testing/test.py"


class InterviewController:
    def __init__(self, question_manager: QuestionManager):
        self.question_manager = question_manager
        self.room = None
        self.current_agent = None

        # Properties from former InterviewState
        self.question = None
        self.code_snapshots = {}  # {id: {"code": str, "timestamp": int}}
        self.start_time = None
        self.stage_timestamps = {}
        self.end_time = None

        # Other controller properties
        # self.llm = LLM(
        #     model="gpt-4",
        #     temperature=0.3
        # )
        # Initialize FileWatcher
        self.file_watcher = FileWatcher(TEST_FILE_PATH)
        logger.info(f"FileWatcher initialized for {TEST_FILE_PATH}")

        # Initialize CodeExecutor with API base URL
        # self.code_executor = CodeExecutor()
        # logger.info(
        #     f"CodeExecutor initialized with API URL: {DOCKER_API_BASE_URL}")

        # Activity tracking
        self.last_activity_time = time.time()
        self.heartbeat_interval = 10  # seconds
        self._heartbeat_task: Optional[asyncio.Task] = None

    def get_file_watcher(self) -> FileWatcher:
        """Get the FileWatcher instance"""
        return self.file_watcher

    def handle_code_update(self, code: str) -> bool:
        """Handle code updates from the frontend"""
        try:
            self.last_activity_time = time.time()  # Update activity time
            success = self.file_watcher.write_content(code)
            if not success:
                logger.error("Failed to write code update to test.py")
            else:
                logger.info("Successfully wrote code update to test.py")
            return success
        except Exception as e:
            logger.error(f"Error handling code update: {e}")
            return False

    def initialize_interview(self, question: Question):
        """Initialize the interview with the selected question"""
        self.question = question
        self.code_snapshots = {}
        self.start_time = datetime.now()
        self.end_time = datetime.now() + timedelta(minutes=self.question.duration)
        self.last_activity_time = time.time()
        asyncio.create_task(get_data_utils().reset_code_editor())
        logger.info(
            f"Interview initialized with duration: {self.question.duration} minutes")

    def get_interview_time_since_start(self, formatted: bool = False) -> Union[int, str]:
        """
        Returns the current interview duration.
        Args:
            formatted (bool): If True, returns time in 'HH:MM:SS' format. If False, returns seconds.
        """
        if not self.start_time:
            return "00:00:00" if formatted else 0

        seconds = int((datetime.now() - self.start_time).total_seconds())

        if formatted:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            remaining_seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

        return seconds

    def get_interview_time_left(self, formatted: bool = False) -> Union[int, str]:
        """
        Returns the time left in the interview.
        """
        time_since_start = self.get_interview_time_since_start(formatted=False)
        time_left_seconds = int(self.question.duration * 60) - time_since_start

        if formatted:
            hours = time_left_seconds // 3600
            minutes = (time_left_seconds % 3600) // 60
            remaining_seconds = time_left_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

        return time_left_seconds

    async def start_time_updates(self, room):
        """Start publishing time updates to the room"""
        while True:
            if self.end_time:
                time_left = self.get_interview_time_left(formatted=True)

                payload = json.dumps({
                    "timeLeft": time_left
                }).encode('utf-8')

                try:
                    await room.local_participant.publish_data(
                        payload,
                        topic="interview-time"
                    )
                except Exception as e:
                    logger.error(f"Error publishing time update: {e}")

            await asyncio.sleep(1)

    async def start_interview_timer(self, duration_minutes: int):
        """Start the interview with a specified duration"""
        logger.info(f"Starting interview timer for {duration_minutes} minutes")
        self.start_time = datetime.now()
        self.end_time = self.start_time + \
            timedelta(minutes=duration_minutes)

        logger.info(
            f"Interview end time set to: {self.end_time}")

        # Start time updates when interview starts
        asyncio.create_task(self.start_time_updates(self.room))

    def add_code_snapshot(self, code: str) -> str:
        """
        Adds a new code snapshot with timestamp relative to interview start
        Returns: snapshot_id
        """
        snapshot_id = f"snapshot_{len(self.code_snapshots)}"

        self.code_snapshots[snapshot_id] = {
            "code": code,
            "timestamp": self.get_interview_time_since_start(formatted=False)
        }
        return snapshot_id

    async def run_code(self, mode: str = "run") -> Dict:
        """
        Run the current code against test cases

        Args:
            mode: Either "run" (visible tests only) or "submit" (all tests)
        """
        test_file_path = self.file_watcher.path_to_watch

        return self.code_executor.run_code(
            test_file_path=test_file_path,
            question=self.question,
            mode=mode
        )

    async def submit_code(self) -> Dict:
        """Submit the code for final evaluation"""
        return await self.run_code(mode="submit")

    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'code_executor'):
            self.code_executor.cleanup()

    def handle_test_execution(self, results: Dict) -> None:
        """Handle test execution results"""
        success = results.get('success', False)
        test_results = results.get('results', [])

        # Get the test summary if available
        test_summary = results.get('test_summary', {})
        total_tests = test_summary.get('total', len(test_results))
        passed_tests = test_summary.get('passed', sum(
            1 for r in test_results if r.get('success')))

        logger.info(
            f"Test execution completed - Success: {success}, "
            f"Passed: {passed_tests}/{total_tests} tests"
        )

        # Update with test results
        self.test_success = success
        self.test_results = test_results
        self.test_summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests
        }

    async def finish_interview(self) -> None:
        """
        Finalize the interview process, record data, and clean up resources.

        Returns:
            Dict: Summary of the interview including duration, test results, and stage data
        """
        # Record completion time
        completion_time = datetime.now()
        self.end_time = completion_time

        # Calculate duration
        total_duration_seconds = int(
            (completion_time - self.start_time).total_seconds())
        hours = total_duration_seconds // 3600
        minutes = (total_duration_seconds % 3600) // 60
        seconds = total_duration_seconds % 60
        formatted_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Prepare summary data
        interview_summary = {
            "question_id": self.question.id,
            "question_title": self.question.title,
            "duration": {
                "seconds": total_duration_seconds,
                "formatted": formatted_duration
            },
            "stages": self.stage_timestamps,
            "code_snapshots_count": len(self.code_snapshots),
            "completed": True
        }

        # Clean up resources
        # self.cleanup()

        # Log completion
        logger.info(f"Interview completed in {formatted_duration}")

        # Publish completion to room if available
        if self.room:
            try:
                payload = json.dumps({
                    "event": "interview_completed",
                    "summary": interview_summary
                }).encode('utf-8')

                asyncio.create_task(
                    self.room.local_participant.publish_data(
                        payload,
                        topic="interview-status"
                    )
                )
            except Exception as e:
                logger.error(f"Error publishing interview completion: {e}")

        return

    async def start_heartbeat(self):
        """
        Start the heartbeat task that checks for user inactivity.
        If the user is inactive for longer than the heartbeat interval,
        the agent will be triggered to interact.
        """
        logger.info(
            f"[DEBUG - interview_controller.py] Starting heartbeat with interval of {self.heartbeat_interval} seconds")
        while True:
            try:
                current_time = time.time()
                idle_time = current_time - self.last_activity_time

                # Check if user has been inactive
                if idle_time > self.heartbeat_interval:
                    logger.info(
                        f"User has been inactive for {idle_time:.1f} seconds, triggering agent interaction")
                    await self.trigger_heartbeat_interaction(self.current_agent)
                    # Reset the activity time to avoid multiple triggers in a row
                    self.last_activity_time = current_time

                # Wait before next check
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                logger.info("Heartbeat task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}")
                await asyncio.sleep(5)  # Continue despite errors

    async def trigger_heartbeat_interaction(self, agent):
        """Trigger the agent to interact with the user during inactivity."""
        try:
            logger.info("[DEBUG] Triggering heartbeat interaction")
            # Get context info
            interview_time = self.get_interview_time_since_start(
                formatted=True)
            time_left = self.get_interview_time_left(formatted=True)

            # Create a system message with key context
            heartbeat_context = f"""
            [SYSTEM NOTE: The user has been inactive for over {self.heartbeat_interval} seconds.
            Current interview time: {interview_time}
            Time remaining: {time_left}

            Check if the user needs help. If code seems incomplete or has issues, ask if they're stuck.
            If they seem to be making good progress but just thinking, encourage them to continue.
            Keep your response brief and supportive.

            If you don't think an interaction is needed right now, please respond with an empty string
            and we will not interrupt the user's thinking time.]
            """

            ctx = self.current_agent.chat_ctx.copy()
            ctx.add_message(
                role="system",
                content=heartbeat_context
            )

            generated_text = ""
            async for chunk in self.current_agent.llm_node(ctx, tools=[], model_settings=ModelSettings()):
                if isinstance(chunk, ChatChunk):
                    # Check delta and content are not None before adding
                    if chunk.delta and chunk.delta.content:
                        generated_text += chunk.delta.content
                else:
                    # If it's not a ChatChunk, ensure it's a string before adding
                    generated_text += str(chunk) if chunk is not None else ""

            logger.info("[HB] raw reply -> %r", generated_text)

            if generated_text.strip():
                await self.current_agent.session.say(generated_text)
                logger.info("[HB] response spoken")
            else:
                logger.info("[HB] response suppressed")

        except Exception as e:
            logger.error(f"Error in heartbeat: {e}")

    def start_heartbeat_task(self):
        # Start the heartbeat loop, canceling any existing heartbeat task.
        self.cancel_heartbeat_task()
        logger.info("Starting heartbeat task")
        self._heartbeat_task = asyncio.create_task(self.start_heartbeat())

    def cancel_heartbeat_task(self):
        # Cancel the heartbeat task if running.
        if self._heartbeat_task:
            logger.info("Canceling heartbeat task")
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
