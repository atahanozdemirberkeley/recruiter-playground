from enum import Enum
from typing import List, Dict, Optional, Union
from components.question_manager import QuestionManager, Question
import json
from utils.template_utils import load_template, save_prompt
from livekit.plugins.openai import LLM
from livekit.agents import llm
from datetime import datetime, timedelta
import asyncio
import logging
from livekit import rtc
from components.filewatcher import FileWatcher
from components.code_executor import CodeExecutor
from config import DOCKER_API_BASE_URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEST_FILE_PATH = "testing/test.py"
class InterviewStage(Enum):
    INTRO = "intro"
    CODING = "coding"
    CONCLUSION = "conclusion"

    def get_stage_prompt(self) -> str:
        """
        Load the stage-specific prompt from templates/stages/template_{stage_name}.txt

        Returns:
            str: The stage-specific instructions and questions
        """
        try:
            template_path = f"templates/stages/template_{self.value}"
            return load_template(template_path)
        except FileNotFoundError:
            logger.error(f"Stage template not found for {self.value}")
            # Return default instructions if template not found
            raise ValueError(f"Stage template not found for {self.value}")


class InterviewController:
    def __init__(self, question_manager: QuestionManager):
        self.question_manager = question_manager
        self.room = None
        
        # Properties from former InterviewState
        self.question = None
        self.current_stage = None
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
        self.code_executor = CodeExecutor()
        logger.info(
            f"CodeExecutor initialized with API URL: {DOCKER_API_BASE_URL}")

    def get_file_watcher(self) -> FileWatcher:
        """Get the FileWatcher instance"""
        return self.file_watcher

    def handle_code_update(self, code: str) -> bool:
        """Handle code updates from the frontend"""
        try:
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
        self.current_stage = InterviewStage.INTRO
        self.code_snapshots = {}
        self.start_time = datetime.now()
        self.end_time = datetime.now() + timedelta(minutes=self.question.duration)
        logger.info(
            f"Interview initialized with duration: {self.question.duration} minutes")

    def get_system_prompt(self) -> str:
        return self._generate_stage_prompt()

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
