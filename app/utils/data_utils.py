import json
import logging
import asyncio
from datetime import datetime
from livekit.rtc import DataPacket
from livekit.agents import llm
from typing import Optional, Callable, Any, Dict
from pathlib import Path
from aiofile import async_open

logger = logging.getLogger(__name__)


class DataUtils:
    def __init__(self, interview_controller, agent=None, log_file_path="transcriptions.log"):
        self.interview_controller = interview_controller
        self.agent = agent
        self.log_queue = asyncio.Queue()
        self.log_file_path = log_file_path

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
                logger.info("Running code")
                results = await self.interview_controller.run_code()
                # Send results back to frontend
                await self.send_results_to_frontend(results)

            elif packet_type == "submit_code":
                logger.info("Submitting code")
                results = await self.interview_controller.submit_code()
                # Send results back to frontend
                await self.send_results_to_frontend(results)

        except json.JSONDecodeError:
            logger.warning(f"Could not parse as JSON: {packet.data}")
        except Exception as e:
            logger.error(f"Error processing data packet: {e}")

    async def send_results_to_frontend(self, results: Dict) -> None:
        """Send test results back to frontend"""
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
        if isinstance(msg.content, list):
            msg.content = "\n".join(
                "[image]" if isinstance(x, llm.ChatImage) else x for x in msg
            )

        # Take code snapshot
        code_snapshot = self.interview_controller.file_watcher._take_snapshot()
        self.interview_controller.state.code_snapshots[str(
            len(self.interview_controller.state.code_snapshots))] = code_snapshot

        # Only update agent context if stage changes
        new_stage_prompt = await self.interview_controller.evaluate_and_update_stage(msg.content, code_snapshot)
        if new_stage_prompt and self.agent:
            self.agent.chat_ctx.append(
                role="system",
                text=new_stage_prompt
            )

        # Log interaction with interview duration
        duration = self.interview_controller.get_interview_time_since_start()
        await self.log_queue.put(
            f"[{duration}] USER:\n{msg.content}\n\n"
            f"CODE:\n{code_snapshot}\n\n"
            f"STAGE: {self.interview_controller.state.current_stage.value}\n"
            f"{'='*80}\n\n"
        )

    async def handle_agent_speech(self, msg: llm.ChatMessage) -> None:
        """Handle agent speech events."""
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

    async def finish_queue(self) -> None:
        """Clean up the log queue and wait for write task completion."""
        await self.log_queue.put(None)
        # Wait for any pending writes to complete
        await asyncio.sleep(0.1)  # Small delay to ensure queue processing
