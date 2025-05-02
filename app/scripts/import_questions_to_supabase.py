#!/usr/bin/env python3
"""
Script to import questions from CSV file to Supabase database.
Make sure to set SUPABASE_URL and SUPABASE_KEY environment variables before running.
"""

from utils.database_manager import DatabaseManager
import os
import sys
import csv
import json
import logging
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Set up logging
logging.basicConfig(level=logging.INFO)
console = Console()

# Path to the CSV file
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'testing', 'create_questions_table.csv')


def parse_csv(csv_path):
    """Parse the CSV file into a list of question dictionaries."""
    questions = []

    try:
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Create a test case structure for each question
                # This is a simple example - real test cases would need proper structure
                test_case = {
                    "visible": True,
                    "description": f"Test for {row['title']}",
                    "input": "example_input",
                    "output": "example_output"
                }

                # Convert the row to a question record
                question = {
                    "id": row["id"],
                    "title": row["title"],
                    "difficulty": row["difficulty"],
                    "category": row["category"],
                    "duration_minutes": int(row["duration_minutes"]),
                    "function_name": row["function_name"],
                    "function_signature": row["function_signature"],
                    "skeleton_code": row["skeleton_code"],
                    "description": row["description"],
                    "solution_code": row["solution_code"],
                    "solution_explanation": row["solution_explanation"],
                    # Store as JSON string
                    "test_cases": json.dumps([test_case]),
                    # Example hints
                    "hints": json.dumps(["Try using a stack or queue", "Consider edge cases"]),
                    "created_at": row.get("created_at", None)
                }
                questions.append(question)

        return questions
    except Exception as e:
        console.print(f"[bold red]Error parsing CSV:[/bold red] {str(e)}")
        return []


def main():
    # Load environment variables
    load_dotenv()

    console.print("[bold green]CSV to Supabase Question Importer[/bold green]")

    # Check for environment variables
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        console.print(
            "[bold red]Error:[/bold red] SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")
        return False

    # Get CSV path (use default or command line argument)
    csv_path = DEFAULT_CSV_PATH
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]

    console.print(f"Importing questions from: [cyan]{csv_path}[/cyan]")

    # Parse CSV
    questions = parse_csv(csv_path)
    if not questions:
        console.print(
            "[bold red]No questions found in CSV or error parsing file.[/bold red]")
        return False

    console.print(f"Found [green]{len(questions)}[/green] questions in CSV.")

    try:
        # Connect to Supabase
        db_manager = DatabaseManager()

        # Import questions with progress bar
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("{task.fields[question]}"),
        ) as progress:
            task = progress.add_task(
                "[cyan]Importing questions...", total=len(questions), question="")

            for question in questions:
                progress.update(task, advance=1, question=question["title"])

                # Check if question already exists
                existing = db_manager.get_question_by_id(question["id"])

                if existing:
                    # Update existing question
                    db_manager.update_question(question["id"], question)
                else:
                    # Insert new question
                    db_manager.supabase.table(
                        'questions').insert(question).execute()

        console.print(
            "[bold green]Success![/bold green] Imported questions to Supabase.")
        return True

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
