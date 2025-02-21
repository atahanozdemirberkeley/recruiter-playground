from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from components.question_manager import QuestionManager, Question
import json
from utils.template_utils import load_template
from livekit.plugins.openai import LLM
from livekit.agents import llm
from datetime import datetime, timedelta
import asyncio
from livekit.data.data_packet import DataPacket_ReliabilityMode


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
    code_snapshots: Dict[str, str]
    clarifications: List[str]
    insights: List[str]
    start_time: Optional[datetime] = None
    stage_timestamps: Dict[InterviewStage, datetime] = {}
    time_publisher: Optional[asyncio.Queue] = None
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
        question = self.question_manager.get_question(question_id)
        self.state = InterviewState(
            question=question,
            current_stage=InterviewStage.INTRODUCTION,
            code_snapshots={},
            clarifications=[],
            insights=[]
        )

    def get_system_prompt(self) -> str:
        return self._generate_stage_prompt()

    def evaluate_stage_transition(self, user_message: str, code_snapshot: str) -> str:
        """Generate a prompt for the LLM to evaluate stage transition"""
        template = load_template('template_stage_evaluation')
        return template.format(
            current_stage=self.state.current_stage.value,
            user_message=user_message,
            code_status='Has code' if code_snapshot else 'No code',
            clarifications_count=len(self.state.clarifications),
            insights_count=len(self.state.insights)
        )

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
        evaluation_prompt = self.evaluate_stage_transition(
            user_message, code_snapshot)

        # Create chat context for the evaluation
        chat_ctx = llm.ChatContext().append(
            role="system",
            text=evaluation_prompt
        )

        # Use chat method instead of generate
        async with self.llm.chat(chat_ctx=chat_ctx) as response:
            llm_response = await response.text()

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

    def get_interview_duration(self, formatted: bool = False) -> Union[int, str]:
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
            if self.state.interview_end_time:
                time_left = max(
                    0, (self.state.interview_end_time - datetime.now()).total_seconds())

                # Create the message payload
                payload = json.dumps({
                    "timeLeft": time_left
                }).encode('utf-8')

                # Publish using the data channel API
                await room.local_participant.publish_data(
                    payload,
                    topic="interview-time",
                    reliability_mode=DataPacket_ReliabilityMode.RELIABLE
                )

            await asyncio.sleep(1)  # Update every second

    async def start_interview(self, duration_minutes: int):
        """Start the interview with a specified duration"""
        self.state.start_time = datetime.now()
        self.state.interview_end_time = self.state.start_time + \
            timedelta(minutes=duration_minutes)

        # Start time updates when interview starts
        asyncio.create_task(self.start_time_updates(self.room))
