"""
Environment preparation script for Sports Baseball Player Analysis task.

This script imports and uses the shared sports database setup utilities.
"""

import sys
import logging
from pathlib import Path

# Add the sports directory to import the shared utilities
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sports_setup import prepare_sports_environment

logger = logging.getLogger(__name__)


def prepare_environment():
    """Main function to prepare the sports database environment."""
    prepare_sports_environment()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prepare_environment()