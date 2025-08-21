#!/usr/bin/env python3
"""
Main entry point for Nixpacks deployment
This file helps Nixpacks detect this as a Python application
"""

import os
import sys
from pathlib import Path

# Import and run the Railway startup script
if __name__ == "__main__":
    from run import main
    main()
