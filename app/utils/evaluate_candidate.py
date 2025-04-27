#!/usr/bin/env python3
"""
CLI tool to manually trigger candidate evaluation from transcription logs.
Usage: python -m app.utils.evaluate_candidate [options]

Examples:
    # Evaluate with default GPT-4 model
    python -m app.utils.evaluate_candidate -f app/transcriptions.log

    # Evaluate with GPT-4o model
    python -m app.utils.evaluate_candidate -f app/transcriptions.log -m gpt-4o
    
    # Evaluate and save to a custom file
    python -m app.utils.evaluate_candidate -f app/transcriptions.log -o my_evaluation.txt
    
    # Evaluate and save to a custom directory
    python -m app.utils.evaluate_candidate -f app/transcriptions.log -d custom_folder
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.utils.data_utils import evaluate_from_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Evaluate a candidate from transcription logs")
    parser.add_argument(
        "--log-file", 
        "-f", 
        default="app/transcriptions.log", 
        help="Path to the transcription log file"
    )
    parser.add_argument(
        "--output", 
        "-o", 
        help="Path to save evaluation results to a custom file (optional)"
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4",
        help="LLM model to use for evaluation (e.g., gpt-4, gpt-4o, gpt-3.5-turbo)"
    )
    parser.add_argument(
        "--dir",
        "-d",
        default="eval_results",
        help="Directory to save the evaluation results (default: eval_results)"
    )
    
    args = parser.parse_args()
    
    # Check if log file exists
    if not os.path.exists(args.log_file):
        logger.error(f"Transcription file not found: {args.log_file}")
        return 1
        
    logger.info(f"Evaluating candidate from log file: {args.log_file} using model: {args.model}")
    
    # Generate evaluation using the utility function
    evaluation_text = await evaluate_from_file(
        file_path=args.log_file, 
        model=args.model,
        output_dir=args.dir
    )
    
    # Print the raw evaluation
    print("\n" + "=" * 80)
    print(evaluation_text)
    print("=" * 80)
    
    # Save to custom file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(evaluation_text)
        logger.info(f"Evaluation results also saved to: {args.output}")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 