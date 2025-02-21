from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from components.question_manager import QuestionManager, Question
import json
from utils.template_utils import load_template
from livekit.plugins.openai import LLM
from livekit.agents import llm
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InterviewStage(Enum):
    INTRODUCTION = "introduction"
    PROBLEM_PRESENTATION = "problem_presentation"
    CLARIFICATION = "clarification"
    CODING = "coding"
    CODE_REVIEW = "code_review"
    OPTIMIZATION = "optimization"
    CONCLUSION = "conclusion"


@dataclass
class InterviewState:
    question: Question
    current_stage: InterviewStage
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
            model="gpt-4",  # or any other model you prefer
            temperature=0.3  # lower temperature for more consistent stage management
        )

    def initialize_interview(self, question_id: str):
        """Initialize the interview state with the selected question"""
        self.question = self.question_manager.get_question(question_id)
        self.state = InterviewState(
            question=self.question,
            current_stage=InterviewStage.INTRODUCTION,
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
        stage_instructions = {
            InterviewStage.INTRODUCTION: """
    Focus: Make the candidate comfortable and set expectations
    Key Questions:
    - Are you ready to begin the technical interview?
    - Would you like me to explain the interview process?""",

            InterviewStage.PROBLEM_PRESENTATION: """
    Focus: Present the problem clearly and confirm understanding
    Key Questions:
    - Would you like me to clarify any part of the problem?
    - Could you rephrase the problem in your own words?""",

            InterviewStage.CLARIFICATION: """
    Focus: Encourage and address clarifying questions
    Key Questions:
    - What assumptions are you making about the input?
    - Have you considered edge cases?""",

            InterviewStage.CODING: """
    Focus: Observe implementation and understand approach
    Key Questions:
    - Can you walk me through your approach?
    - What data structures are you considering?""",

            InterviewStage.CODE_REVIEW: """
    Focus: Review code structure and implementation choices
    Key Questions:
    - Why did you choose this particular approach?
    - How would this solution scale with larger inputs?""",

            InterviewStage.OPTIMIZATION: """
    Focus: Discuss potential optimizations and tradeoffs
    Key Questions:
    - Are there any optimizations you can think of?
    - What are the space/time complexity tradeoffs?""",

            InterviewStage.CONCLUSION: """
    Focus: Wrap up and gather final insights
    Key Questions:
    - What would you do differently if you had more time?
    - Do you have any questions about the interview?"""
        }

        return f"""Current Interview Stage: {self.state.current_stage.value}
    Stage Goal: {stage_instructions[self.state.current_stage]}
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
