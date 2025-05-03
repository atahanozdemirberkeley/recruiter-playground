import logging
from fastapi import APIRouter, HTTPException
from utils.database_manager import DatabaseManager

# Configure router
router = APIRouter(prefix="/api")

# Configure logging
logger = logging.getLogger(__name__)


@router.get("/questions/{question_id}")
async def get_question(question_id: str):
    """
    Get a question by its ID.

    Args:
        question_id: The ID of the question to retrieve

    Returns:
        The question data
    """
    try:
        # Create an instance of the database manager
        db_manager = DatabaseManager()

        # Get the question by ID
        question = db_manager.get_question_by_id(question_id)
        if not question:
            raise HTTPException(
                status_code=404, detail=f"Question with ID {question_id} not found")

        return question
    except Exception as e:
        # Log the error
        logger.error(f"Error fetching question {question_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving question: {str(e)}")
