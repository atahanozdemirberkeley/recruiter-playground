import json
import logging
import asyncio
import os
from datetime import datetime
from livekit.rtc import DataPacket
from typing import Optional, Dict
from pathlib import Path
from aiofile import async_open
from components.interview_controller import InterviewController
from components.agents.evaluation_agent import EvaluationAgent
from components.agents.coding_agent import CodingAgent

logger = logging.getLogger(__name__)


class DataUtils:
    def __init__(self, interview_controller: InterviewController):
        self.interview_controller = interview_controller
        self.log_queue = asyncio.Queue()
        self.last_code_snapshot = ""  # Track the last code snapshot
        self.current_transcription_file = None  # Track current transcription file

    async def process_data_packet(self, packet: DataPacket) -> None:
        """Process incoming data packets from the room."""
        try:
            payload_str = packet.data.decode("utf-8")
            payload = json.loads(payload_str)
            packet_type = payload.get("type")

            if packet_type == "code_update":
                code_text = payload.get("code", "")
                self.interview_controller.file_watcher.write_content(code_text)

            elif packet_type == "run_code":

                if isinstance(self.interview_controller.current_agent, CodingAgent):

                    results = await self.interview_controller.run_code(
                        mode="run"
                    )

                    #
                    from rich import print as rich_print
                    rich_print("[bold green]results[/bold green]", results)
                    #

                    await self.send_results_to_frontend(results, state="run")

            elif packet_type == "submit_code":

                if isinstance(self.interview_controller.current_agent, CodingAgent):
                    results = await self.interview_controller.run_code(
                        mode="submit"
                    )
                    await self.send_results_to_frontend(results, state="submit")

        except json.JSONDecodeError:
            logger.warning(f"Could not parse as JSON: {packet.data}")
        except Exception as e:
            logger.error(f"Error processing data packet: {e}")

    async def send_results_to_frontend(self, results: Dict, state: str = 'run') -> None:
        """Send test results back to frontend

        Args:
            results: The test results data
            state: The state of the test results - either 'run' or 'submit'
        """
        try:
            payload = json.dumps({
                "type": "test_results",
                "data": {
                    **results,
                    "state": state
                }
            }).encode('utf-8')

            await self.interview_controller.room.local_participant.publish_data(
                payload,
                topic="test-results"
            )
        except Exception as e:
            logger.error(f"Error sending results to frontend: {e}")

    async def handle_user_speech(self, msg: str) -> None:
        """Handle user speech events."""
        # Take code snapshot
        code_snapshot = self.interview_controller.file_watcher._take_snapshot()

        # Only include code if it's changed
        code_section = ""
        has_code_changed = code_snapshot != self.last_code_snapshot

        # Only save to code_snapshots if different from last snapshot
        if has_code_changed:
            snapshot_id = str(len(self.interview_controller.code_snapshots))
            self.interview_controller.code_snapshots[snapshot_id] = code_snapshot
            self.last_code_snapshot = code_snapshot  # Update last snapshot
            code_section = f"CODE:\n{code_snapshot}\n\n"

        # Log interaction with interview duration
        duration = self.interview_controller.get_interview_time_since_start()

        await self.log_queue.put(
            f"[{duration}] USER:\n{msg}\n\n"
            f"{code_section}"
            f"{'='*80}\n\n"
        )

    async def handle_agent_speech(self, msg: str) -> None:
        """Handle agent speech events."""
        duration = self.interview_controller.get_interview_time_since_start()
        await self.log_queue.put(
            f"[{duration}] AGENT:\n{msg}\n\n"
            f"{'='*80}\n\n"
        )

    async def write_transcription(self) -> None:
        """Write transcriptions to a timestamped log file in the transcriptions directory."""
        # Create transcriptions directory if it doesn't exist
        transcriptions_dir = Path("transcriptions")
        if not transcriptions_dir.exists():
            transcriptions_dir.mkdir(parents=True)
            logger.info(f"Created directory: {transcriptions_dir}")

        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_transcription_file = transcriptions_dir / \
            f"{timestamp}_transcription.log"

        async with async_open(self.current_transcription_file, "w") as f:
            while True:
                try:
                    msg = await self.log_queue.get()
                    if msg is None:
                        break
                    await f.write(msg)
                    await f.flush()
                except Exception as e:
                    logger.error(f"Error writing transcription: {e}")

    async def send_question_to_frontend(self) -> None:
        """Send question description and skeleton code to the frontend code editor."""
        try:
            question = self.interview_controller.question
            if not question:
                logger.error("No question available to send to frontend")
                return

            payload = json.dumps({
                "type": "question_data",
                "data": {
                    "description": question.description,
                    "skeleton_code": question.skeleton_code
                }
            }).encode('utf-8')

            await self.interview_controller.room.local_participant.publish_data(
                payload,
                topic="question-data"
            )
            logger.info("Question data sent to frontend")

            # Update the file watcher with skeleton code if available
            if hasattr(question, 'skeleton_code') and question.skeleton_code:
                self.interview_controller.file_watcher.write_content(
                    question.skeleton_code)

        except Exception as e:
            logger.error(f"Error sending question to frontend: {e}")

    async def reset_code_editor(self) -> None:
        """
        Reset the code editor and interview state.
        Clears the editor and resets timer.
        """
        try:
            # Reset the code editor to empty (will show placeholder)
            code_payload = json.dumps({
                "type": "question_data",
                "data": {
                    "description": "",
                    "skeleton_code": ""
                }
            }).encode('utf-8')

            await self.interview_controller.room.local_participant.publish_data(
                code_payload,
                topic="question-data"
            )

            # Also clear the file watcher
            self.interview_controller.file_watcher.write_content("")

            # Reset interview timer
            if self.interview_controller.question:
                duration_minutes = self.interview_controller.question.duration
                await self.interview_controller.start_interview_timer(duration_minutes)

                # Notify frontend about reset
                payload = json.dumps({
                    "type": "interview_reset",
                    "data": {
                        "questionId": self.interview_controller.question.id,
                        "questionTitle": self.interview_controller.question.title,
                        "durationMinutes": duration_minutes,
                        "timestamp": datetime.now().isoformat()
                    }
                }).encode('utf-8')

                await self.interview_controller.room.local_participant.publish_data(
                    payload,
                    topic="interview-status"
                )

                # Clear transcription logs if needed
                self.log_queue = asyncio.Queue()

                logger.info("Code editor and interview state reset")
            else:
                logger.error("Cannot reset code editor: No question available")

        except Exception as e:
            logger.error(f"Error resetting code editor: {e}")

    async def generate_candidate_evaluation(self, chat_ctx: Optional[list] = None, model: str = "gpt-4") -> str:
        """
        Generate a comprehensive evaluation of the candidate based on the interview.

        Args:
            chat_ctx: Optional chat context to use instead of the transcription log
            model: LLM model to use for evaluation (default: gpt-4)

        Returns:
            Raw evaluation text from the LLM
        """
        try:
            # Ensure all pending transcription entries are written
            if self.log_queue.qsize() > 0:
                logger.info(
                    f"Waiting for {self.log_queue.qsize()} pending transcription entries to be written")
                await asyncio.sleep(1)  # Brief delay to allow queue processing

            if not self.current_transcription_file:
                logger.error("No transcription file available for evaluation")
                return "ERROR: No transcription file available for evaluation"

            # Initialize evaluation agent with specified model
            evaluator = EvaluationAgent(transcription_path=str(
                self.current_transcription_file), model=model)

            # Generate evaluation (raw text)
            evaluation_text = await evaluator.evaluate_candidate(chat_ctx)

            # Save evaluation to a timestamped file
            await self._save_evaluation_text(evaluation_text)

            return evaluation_text
        except Exception as e:
            logger.error(f"Error generating candidate evaluation: {e}")
            return f"ERROR: Failed to generate evaluation: {str(e)}"

    async def _save_evaluation_text(self, evaluation_text: str) -> None:
        """
        Save raw evaluation text to a timestamped file in the eval_results directory.

        Args:
            evaluation_text: The raw evaluation text to save
        """
        try:
            # Create eval_results directory if it doesn't exist
            eval_dir = Path("eval_results")
            if not eval_dir.exists():
                eval_dir.mkdir(parents=True)
                logger.info(f"Created directory: {eval_dir}")

            # Generate timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Get candidate info from interview controller if available
            candidate_name = "candidate"
            if self.interview_controller and self.interview_controller.question:
                question_id = self.interview_controller.question.id
                candidate_name = f"candidate_{question_id}"

            # Create filename with timestamp and candidate name
            result_filename = f"{timestamp}_{candidate_name}_evaluation.txt"
            result_path = eval_dir / result_filename

            # Save evaluation text
            with open(result_path, 'w') as f:
                f.write(evaluation_text)

            logger.info(f"Evaluation text saved to: {result_path}")

        except Exception as e:
            logger.error(f"Error saving evaluation text: {e}")

# Utility functions outside the DataUtils class


async def evaluate_from_file(file_path: str, model: str = "gpt-4", output_dir: str = "eval_results") -> str:
    """
    Utility function to evaluate a candidate directly from a transcription file.
    Saves the raw LLM response to a text file and returns it.

    Args:
        file_path: Path to the transcription log file
        model: LLM model to use for evaluation (supports "gpt-4", "gpt-4o", "gpt-3.5-turbo", etc.)
        output_dir: Directory to save the evaluation text file

    Returns:
        Raw evaluation text from the LLM
    """
    try:
        # Initialize evaluation agent
        evaluator = EvaluationAgent(transcription_path=file_path, model=model)

        # Generate evaluation (raw text)
        evaluation_text = await evaluator.evaluate_candidate()

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True)
            logger.info(f"Created directory: {output_path}")

        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Extract transcription timestamp from file path
        log_filename = os.path.basename(file_path)
        transcription_timestamp = log_filename.split(
            '_')[0] if '_' in log_filename else "unknown"

        # Create filename with both timestamps
        result_filename = f"{timestamp}_{transcription_timestamp}_evaluation.txt"
        result_path = output_path / result_filename

        # Save raw evaluation text
        with open(result_path, 'w') as f:
            f.write(evaluation_text)

        logger.info(f"Evaluation results saved to: {result_path}")

        return evaluation_text
    except Exception as e:
        logger.error(f"Error evaluating from file: {e}")
        return f"ERROR: Failed to evaluate: {str(e)}"
