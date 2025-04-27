import logging
import os
from pathlib import Path
from typing import Optional, List
from livekit.agents import llm, ChatContext
from livekit.plugins import openai
from utils.template_utils import load_template
from components.question_manager import QuestionManager

logger = logging.getLogger(__name__)


class EvaluationAgent:
    """
    An agent that evaluates candidate performance in coding interviews
    based on transcription data and code snapshots.
    """

    def __init__(self, transcription_path: str = "transcriptions.log", model: str = "gpt-4"):
        """
        Initialize the evaluation agent with the path to transcription data.

        Args:
            transcription_path: Path to the transcription log file
            model: The LLM model to use for evaluation
        """
        self.transcription_path = transcription_path
        self.model = model

    async def evaluate_candidate(self, chat_ctx: Optional[List[llm.ChatMessage]] = None) -> str:
        """
        Evaluate a candidate based on either the chat context or the transcription log.

        Args:
            chat_ctx: Optional list of chat messages to analyze instead of log file

        Returns:
            Raw evaluation text from the LLM
        """
        print("Evaluating candidate")
        # Read transcription data either from chat_ctx or log file
        if chat_ctx:
            transcript_data = self._parse_chat_context(chat_ctx)
        else:
            transcript_data = await self._read_transcription_file()

        if not transcript_data:
            logger.error("No transcript data available for evaluation")
            return "ERROR: No transcript data available for evaluation"

        # Generate the evaluation using LLM and return raw text
        return await self._generate_evaluation(transcript_data)

    def _parse_chat_context(self, chat_ctx: List[llm.ChatMessage]) -> str:
        """
        Parse chat context into a formatted transcript for evaluation.

        Args:
            chat_ctx: List of chat messages

        Returns:
            Formatted transcript string
        """
        transcript = ""
        for msg in chat_ctx:
            role = "USER" if msg.role == "user" else "AGENT"
            transcript += f"[{role}]:\n{msg.content}\n\n"

        return transcript

    async def _read_transcription_file(self) -> Optional[str]:
        """
        Read and parse the transcription log file.

        Returns:
            Formatted transcript string or None if file doesn't exist
        """
        try:
            transcript_path = Path(self.transcription_path)
            if not transcript_path.exists():
                logger.error(
                    f"Transcription file not found: {self.transcription_path}")
                return None

            with open(transcript_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading transcription file: {e}")
            return None

    async def _generate_evaluation(self, transcript_data: str) -> str:
        """
        Generate an evaluation of the candidate using LLM.

        Args:
            transcript_data: Formatted transcript string

        Returns:
            Raw LLM response as a string
        """
        # Load the evaluation template and format it with the transcript data
        template = load_template("template_evaluation_agent.txt")
        question_manager = QuestionManager()
        question_prompt = question_manager.get_question_prompt(
            "valid_paranthesis")
        prompt = template.format(
            transcript_data=transcript_data, question=question_prompt)

        try:
            # Use the OpenAI plugin directly
            llm_instance = openai.LLM(model=self.model)

            # Create a chat context with the system prompt
            chat_ctx = ChatContext()
            chat_ctx.add_message(role="system", content=prompt)

            # Stream the response
            full_response = ""
            async with llm_instance.chat(chat_ctx=chat_ctx) as stream:
                async for chunk in stream:
                    if chunk.delta and chunk.delta.content:
                        full_response += chunk.delta.content

            return full_response
        except Exception as e:
            logger.error(f"Error generating evaluation: {e}")
            return f"ERROR: Failed to generate evaluation: {str(e)}"
