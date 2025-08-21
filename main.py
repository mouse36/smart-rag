#!/usr/bin/env python3
"""
Main entry point for Nixpacks deployment
This file helps Nixpacks detect this as a Python application
"""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Change to backend directory
os.chdir(backend_dir)

# Import and run the Railway startup script
if __name__ == "__main__":
    from run_railway import main
    main()
