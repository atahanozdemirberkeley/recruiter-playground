from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime
import uuid


@dataclass
class TestCaseIO:
    """Represents the input/output structure for a test case."""
    args: List[Any]  # List of arguments for the function
    expected: Any    # Expected return value

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestCaseIO':
        """Creates a TestCaseIO instance from a dictionary."""
        # Handle named parameters (input_x) or single/list input
        if any(k.startswith('input_') for k in data.keys()):
            args = [data[k]
                    for k in sorted(data.keys()) if k.startswith('input_')]
        else:
            args = [data['input']] if not isinstance(
                data['input'], list) else data['input']

        return cls(args=args, expected=data['output'])


@dataclass
class TestCaseResult:
    """Represents the result of a test case execution."""
    test_case_id: str  # Reference to the parent TestCase
    success: bool = False
    actual_output: Any = None
    error_message: Optional[str] = None


@dataclass
class TestCase:
    """Represents a single test case for a coding question."""
    io_data: TestCaseIO
    visible: bool = True
    description: Optional[str] = None
    id: str = field(default_factory=lambda: str(
        uuid.uuid4()))  # Unique identifier
    results: List[TestCaseResult] = field(
        default_factory=list)  # Store multiple results

    def add_result(self, output: Any, success: bool, error: Optional[str] = None) -> TestCaseResult:
        """Add a new execution result."""
        result = TestCaseResult(
            test_case_id=self.id,
            success=success,
            actual_output=output,
            error_message=error
        )
        self.results.append(result)
        return result

    def get_latest_result(self) -> Optional[TestCaseResult]:
        """Get the most recent execution result."""
        return self.results[-1] if self.results else None

    def get_all_results(self) -> List[TestCaseResult]:
        """Get all execution results."""
        return self.results

    def clear_results(self) -> None:
        """Clear all execution results."""
        self.results = []

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestCase':
        return cls(
            io_data=TestCaseIO.from_dict(data),
            visible=data.get('visible', True),
            description=data.get('description')
        )


@dataclass
class Question:
    """Represents a coding interview question with its metadata and content."""
    id: str
    title: str
    difficulty: str
    category: str
    description: str
    solution: Dict[str, str]  # Contains both code and explanation
    visible_test_cases: List[TestCase]
    all_test_cases: List[TestCase]
    hints: List[str]
    duration: int
    function_name: str
    function_signature: str
    skeleton_code: str
    prompt: Optional[str] = None

    @classmethod
    def from_json_file(cls, question_file: Path) -> 'Question':
        """Creates a Question instance from a JSON file."""
        try:
            with open(question_file) as f:
                data = json.load(f)

            # Convert test cases to TestCase objects
            test_cases = [TestCase.from_dict(tc) for tc in data['test_cases']]
            visible_tests = [tc for tc in test_cases if tc.visible]

            return cls(
                id=data['metadata']['id'],
                title=data['metadata']['title'],
                difficulty=data['metadata']['difficulty'],
                category=data['metadata']['category'],
                description=data['description'],
                solution={
                    'code': data['solution']['code'],
                    'explanation': data['solution']['explanation']
                },
                visible_test_cases=visible_tests,
                all_test_cases=test_cases,
                hints=data['metadata'].get('hints', []),
                duration=data['metadata'].get('duration', 60),
                function_name=data['metadata']['function_name'],
                function_signature=data['metadata']['function_signature'],
                skeleton_code=data['metadata'].get('skeleton_code', '')
            )

        except Exception as e:
            raise Exception(
                f"Error loading question from {question_file}: {e}")

    @classmethod
    def from_dict(cls, db_record: Dict[str, Any]) -> 'Question':
        """
        Creates a Question instance from a Supabase database record.

        Args:
            db_record: Dictionary containing the database record

        Returns:
            Question object
        """
        try:
            # Parse test cases from JSON if stored as string
            test_cases_data = db_record.get('test_cases', [])
            if isinstance(test_cases_data, str):
                test_cases_data = json.loads(test_cases_data)

            # Convert test cases to TestCase objects
            test_cases = [TestCase.from_dict(tc) for tc in test_cases_data]
            visible_tests = [tc for tc in test_cases if tc.visible]

            # Parse hints from JSON if stored as string
            hints = db_record.get('hints', [])
            if isinstance(hints, str):
                hints = json.loads(hints)

            # Create solution dictionary
            solution = {
                'code': db_record.get('solution_code', ''),
                'explanation': db_record.get('solution_explanation', '')
            }

            return cls(
                id=db_record['id'],
                title=db_record['title'],
                difficulty=db_record['difficulty'],
                category=db_record['category'],
                description=db_record['description'],
                solution=solution,
                visible_test_cases=visible_tests,
                all_test_cases=test_cases,
                hints=hints if isinstance(hints, list) else [],
                duration=db_record.get('duration_minutes', 60),
                function_name=db_record['function_name'],
                function_signature=db_record['function_signature'],
                skeleton_code=db_record.get('skeleton_code', '')
            )
        except Exception as e:
            raise Exception(
                f"Error converting database record to Question: {e}")
