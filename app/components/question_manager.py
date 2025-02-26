from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json
import logging
from utils.template_utils import load_template, save_prompt
from rich.console import Console
from .question_models import Question, TestCase

logger = logging.getLogger("question_manager")
logger.setLevel(logging.INFO)
console = Console()


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
        """Load all questions from JSON files."""
        # Look for question.json files in subdirectories
        for question_dir in self.questions_root.iterdir():
            if question_dir.is_dir():
                question_file = question_dir / "question.json"
                if question_file.exists():
                    try:
                        question = Question.from_json_file(question_file)
                        self.questions[question.id] = question
                        logger.info(
                            f"Loaded question {question.id}: {question.title}")
                    except Exception as e:
                        logger.error(
                            f"Failed to load question from {question_file}: {e}")

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
        formatted_prompt = template.format(
            title=question.title,
            difficulty=question.difficulty,
            category=question.category,
            question=question.description,
            hints=chr(10).join(f"- {hint}" for hint in question.hints),
            solution=question.solution['code']
        )

        save_prompt("question_context", formatted_prompt)
        return formatted_prompt

    def get_solution(self, question_id: str) -> Optional[str]:
        """Get the solution for a specific question (for verification only)."""
        question = self.get_question(question_id)
        return question.solution['code'] if question else None

    def get_test_cases(self, question_id: str, visible_only: bool = True) -> List[TestCase]:
        """
        Get test cases for a specific question.

        Args:
            question_id: The ID of the question
            visible_only: If True, returns only visible test cases
        """
        question = self.get_question(question_id)
        if not question:
            return []
        return question.visible_test_cases if visible_only else question.all_test_cases

    def select_question(self, question_number: int = 1) -> Tuple[str, str]:
        """
        Select the question by its number.

        Args:
            question_number: The index of the question to select (1-based)

        Returns:
            Tuple[str, str]: Question ID and the complete prompt
        """
        if not self.questions:
            raise ValueError("No questions available")

        # Get sorted list of question IDs for consistent ordering
        question_ids = sorted(self.questions.keys())

        # Adjust for 1-based indexing
        idx = question_number - 1
        if idx < 0 or idx >= len(question_ids):
            raise ValueError(
                f"Question number {question_number} is out of range. Available questions: 1-{len(question_ids)}")

        selected_id = question_ids[idx]
        prompt = self.complete_prompt(selected_id)
        return selected_id, prompt

    # TODO: Adapt to implementation
    def validate_solution(self, question_id: str, submitted_code: str) -> Tuple[bool, List[str]]:
        """
        Validate a submitted solution against all test cases.

        Args:
            question_id: The ID of the question
            submitted_code: The submitted solution code

        Returns:
            Tuple[bool, List[str]]: (Success status, List of error messages)
        """
        question = self.get_question(question_id)
        if not question:
            return False, ["Question not found"]

        # Here you would implement the actual validation logic
        # This might involve:
        # 1. Creating a Solution class instance from the submitted code
        # 2. Running all test cases
        # 3. Comparing results with expected outputs

        return True, []  # Placeholder return
