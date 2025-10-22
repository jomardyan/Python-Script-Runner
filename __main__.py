"""
Python Script Runner - Main Entry Point

Enables running the module as:
    python -m runner [script.py] [args...]

This provides a clean entry point for module execution.
"""

import sys
from runner import main

if __name__ == "__main__":
    sys.exit(main())
