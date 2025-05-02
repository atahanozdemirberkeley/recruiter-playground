#!/usr/bin/env python3
"""
Test script to verify Supabase connection and question loading.
Make sure to set SUPABASE_URL and SUPABASE_KEY environment variables before running.
"""

from utils.database_manager import DatabaseManager
from components.question_manager import QuestionManager
import os
import sys
import logging
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Set up logging
logging.basicConfig(level=logging.INFO)
console = Console()


def main():
    # Load environment variables
    load_dotenv()

    console.print("[bold green]Testing Supabase connection...[/bold green]")

    # Check for environment variables
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        console.print(
            "[bold red]Error:[/bold red] SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")
        return False

    try:
        # Test direct database connection
        console.print("Testing database manager...")
        db_manager = DatabaseManager()
        questions_data = db_manager.get_questions()
        console.print(
            f"[green]✓[/green] Connected to Supabase successfully. Found {len(questions_data)} questions.")

        # Test question manager integration
        console.print("\nTesting QuestionManager integration...")
        question_manager = QuestionManager()

        # Display loaded questions in a table
        table = Table(title="Loaded Questions")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Difficulty", style="magenta")
        table.add_column("Category", style="yellow")

        for question_id, question in question_manager.questions.items():
            table.add_row(
                question_id,
                question.title,
                question.difficulty,
                question.category
            )

        console.print(table)
        console.print(
            f"\n[bold green]Success![/bold green] Loaded {len(question_manager.questions)} questions from Supabase.")
        return True

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
