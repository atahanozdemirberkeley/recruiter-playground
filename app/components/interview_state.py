from enum import Enum
from dataclasses import dataclass, field
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEST_FILE_PATH = "testing/test.py"


class InterviewStage(Enum):
    INTRODUCTION = "introduction"
    PROBLEM_PRESENTATION = "problem_presentation"
    CLARIFICATION = "clarification"
    CODING = "coding"
    CODE_REVIEW = "code_review"
    OPTIMIZATION = "optimization"
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
            return """
    Focus: Continue with the interview process
    """


@dataclass
class InterviewState:
    question: Question
    current_stage: InterviewStage
    file_watcher: Optional[FileWatcher] = None  # Just store the reference
    # {id: {"code": str, "timestamp": int}}
    code_snapshots: Dict[str, Dict[str, Union[str, int]]
                         ] = field(default_factory=dict)
    clarifications: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    stage_timestamps: Dict[InterviewStage,
                           datetime] = field(default_factory=dict)
    interview_end_time: Optional[datetime] = None


class InterviewController:
    def __init__(self, question_manager: QuestionManager):
        self.question_manager = question_manager
        self.state = None
        self._last_stage_prompt = None
        self.llm = LLM(
            model="gpt-4",
            temperature=0.3
        )
        # Initialize FileWatcher here instead
        self.file_watcher = FileWatcher(TEST_FILE_PATH)
        logger.info(f"FileWatcher initialized for {TEST_FILE_PATH}")
        self.code_executor = CodeExecutor()

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

    def handle_data_message(self, data: bytes, user_id: str, topic: Optional[str] = None):
        """Handle incoming data channel messages"""
        try:
            decoded = json.loads(data.decode('utf-8'))

            # Handle code updates from the frontend
            if decoded.get('type') == 'code_update':
                code = decoded.get('code', '')
                self.handle_code_update(code)

        except Exception as e:
            logger.error(f"Error handling data channel message: {e}")

    def initialize_interview(self, question_id: str):
        """Initialize the interview state with the selected question"""
        self.question = self.question_manager.get_question(question_id)
        self.state = InterviewState(
            question=self.question,
            current_stage=InterviewStage.INTRODUCTION,
            file_watcher=self.file_watcher,  # Pass the reference
            code_snapshots={},
            clarifications=[],
            insights=[],
            start_time=datetime.now(),
            interview_end_time=datetime.now() + timedelta(minutes=self.question.duration)
        )
        logger.info(
            f"Interview initialized with duration: {self.question.duration} minutes")

    def get_system_prompt(self) -> str:
        return self._generate_stage_prompt()

    def update_stage(self, llm_response: dict) -> None:
        """Update interview state based on LLM's evaluation"""
        if llm_response["stage_action"] == "NEXT":
            current_idx = list(InterviewStage).index(self.state.current_stage)
            self.state.current_stage = list(InterviewStage)[min(
                current_idx + 1, len(InterviewStage) - 1)]

        # TODO: Explore this more in depth
        # Record any insights or clarifications
        # if llm_response["record"]["type"] == "insight":
        #     self.state.insights.append(llm_response["record"]["content"])
        # elif llm_response["record"]["type"] == "clarification":
        #     self.state.clarifications.append(llm_response["record"]["content"])

    def _generate_stage_prompt(self) -> str:
        return f"""Current Interview Stage: {self.state.current_stage.value}
        Stage Goal: {self.state.current_stage.get_stage_prompt()}
        Question: {self.state.question.title}
        Difficulty: {self.state.question.difficulty}
        Code Snapshots: {len(self.state.code_snapshots)}
        Clarifications: {len(self.state.clarifications)}
        Insights: {len(self.state.insights)}
        """

    async def evaluate_and_update_stage(self, user_message: str, code_snapshot: str) -> Optional[str]:
        """Returns new stage prompt only if stage changed, None otherwise"""

        template = load_template('template_stage_evaluation')
        evaluation_prompt = template.format(
            current_stage=self.state.current_stage.value,
            user_message=user_message,
            code_status='Has code' if code_snapshot else 'No code',
            clarifications_count=len(self.state.clarifications),
            insights_count=len(self.state.insights)
        )

        save_prompt("stage_evaluation", evaluation_prompt)

        # Create chat context for the evaluation
        chat_ctx = llm.ChatContext().append(
            role="system",
            text=evaluation_prompt
        )

        # Use chat method instead of generate
        async with self.llm.chat(chat_ctx=chat_ctx) as response:
            chunks = []
            async for chunk in response:
                chunks.append(str(chunk))
            llm_response = "".join(chunks)

        try:
            response = json.loads(llm_response)
            if response["stage_action"] == "NEXT":
                self.update_stage(response)
                new_prompt = self._generate_stage_prompt()
                self._last_stage_prompt = new_prompt
                return new_prompt

            # # Record insights/clarifications even if we stay in same stage
            # if response["record"]["type"] in ["insight", "clarification"]:
            #     self.update_stage(response)

            return None

        except json.JSONDecodeError:
            return None

    def get_interview_time_since_start(self, formatted: bool = False) -> Union[int, str]:
        """
        Returns the current interview duration.
        Args:
            formatted (bool): If True, returns time in 'HH:MM:SS' format. If False, returns seconds.
        """
        if not self.state or not self.state.start_time:
            return "00:00:00" if formatted else 0

        seconds = int((datetime.now() - self.state.start_time).total_seconds())

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

    def get_stage_duration(self, stage: InterviewStage, formatted: bool = False) -> Union[int, str]:
        """
        Returns the duration of a specific stage.
        Args:
            stage (InterviewStage): The stage to get duration for
            formatted (bool): If True, returns time in 'HH:MM:SS' format. If False, returns seconds.
        """
        if stage not in self.state.stage_timestamps:
            return "00:00:00" if formatted else 0

        stage_start = self.state.stage_timestamps[stage]
        if stage == self.state.current_stage:
            stage_end = datetime.now()
        else:
            next_stages = list(InterviewStage)[list(
                InterviewStage).index(stage) + 1:]
            for next_stage in next_stages:
                if next_stage in self.state.stage_timestamps:
                    stage_end = self.state.stage_timestamps[next_stage]
                    break
            else:
                stage_end = datetime.now()

        seconds = int((stage_end - stage_start).total_seconds())

        if formatted:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            remaining_seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

        return seconds

    async def start_time_updates(self, room):
        """Start publishing time updates to the room"""
        while True:
            if self.state and self.state.interview_end_time:
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
        self.state.start_time = datetime.now()
        self.state.interview_end_time = self.state.start_time + \
            timedelta(minutes=duration_minutes)

        logger.info(
            f"Interview end time set to: {self.state.interview_end_time}")

        # Start time updates when interview starts
        asyncio.create_task(self.start_time_updates(self.room))

    def add_code_snapshot(self, code: str) -> str:
        """
        Adds a new code snapshot with timestamp relative to interview start
        Returns: snapshot_id
        """
        snapshot_id = f"snapshot_{self.snapshot_counter}"
        self.snapshot_counter += 1

        self.state.code_snapshots[snapshot_id] = {
            "code": code,
            "timestamp": self.get_interview_duration(formatted=False)
        }
        return snapshot_id

    async def run_code(self, mode: str = "run") -> Dict:
        """
        Run the current code against test cases

        Args:
            mode: Either "run" (visible tests only) or "submit" (all tests)
        """
        try:
            logger.info(f"Starting code execution in {mode} mode")

            # Get test file path from FileWatcher
            test_file_path = self.file_watcher.path_to_watch
            logger.info(f"Using test file: {test_file_path}")

            # Select test cases based on mode
            test_cases = (
                self.state.question.visible_test_cases if mode == "run"
                else self.state.question.all_test_cases
            )
            logger.info(
                f"Selected {len(test_cases)} test cases for {mode} mode"
                f" ({len(self.state.question.all_test_cases)} total cases available)"
            )

            # Execute tests
            logger.info("Executing tests...")
            success, results, console_output = self.code_executor.execute_tests(
                test_file_path,
                test_cases
            )

            logger.info(
                f"Test execution completed - Success: {success}, "
                f"Results count: {len(results) if isinstance(results, dict) else 0}"
            )

            response = {
                "success": success,
                "results": results,
                "console_output": console_output,
                "mode": mode
            }
            logger.debug(f"Full response: {response}")
            return response

        except Exception as e:
            logger.error(
                f"Error running code in {mode} mode: {e}", exc_info=True)
            return {"success": False, "error": str(e), "mode": mode}

    async def submit_code(self) -> Dict:
        """Submit the code for final evaluation"""
        return await self.run_code(mode="submit")

    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'code_executor'):
            self.code_executor.cleanup()
