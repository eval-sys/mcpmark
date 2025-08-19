"""
Environment preparation script for Chinook Sales and Music Charts task.

This script imports and uses the shared Chinook database setup utilities.
"""

import sys
import logging
from pathlib import Path

# Add the chinook directory to import the shared utilities
sys.path.append(str(Path(__file__).resolve().parents[1]))

from chinook_setup import prepare_chinook_environment

logger = logging.getLogger(__name__)


def prepare_environment():
    """Main function to prepare the Chinook database environment."""
    prepare_chinook_environment()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prepare_environment()