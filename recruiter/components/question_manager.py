from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import yaml
import logging
from utils.template_utils import load_template
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
import sys

logger = logging.getLogger("question_manager")
logger.setLevel(logging.INFO)
console = Console()


@dataclass
class Question:
    """Represents a coding interview question with its metadata and content."""
    id: str
    title: str
    difficulty: str
    category: str
    question: str
    solution: str
    test_cases: List[Dict]
    hints: List[str]
    # in minutes
    duration: int

    @classmethod
    def from_directory(cls, question_dir: Path) -> 'Question':
        """
        Creates a Question instance from a directory containing question files.

        Expected directory structure:
        question_id/
        ├── metadata.yaml
        ├── question.txt
        ├── solution.txt
        └── test_cases.yaml
        """
        try:
            # Read metadata
            with open(question_dir / "metadata.yaml") as f:
                metadata = yaml.safe_load(f)

            # Read question text
            with open(question_dir / "question.txt") as f:
                question = f.read()

            # Read solution
            with open(question_dir / "solution.txt") as f:
                solution = f.read()

            # Read test cases if they exist
            test_cases = []
            test_cases_path = question_dir / "test_cases.yaml"
            if test_cases_path.exists():
                with open(test_cases_path) as f:
                    test_cases = yaml.safe_load(f)

            return cls(
                id=metadata['id'],
                title=metadata['title'],
                difficulty=metadata['difficulty'],
                category=metadata['category'],
                question=question,
                solution=solution,
                test_cases=test_cases,
                hints=metadata.get('hints', []),
                duration=metadata.get('duration', 0)
            )

        except Exception as e:
            logger.error(f"Error loading question from {question_dir}: {e}")
            raise


class QuestionManager:
    """Manages a collection of coding interview questions."""

    def __init__(self, questions_root: Path):
        """
        Initialize QuestionManager with the root directory containing all questions.

        Args:
            questions_root (Path): Path to the root directory containing question subdirectories
        """
        self.questions_root = Path(questions_root)
        self.questions: Dict[str, Question] = {}
        self._load_questions()

    def _load_questions(self):
        """Load all questions from the questions directory."""
        for question_dir in self.questions_root.iterdir():
            if question_dir.is_dir():
                try:
                    question = Question.from_directory(question_dir)
                    self.questions[question.id] = question
                    # logger.info(
                    #     f"Loaded question {question.id}: {question.title}")
                except Exception as e:
                    logger.error(
                        f"Failed to load question from {question_dir}: {e}")

    def get_question(self, question_id: str) -> Optional[Question]:
        """Get a question by its ID."""
        return self.questions.get(question_id)

    def get_questions_by_category(self, category: str) -> List[Question]:
        """Get all questions in a specific category."""
        return [q for q in self.questions.values() if q.category == category]

    def get_questions_by_difficulty(self, difficulty: str) -> List[Question]:
        """Get all questions of a specific difficulty level."""
        return [q for q in self.questions.values() if q.difficulty == difficulty]

    def complete_prompt(self, question_id: str) -> str:
        """
        Provide the information to complete the agent prompt for the question
        """
        question = self.get_question(question_id)
        if not question:
            raise ValueError(f"Question {question_id} not found")

        template = load_template('template_question_context')
        return template.format(
            title=question.title,
            difficulty=question.difficulty,
            category=question.category,
            question=question.question,
            duration=question.duration,
            hints=chr(10).join(f"- {hint}" for hint in question.hints),
            solution=question.solution
        )

    def get_solution(self, question_id: str) -> Optional[str]:
        """Get the solution for a specific question (for verification only)."""
        question = self.get_question(question_id)
        return question.solution_code if question else None

    def select_question(self, question_number: int = 1) -> Tuple[str, str]:
        """
        Select the question by its number.

        Args:
            question_number: The index of the question to select

        Returns:
            Tuple[str, str]: Question ID and the complete prompt
        """
        if not self.questions:
            raise ValueError("No questions available")

        # Get list of question IDs
        question_ids = list(self.questions.keys())

        # Validate index
        if question_number < 0 or question_number >= len(question_ids):
            raise ValueError(
                f"Question number {question_number} is out of range. Available questions: 1-{len(question_ids)}")

        selected_id = question_ids[question_number]
        prompt = self.complete_prompt(selected_id)
        return selected_id, prompt
