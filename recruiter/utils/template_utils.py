"""Utility module for handling template loading."""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def load_template(template_path: str, project_root: Optional[str] = None) -> str:
    """
    Load a template file from the templates directory.
    
    Args:
        template_path: Path to the template file, relative to templates directory
                      (e.g. 'template_select_tables' or 'template_select_tables.txt')
        project_root: Optional project root directory. If not provided, will be inferred
        
    Returns:
        str: Contents of the template file
        
    Raises:
        FileNotFoundError: If template file doesn't exist
        IOError: If there's an error reading the template file
    """
    try:
        if project_root is None:
            # Get the project root directory (3 levels up from this file)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            
        # If template_path is already absolute, use it as is
        if os.path.isabs(template_path):
            full_path = template_path
        else:
            # Otherwise join with templates directory
            full_path = os.path.join(project_root, "templates", template_path)
            
            # If path doesn't include .txt extension, add it
            if not full_path.endswith('.txt'):
                full_path += '.txt'
        
        with open(full_path, 'r') as f:
            template = f.read()
        return template
        
    except FileNotFoundError:
        logger.error(f"Template file not found at: {full_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        raise 