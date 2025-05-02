import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("database_manager")
logger.setLevel(logging.INFO)


class DatabaseManager:
    """Manages database operations for the application using Supabase."""

    def __init__(self):
        """Initialize the Supabase client."""
        # Get credentials from environment variables
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "Supabase URL and key must be provided in environment variables")

        # Initialize Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")

    def get_questions(self) -> List[Dict[str, Any]]:
        """
        Fetch all questions from the Supabase questions table.

        Returns:
            List of question data dictionaries
        """
        try:
            response = self.supabase.table('questions').select('*').execute()
            questions = response.data
            logger.info(
                f"Successfully fetched {len(questions)} questions from Supabase")
            return questions
        except Exception as e:
            logger.error(f"Error fetching questions from Supabase: {str(e)}")
            return []

    def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific question by its ID.

        Args:
            question_id: The ID of the question to fetch

        Returns:
            Question data dictionary or None if not found
        """
        try:
            response = self.supabase.table('questions').select(
                '*').eq('id', question_id).execute()
            questions = response.data

            if not questions:
                logger.warning(f"No question found with ID: {question_id}")
                return None

            logger.info(
                f"Successfully fetched question with ID: {question_id}")
            return questions[0]
        except Exception as e:
            logger.error(
                f"Error fetching question {question_id} from Supabase: {str(e)}")
            return None

    def update_question(self, question_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a question in the database.

        Args:
            question_id: The ID of the question to update
            data: The data to update

        Returns:
            True if successful, False otherwise
        """
        try:
            self.supabase.table('questions').update(
                data).eq('id', question_id).execute()
            logger.info(
                f"Successfully updated question with ID: {question_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating question {question_id}: {str(e)}")
            return False
