from dataclasses import dataclass
from typing import Any, List, Dict, Optional
from pathlib import Path
import json


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
class TestCase:
    """Represents a single test case for a coding question."""
    io_data: TestCaseIO
    visible: bool = True
    description: Optional[str] = None

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
