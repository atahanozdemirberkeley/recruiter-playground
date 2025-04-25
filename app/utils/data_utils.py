import json
import logging
import asyncio
import time
from datetime import datetime
from livekit.rtc import DataPacket
from livekit.agents import llm
from typing import Optional, Callable, Any, Dict
from pathlib import Path
from aiofile import async_open
from components.interview_controller import InterviewController
logger = logging.getLogger(__name__)


class DataUtils:
    def __init__(self, interview_controller: InterviewController, log_file_path="transcriptions.log"):
        self.interview_controller = interview_controller
        self.log_queue = asyncio.Queue()
        self.log_file_path = log_file_path

    async def process_data_packet(self, packet: DataPacket) -> None:
        """Process incoming data packets from the room."""
        self.interview_controller.last_activity_time = time.time()  # Update activity time
        try:
            payload_str = packet.data.decode("utf-8")
            payload = json.loads(payload_str)
            packet_type = payload.get("type")

            if packet_type == "code_update":
                code_text = payload.get("code", "")
                self.interview_controller.file_watcher.write_content(code_text)

            elif packet_type == "run_code":
                test_file_path = self.interview_controller.file_watcher.path_to_watch
                results = await self.interview_controller.run_code(
                    mode="run"
                )
                await self.send_results_to_frontend(results)

            elif packet_type == "submit_code":
                test_file_path = self.interview_controller.file_watcher.path_to_watch
                results = await self.interview_controller.run_code(
                    mode="submit"
                )
                await self.send_results_to_frontend(results)

        except json.JSONDecodeError:
            logger.warning(f"Could not parse as JSON: {packet.data}")
        except Exception as e:
            logger.error(f"Error processing data packet: {e}")

    async def send_results_to_frontend(self, results: Dict) -> None:
        """Send test results back to frontend"""
        self.interview_controller.last_activity_time = time.time()  # Update activity time
        try:
            payload = json.dumps({
                "type": "test_results",
                "data": results
            }).encode('utf-8')

            await self.interview_controller.room.local_participant.publish_data(
                payload,
                topic="test-results"
            )
        except Exception as e:
            logger.error(f"Error sending results to frontend: {e}")

    async def handle_user_speech(self, msg: llm.ChatMessage) -> None:
        """Handle user speech events."""
        # update the interview controller's last activity time
        self.interview_controller.last_activity_time = time.time()
        
        # Take code snapshot
        code_snapshot = self.interview_controller.file_watcher._take_snapshot()
        # Update to access code_snapshots directly on interview_controller
        snapshot_id = str(len(self.interview_controller.code_snapshots))
        self.interview_controller.code_snapshots[snapshot_id] = code_snapshot

        # Log interaction with interview duration
        duration = self.interview_controller.get_interview_time_since_start()
        await self.log_queue.put(
            f"[{duration}] USER:\n{msg.content}\n\n"
            f"CODE:\n{code_snapshot}\n\n"
            f"{'='*80}\n\n"
        )

    async def handle_agent_speech(self, msg: llm.ChatMessage) -> None:
        """Handle agent speech events."""
        # update the interview controller's last activity time
        self.interview_controller.last_activity_time = time.time()
        
        code_snapshot = self.interview_controller.file_watcher._take_snapshot()
        duration = self.interview_controller.get_interview_time_since_start()
        await self.log_queue.put(
            f"[{duration}] AGENT:\n{msg.content}\n\n"
            f"CODE:\n{code_snapshot}\n\n"
            f"{'='*80}\n\n"
        )

    async def write_transcription(self) -> None:
        """Write transcriptions to a log file."""
        async with async_open(self.log_file_path, "w") as f:
            while True:
                try:
                    msg = await self.log_queue.get()
                    if msg is None:
                        break
                    await f.write(msg)
                    await f.flush()
                except Exception as e:
                    logger.error(f"Error writing transcription: {e}")

    async def finish_queue(self, shutdown_reason=None) -> None:
        """Clean up the log queue and wait for write task completion.
        
        Args:
            shutdown_reason: The reason for shutdown (passed by LiveKit callback)
        """
        logger.info(f"Finishing queue, shutdown reason: {shutdown_reason}")
        await self.log_queue.put(None)
        # Wait for any pending writes to complete
        await asyncio.sleep(0.1)  # Small delay to ensure queue processing

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
                self.interview_controller.file_watcher.write_content(question.skeleton_code)
                
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
    
