"""
Environment preparation script for DVD Rental Customer Analysis Fix task.

This script imports and uses the shared DVD rental database setup utilities.
"""

import sys
import logging
from pathlib import Path

# Add the dvdrental directory to import the shared utilities
sys.path.append(str(Path(__file__).resolve().parents[1]))

from dvdrental_setup import prepare_dvdrental_environment

logger = logging.getLogger(__name__)


def prepare_environment():
    """Main function to prepare the DVD rental database environment."""
    prepare_dvdrental_environment()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prepare_environment()