"""
Environment preparation script for Employees Management Structure Analysis task.

This script imports and uses the shared employees database setup utilities.
"""

import sys
import logging
from pathlib import Path

# Add the employees directory to import the shared utilities
sys.path.append(str(Path(__file__).resolve().parents[1]))

from employees_setup import prepare_employees_environment

logger = logging.getLogger(__name__)


def prepare_environment():
    """Main function to prepare the employees database environment."""
    prepare_employees_environment()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prepare_environment()